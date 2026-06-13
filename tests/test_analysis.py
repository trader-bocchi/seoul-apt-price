"""
순수 분석 함수 회귀 테스트 (네트워크 호출 없음).

gstack 점검(R1~R3) 적용 후 추가:
- 분석 통계 정확성 (migration / complex)
- R2 회귀: 텔레그램 HTML escaping
"""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.analyzers import migration_analyzer as ma
from src.analyzers.complex_analyzer import ComplexAnalyzer
from src.notifiers import telegram as tg


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """한글 컬럼 표준 스키마로 DataFrame 생성"""
    base_cols = {
        "단지명": "테스트단지",
        "지역명": "테스트동",
        "거래유형코드": "A1",
        "가격": 0,                # 만원
        "전용면적제곱미터": 59.0,
        "층수정보": "10/20",
        "동명": "101",
        "방향": "남향",
        "매물특징설명": "",
    }
    return pd.DataFrame([{**base_cols, **r} for r in rows])


# ── migration_analyzer._compute_area_stats ──────────────────

def test_compute_area_stats_sale_lease_gap():
    df = _make_df([
        {"거래유형코드": "A1", "가격": 140000, "전용면적제곱미터": 59.0},
        {"거래유형코드": "A1", "가격": 150000, "전용면적제곱미터": 59.5},
        {"거래유형코드": "B1", "가격": 70000, "전용면적제곱미터": 59.0},
        {"거래유형코드": "B1", "가격": 74000, "전용면적제곱미터": 59.2},
    ])
    s = ma._compute_area_stats(df, 59)
    assert s is not None
    assert s["sale_median"] == pytest.approx(14.5)   # (14.0+15.0)/2
    assert s["lease_median"] == pytest.approx(7.2)   # (7.0+7.4)/2
    assert s["lease_gap"] == pytest.approx(7.3)
    assert s["sale_count"] == 2 and s["lease_count"] == 2
    assert isinstance(s["price_per_pyeong"], int) and s["price_per_pyeong"] > 0


def test_compute_area_stats_empty_area_returns_none():
    df = _make_df([{"거래유형코드": "A1", "가격": 140000, "전용면적제곱미터": 84.0}])
    assert ma._compute_area_stats(df, 59) is None


def test_find_closest_area():
    assert ma._find_closest_area([49, 59, 84], 60) == 59
    assert ma._find_closest_area([], 59) is None


# ── migration_analyzer.match_files_to_periods ───────────────

def test_match_files_to_periods_buckets(tmp_path: Path):
    today = date(2026, 6, 13)
    # days_ago: 31→1M[1,60), 91→3M[60,135), 200→6M[135,272), 400→1Y[272,∞)
    names = {
        "1M": "properties_20260513_000000.csv",   # 31d
        "3M": "properties_20260314_000000.csv",   # 91d
        "6M": "properties_20251125_000000.csv",   # 200d
        "1Y": "properties_20250509_000000.csv",   # 400d
    }
    files = []
    for n in names.values():
        p = tmp_path / n
        p.write_text("x")
        files.append(p)
    matched = ma.match_files_to_periods(files, today)
    for label, fname in names.items():
        assert matched[label] is not None
        assert matched[label].name == fname


def test_match_files_excludes_today(tmp_path: Path):
    today = date(2026, 6, 13)
    p = tmp_path / "properties_20260613_120000.csv"  # days_ago=0 → 제외
    p.write_text("x")
    matched = ma.match_files_to_periods([p], today)
    assert all(v is None for v in matched.values())


# ── ComplexAnalyzer.analyze_complex_from_dataframe ──────────

def test_analyze_complex_uses_sale_only_for_price():
    df = _make_df([
        {"거래유형코드": "A1", "가격": 100000, "전용면적제곱미터": 59.0},
        {"거래유형코드": "A1", "가격": 120000, "전용면적제곱미터": 59.0},
        {"거래유형코드": "B1", "가격": 60000, "전용면적제곱미터": 59.0},  # 전세는 매매 분포에서 제외
    ])
    res = ComplexAnalyzer("테스트단지").analyze_complex_from_dataframe(df)
    assert res["total_count"] == 2  # 매매 2건만
    by_area = res["price_distribution_by_area"]["by_area"]
    assert 59 in by_area
    assert by_area[59]["median"] == pytest.approx(11.0)  # (10+12)/2, 전세 6 미포함
    # 전세 분포는 별도로 잡힘
    assert res["lease_distribution_by_area"]["by_area"][59]["median"] == pytest.approx(6.0)


# ── R2 회귀: HTML escaping ──────────────────────────────────

def test_esc_escapes_html_metachars():
    assert tg._esc("A<b>&'\"") == "A&lt;b&gt;&amp;&#x27;&quot;"


def test_complex_block_escapes_complex_name():
    data = {
        "total_count": 1,
        "price_distribution_by_area": {
            "by_area": {59: {"min": 1.0, "max": 2.0, "median": 1.5, "count": 1}}
        },
    }
    out = tg._format_complex_block("강남<script>아파트&", data, is_my_home=False)
    # 단지명 내부의 꺾쇠/앰퍼샌드는 이스케이프되어 raw 태그가 남지 않아야 함
    assert "<script>" not in out
    assert "강남&lt;script&gt;아파트&amp;" in out
    # 래퍼 태그(<b>)는 정상 유지
    assert "<b>" in out
