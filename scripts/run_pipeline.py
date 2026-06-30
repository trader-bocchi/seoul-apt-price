"""
수집 → 분석 → 전송 인메모리 파이프라인

수집 → 분석 → 텔레그램 전송을 한 번에 실행합니다.
`python scripts/run_pipeline.py`로 수동 실행합니다.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import pandas as pd
from datetime import datetime
from src.collectors.region_collector import RegionCollector
from src.collectors.api_client import ApiConfig
from src.config.env_loader import EnvConfig
from src.analyzers.complex_analyzer import ComplexAnalyzer
from src.analyzers.migration_analyzer import build_migration_report
from src.notifiers.telegram import TelegramNotifier
from src.storage.csv_store import CSVStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _previous_run_raw_total(raw_base: Path, current_date_str: str) -> int:
    """직전 실행(가장 최근의 이전 날짜) raw CSV의 총 행수(중복 제거 전) 반환. 없으면 0."""
    totals: dict[str, int] = {}
    for csv_path in raw_base.glob("*/properties_*.csv"):
        date_str = csv_path.stem.replace("properties_", "")
        if date_str >= current_date_str:  # 이번 실행분 제외
            continue
        try:
            totals[date_str] = totals.get(date_str, 0) + len(
                pd.read_csv(csv_path, usecols=["매물번호"], encoding="utf-8-sig")
            )
        except Exception:
            continue
    return totals[max(totals)] if totals else 0


def properties_to_dataframe(properties) -> pd.DataFrame:
    """Property 리스트를 분석용 DataFrame으로 변환 (한글 컬럼명 사용)"""
    rows = []
    for p in properties:
        rows.append({
            "매물번호": p.item_id,
            "지역명": p.region_name,
            "단지명": p.complex_name,
            "부동산유형": p.property_type,
            "거래유형": p.trade_type,
            "거래유형코드": p.trade_type_code,
            "가격": p.price,
            "가격표시": p.price_display,
            "위도": p.latitude,
            "경도": p.longitude,
            "최소관리비": p.min_mvi_fee,
            "최대관리비": p.max_mvi_fee,
            "VR존재": p.tour_exist,
            "수집일시": p.collected_at.isoformat(),
            "지역코드": p.cortar_no,
            "매물상태코드": p.atcl_stat_cd,
            "층수정보": p.flr_info,
            "임대료": p.rent_prc,
            "전용면적평": p.spc1,
            "전용면적제곱미터": p.spc2,
            "방향": p.direction,
            "매물확인일자": p.atcl_cfm_ymd,
            "동명": p.bild_nm,
            "매물특징설명": p.atcl_fetr_desc,
            "직접거래여부": p.direct_trad_yn,
            "중개사플랫폼명": p.cp_nm,
            "중개사명": p.rltr_nm,
        })
    return pd.DataFrame(rows)


def main():
    # 1. 설정 로드
    region_names = EnvConfig.get_region_names()
    if not region_names:
        logger.error("REGION_NAME이 설정되지 않았습니다.")
        sys.exit(1)

    my_home = EnvConfig.get_my_home_complex_name()
    target_homes = EnvConfig.get_target_home_complex_names()
    complex_names = ([my_home] if my_home else []) + target_homes

    if not complex_names:
        logger.error("MY_HOME_COMPLEX_NAME 또는 TARGET_HOME_COMPLEX_NAME이 설정되지 않았습니다.")
        sys.exit(1)

    try:
        notifier = TelegramNotifier()
    except ValueError as e:
        logger.error(f"텔레그램 설정 오류: {e}")
        sys.exit(1)

    dprc_min = EnvConfig.get_price_filter_min()
    dprc_max = EnvConfig.get_price_filter_max()
    spc_min = EnvConfig.get_area_filter_min()
    spc_max = EnvConfig.get_area_filter_max()

    has_filters = any(v is not None for v in [dprc_min, dprc_max, spc_min, spc_max])

    # 2. 수집 + 지역별 즉시 raw 저장
    logger.info(f"수집 대상 지역 {len(region_names)}개: {', '.join(region_names)}")
    collector = RegionCollector(ApiConfig(
        timeout=10, max_retries=3, max_workers=EnvConfig.get_collect_max_workers()
    ))
    all_properties = []

    raw_base = project_root / "data" / "raw"
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    for region_name in region_names:
        try:
            if has_filters:
                # 매매: 가격+면적 필터 모두 적용
                sale_props, _ = collector.collect_properties_by_region(
                    region_name=region_name,
                    rlet_tp_cd="APT:JGC",
                    trad_tp_cd="A1",
                    dprc_min=dprc_min,
                    dprc_max=dprc_max,
                    spc_min=spc_min,
                    spc_max=spc_max,
                )
                # 전세: 면적 필터만 적용 (전세가와 매매가 범위가 다름)
                lease_props, _ = collector.collect_properties_by_region(
                    region_name=region_name,
                    rlet_tp_cd="APT:JGC",
                    trad_tp_cd="B1",
                    dprc_min=None,
                    dprc_max=None,
                    spc_min=spc_min,
                    spc_max=spc_max,
                )
                props = sale_props + lease_props
            else:
                props, _ = collector.collect_properties_by_region(
                    region_name=region_name,
                    rlet_tp_cd="APT:JGC",
                    trad_tp_cd="A1:B1",
                )
            all_properties.extend(props)
            logger.info(f"[{region_name}] {len(props)}개 수집")

            # 행정구역 폴더에 즉시 저장
            region_dir = raw_base / region_name
            region_dir.mkdir(parents=True, exist_ok=True)
            region_path = region_dir / f"properties_{date_str}.csv"
            properties_to_dataframe(props).to_csv(region_path, index=False, encoding="utf-8-sig")
            logger.info(f"  → 저장: {region_path}")
        except Exception as e:
            logger.warning(f"[{region_name}] 수집 실패: {e}")

    if not all_properties:
        logger.error("수집된 매물이 없습니다.")
        sys.exit(1)

    # 2.5. my_home 단지 매물 특징 설명 보강 (basicInfo API)
    if my_home:
        my_home_props = [p for p in all_properties if my_home.lower() in p.complex_name.lower()]
        if my_home_props:
            logger.info(f"[{my_home}] 특징 설명 보강 중... ({len(my_home_props)}건)")
            enriched = 0
            for p in my_home_props:
                desc = collector.api_client.get_article_basic_info(
                    p.item_id, trade_type=p.trade_type_code
                )
                if desc:
                    p.atcl_fetr_desc = desc
                    enriched += 1
            logger.info(f"[{my_home}] 특징 설명 {enriched}건 보강 완료")

            # my_home 지역 CSV 덮어쓰기 (특징 설명 포함)
            my_home_region = my_home_props[0].region_name
            region_props = [p for p in all_properties if p.region_name == my_home_region]
            region_path = raw_base / my_home_region / f"properties_{date_str}.csv"
            properties_to_dataframe(region_props).to_csv(region_path, index=False, encoding="utf-8-sig")
            logger.info(f"  → 특징 설명 반영 재저장: {region_path}")

    # 3. 전체 합산 DataFrame + 중복 제거
    combined_df = properties_to_dataframe(all_properties)
    before = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=["매물번호"])
    logger.info(f"총 {len(combined_df)}개 매물 (중복 {before - len(combined_df)}개 제거)")

    # 수집 건수 급감 감지 (raw 기준, 직전 실행 대비 50% 미만이면 429/IP 차단 의심)
    prev_raw_total = _previous_run_raw_total(raw_base, date_str)
    if prev_raw_total and before < prev_raw_total * 0.5:
        warn = (
            f"⚠️ <b>수집 건수 급감</b>\n"
            f"직전 {prev_raw_total:,}건 → 이번 {before:,}건 "
            f"({before / prev_raw_total * 100:.0f}%)\n"
            f"429 rate limit / IP 차단 의심 — 리포트가 불완전할 수 있습니다."
        )
        logger.warning(warn.replace("\n", " "))
        notifier.send_message(warn)

    # 4. 단지별 필터링 & 분석
    all_analyses = {}
    my_analysis = None

    for complex_name in complex_names:
        filtered = combined_df[
            combined_df["단지명"].str.contains(complex_name, na=False, case=False)
        ]
        if filtered.empty:
            logger.warning(f"[{complex_name}] 매물 없음")
            continue

        analysis = ComplexAnalyzer(complex_name).analyze_complex_from_dataframe(filtered)
        if analysis.get("total_count", 0) == 0:
            logger.warning(f"[{complex_name}] 분석 결과 없음")
            continue

        logger.info(f"[{complex_name}] 분석 완료 ({analysis['total_count']}개 매물)")
        all_analyses[complex_name] = analysis

        if complex_name == my_home:
            my_analysis = analysis

    if not all_analyses:
        logger.error("분석 결과가 없습니다.")
        sys.exit(1)

    # 5. 텔레그램 전송 (순서: 내 단지 상세 → 호가 리포트 → 이사 비교 → 추세)
    logger.info("텔레그램 리포트 전송 중...")

    # 5-1. 내 단지 상세분석
    if my_analysis:
        if not notifier.send_my_home_detailed_analysis(my_home, my_analysis):
            logger.error("내 단지 상세분석 리포트 전송 실패")

    # 5-2. 호가 리포트 (전 단지)
    if not notifier.send_all_complexes_analysis(all_analyses):
        logger.error("단지 분석 리포트 전송 실패")

    # 5-3. 이사 비교 레포트 (스냅샷 + 추세)
    if my_home and target_homes:
        my_home_area = EnvConfig.get_my_home_area()
        if my_home_area is None:
            logger.warning("MY_HOME_AREA 미설정 — 이사 비교 레포트 건너뜀")
        else:
            logger.info("이사 비교 레포트 전송 중...")
            migration_report = build_migration_report(
                combined_df,
                my_home,
                target_homes,
                raw_base,
                my_home_area,
            )
            if not notifier.send_migration_report(migration_report):
                logger.error("이사 비교 레포트 전송 실패")

    logger.info("완료")


if __name__ == "__main__":
    main()
