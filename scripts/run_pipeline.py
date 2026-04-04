"""
수집 → 분석 → 전송 인메모리 파이프라인

로컬 파일 저장 없이 전체 파이프라인을 메모리 내에서 실행합니다.
GitHub Actions 등 임시 환경에서 사용합니다.
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
from src.notifiers.telegram import TelegramNotifier
from src.storage.csv_store import CSVStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

    trad_tp_cd = "A1:B1:B2:B3"
    if any(v is not None for v in [dprc_min, dprc_max, spc_min, spc_max]):
        trad_tp_cd = "A1"

    # 2. 수집 + 지역별 즉시 raw 저장
    logger.info(f"수집 대상 지역 {len(region_names)}개: {', '.join(region_names)}")
    collector = RegionCollector(ApiConfig(timeout=10, max_retries=3))
    all_properties = []

    raw_base = project_root / "data" / "raw"
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    for region_name in region_names:
        try:
            props, _ = collector.collect_properties_by_region(
                region_name=region_name,
                rlet_tp_cd="APT:JGC",
                trad_tp_cd=trad_tp_cd,
                dprc_min=dprc_min,
                dprc_max=dprc_max,
                spc_min=spc_min,
                spc_max=spc_max,
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

    # 3. 전체 합산 DataFrame + 중복 제거
    combined_df = properties_to_dataframe(all_properties)
    before = len(combined_df)
    combined_df = combined_df.drop_duplicates(subset=["매물번호"])
    logger.info(f"총 {len(combined_df)}개 매물 (중복 {before - len(combined_df)}개 제거)")

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

    # 5. 텔레그램 전송
    logger.info("텔레그램 리포트 전송 중...")

    if not notifier.send_all_complexes_analysis(all_analyses):
        logger.error("단지 분석 리포트 전송 실패")

    if my_analysis:
        if not notifier.send_my_home_detailed_analysis(my_home, my_analysis):
            logger.error("내 단지 상세분석 리포트 전송 실패")

    logger.info("완료")


if __name__ == "__main__":
    main()
