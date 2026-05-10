"""
이사 타겟 단지 비교 분석 모듈

내 단지 vs 타겟 단지들의 전용면적별 매매/전세 중위가, 평당가 비교.
시계열 추세: 1M/3M/6M/1Y 구간 매칭 (파일 간 중복 배정 없음).
"""
import math
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

_SQM_PER_PYEONG = 3.3058

# 비교할 타겟 전용면적 (㎡)
TARGET_AREAS = [59, 84]

# 시계열 구간: (label, target_days, zone_lo_inclusive, zone_hi_exclusive)
# 경계 = 연속 구간 중점: 60d, 135d, 272d
_PERIODS: List[Tuple[str, int, int, int]] = [
    ("1M",  30,   1,   60),
    ("3M",  90,  60,  135),
    ("6M", 180, 135,  272),
    ("1Y", 365, 272, 9999),
]


# ──────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────

def _file_date(path: Path) -> Optional[date]:
    """파일명 properties_YYYYMMDD_HHMMSS.csv 에서 날짜 추출"""
    try:
        return datetime.strptime(path.stem.split("_")[1], "%Y%m%d").date()
    except Exception:
        return None


def _find_closest_area(available: List[int], target: int) -> Optional[int]:
    if not available:
        return None
    return min(available, key=lambda x: abs(x - target))


def _get_available_areas(df: pd.DataFrame) -> List[int]:
    """전용면적제곱미터 컬럼에서 floor 값 목록 반환"""
    areas = pd.to_numeric(df["전용면적제곱미터"], errors="coerce").dropna()
    return sorted({math.floor(a) for a in areas})


def _compute_area_stats(df: pd.DataFrame, area_key: int) -> Optional[Dict]:
    """
    특정 면적대(floor(전용면적제곱미터) == area_key)의 통계 계산.

    Returns:
        {
            actual_area: int,
            sale_median: float | None,   # 억
            lease_median: float | None,  # 억
            lease_gap: float | None,     # 억
            price_per_pyeong: int | None,  # 만원/평 (매매 중위 기준)
            sale_count: int,
            lease_count: int,
        }
    """
    work = df.copy()
    work["전용면적제곱미터"] = pd.to_numeric(work["전용면적제곱미터"], errors="coerce")
    work["면적대"] = work["전용면적제곱미터"].apply(
        lambda x: math.floor(x) if pd.notna(x) else None
    )
    work["가격_억"] = pd.to_numeric(work["가격"], errors="coerce") / 10000

    area_df = work[work["면적대"] == area_key]
    if area_df.empty:
        return None

    sale_df = area_df[area_df["거래유형코드"] == "A1"]
    lease_df = area_df[area_df["거래유형코드"] == "B1"]

    sale_median = float(sale_df["가격_억"].median()) if not sale_df.empty else None
    lease_median = float(lease_df["가격_억"].median()) if not lease_df.empty else None
    lease_gap = (
        round(sale_median - lease_median, 2)
        if sale_median is not None and lease_median is not None
        else None
    )

    # 평당가: 해당 면적대 실제 전용면적 중위값 기준
    actual_m2 = area_df["전용면적제곱미터"].median()
    price_per_pyeong: Optional[int] = None
    if sale_median is not None and actual_m2 and actual_m2 > 0:
        pyeong = actual_m2 / _SQM_PER_PYEONG
        price_per_pyeong = round(sale_median * 10000 / pyeong)  # 만원/평

    return {
        "actual_area": area_key,
        "sale_median": round(sale_median, 2) if sale_median is not None else None,
        "lease_median": round(lease_median, 2) if lease_median is not None else None,
        "lease_gap": lease_gap,
        "price_per_pyeong": price_per_pyeong,
        "sale_count": len(sale_df),
        "lease_count": len(lease_df),
    }


def _filter_complex(df: pd.DataFrame, complex_name: str) -> pd.DataFrame:
    return df[df["단지명"].str.contains(complex_name, na=False, case=False)]


# ──────────────────────────────────────────
# Public API
# ──────────────────────────────────────────

def match_files_to_periods(files: List[Path], today: date) -> Dict[str, Optional[Path]]:
    """
    파일 목록을 1M/3M/6M/1Y 구간에 1:1 매칭.

    구간 경계 (단위: 일 전):
      1M : [1, 60)
      3M : [60, 135)
      6M : [135, 272)
      1Y : [272, ∞)

    각 구간 내 후보 중 구간 타겟(30/90/180/365)에 가장 가까운 파일 선택.
    오늘 파일(days_ago=0)은 현재 스냅샷 용이므로 제외.
    """
    result: Dict[str, Optional[Path]] = {label: None for label, *_ in _PERIODS}

    dated: List[Tuple[int, Path]] = []
    for f in files:
        d = _file_date(f)
        if d is None:
            continue
        days_ago = (today - d).days
        if days_ago <= 0:
            continue
        dated.append((days_ago, f))

    for label, target, lo, hi in _PERIODS:
        candidates = [(d, f) for d, f in dated if lo <= d < hi]
        if candidates:
            result[label] = min(candidates, key=lambda x: abs(x[0] - target))[1]

    return result


def build_migration_report(
    current_df: pd.DataFrame,
    my_home: str,
    target_homes: List[str],
    data_root: Path,
    my_home_area: float,
) -> Dict:
    """
    이사 비교 레포트 데이터 구성.

    Args:
        current_df:    이번 수집 전체 DataFrame (지역명, 단지명, 거래유형코드, 가격, 전용면적제곱미터 포함)
        my_home:       내 단지명
        target_homes:  타겟 단지명 리스트
        data_root:     raw 데이터 루트 Path (data/raw)
        my_home_area:  내 집 전용면적 (㎡)

    Returns:
        {
            "my_home": {
                "name": str,
                "area": int,
                "stats": dict | None,
                "trend": {"1M": float|None, ...},
            },
            "targets": [
                {
                    "name": str,
                    "area_matched": {59: int, 84: int},   # target→actual 매핑
                    "snapshots": {59: stats, 84: stats},
                    "trend": {"1M": {59: float|None, 84: float|None}, ...},
                },
                ...
            ],
        }
    """
    today = date.today()

    # ── 내 단지 스냅샷 ──────────────────────────
    my_area_key = math.floor(my_home_area)
    my_df = _filter_complex(current_df, my_home)
    my_stats = _compute_area_stats(my_df, my_area_key) if not my_df.empty else None

    # 내 단지 시계열
    my_trend: Dict[str, Optional[float]] = {}
    if not my_df.empty and "지역명" in my_df.columns:
        my_region = my_df["지역명"].iloc[0]
        my_region_dir = data_root / my_region
        if my_region_dir.exists():
            period_files = match_files_to_periods(
                list(my_region_dir.glob("properties_*.csv")), today
            )
            for label, hist_path in period_files.items():
                if hist_path is None:
                    continue
                try:
                    hist_my = _filter_complex(
                        pd.read_csv(hist_path, encoding="utf-8-sig"), my_home
                    )
                    if hist_my.empty:
                        continue
                    s = _compute_area_stats(hist_my, my_area_key)
                    my_trend[label] = s["sale_median"] if s else None
                except Exception as e:
                    logger.warning(f"[migration] 내 단지 시계열 로드 실패 {hist_path}: {e}")

    report: Dict = {
        "my_home": {
            "name": my_home,
            "area": my_area_key,
            "stats": my_stats,
            "trend": my_trend,
        },
        "targets": [],
    }

    # ── 타겟 단지별 ─────────────────────────────
    for target_name in target_homes:
        target_df = _filter_complex(current_df, target_name)
        if target_df.empty:
            logger.warning(f"[migration] {target_name}: 현재 데이터 없음, 제외")
            continue

        available_areas = _get_available_areas(target_df)
        area_matched: Dict[int, int] = {}
        snapshots: Dict[int, Optional[Dict]] = {}

        for t_area in TARGET_AREAS:
            matched = _find_closest_area(available_areas, t_area)
            if matched is None:
                continue
            area_matched[t_area] = matched
            snapshots[t_area] = _compute_area_stats(target_df, matched)

        # 시계열
        trend: Dict[str, Dict[int, Optional[float]]] = {}
        if "지역명" in target_df.columns:
            region_name = target_df["지역명"].iloc[0]
            region_dir = data_root / region_name
            if region_dir.exists():
                period_files = match_files_to_periods(
                    list(region_dir.glob("properties_*.csv")), today
                )
                for label, hist_path in period_files.items():
                    if hist_path is None:
                        continue
                    try:
                        hist_target = _filter_complex(
                            pd.read_csv(hist_path, encoding="utf-8-sig"), target_name
                        )
                        if hist_target.empty:
                            continue
                        period_row: Dict[int, Optional[float]] = {}
                        for t_area, matched_area in area_matched.items():
                            s = _compute_area_stats(hist_target, matched_area)
                            period_row[t_area] = s["sale_median"] if s else None
                        if any(v is not None for v in period_row.values()):
                            trend[label] = period_row
                    except Exception as e:
                        logger.warning(f"[migration] 시계열 로드 실패 {hist_path}: {e}")

        report["targets"].append({
            "name": target_name,
            "area_matched": area_matched,
            "snapshots": snapshots,
            "trend": trend,
        })

    return report
