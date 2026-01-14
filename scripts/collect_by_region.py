"""
행정구역 기반 매물 수집 및 결과 생성 메인 파일
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from typing import List, Optional
from src.collectors.region_collector import RegionCollector
from src.collectors.api_client import ApiConfig
from src.config.env_loader import EnvConfig
from src.storage.csv_store import CSVStore


def collect_single_region(
    collector: RegionCollector,
    region_name: str,
    rlet_tp_cd: str,
    trad_tp_cd: str,
    region_index: int = 1,
    total_regions: int = 1,
    dprc_min: Optional[int] = None,
    dprc_max: Optional[int] = None,
    spc_min: Optional[int] = None,
    spc_max: Optional[int] = None
) -> tuple[List, List]:
    """단일 지역 수집"""
    print(f"\n[{region_index}/{total_regions}] 지역: {region_name}")
    print("-" * 60)
    
    def progress_callback(current: int, total: int, message: str):
        """진행 상황 출력"""
        pct = int((current / total) * 100) if total > 0 else 0
        print(f"[{pct:3d}%] {message}")
    
    properties, complexes = collector.collect_properties_by_region(
        region_name=region_name,
        rlet_tp_cd=rlet_tp_cd,
        trad_tp_cd=trad_tp_cd,
        progress_callback=progress_callback,
        dprc_min=dprc_min,
        dprc_max=dprc_max,
        spc_min=spc_min,
        spc_max=spc_max
    )
    
    return properties, complexes


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("행정구역 기반 매물 수집 시스템")
    print("=" * 60)
    
    # 1. 환경 변수 검증
    region_names = EnvConfig.get_region_names()
    if not region_names:
        print("오류: .env 파일에 REGION_NAME이 설정되지 않았습니다.")
        print("\n예시 (단일 지역):")
        print("  REGION_NAME=성남시 수정구 신흥동")
        print("\n예시 (여러 지역):")
        print("  REGION_NAME=성남시 수정구 신흥동,서울시 강남구 역삼동")
        sys.exit(1)
    
    print(f"\n수집 대상 지역: {len(region_names)}개")
    for idx, name in enumerate(region_names, 1):
        print(f"  {idx}. {name}")
    
    print(f"\n[정보] 각 지역마다 자동으로 cortarNo를 추출합니다.")
    print(f"   .env의 REGION_CORTAR_NO는 무시됩니다.")
    
    # 2. 수집 옵션 설정
    rlet_tp_cd = "APT"  # 아파트
    # 정답지 API 형식: A1:B1:B2:B3 (매매, 전세, 월세, 반전세 모두 수집)
    trad_tp_cd = "A1:B1:B2:B3"   # 모든 거래 유형 (매매, 전세, 월세, 반전세)
    
    # 3. 필터 조건 설정 (.env에서 읽어옴)
    # .env 파일에 다음 변수를 설정할 수 있습니다:
    # FILTER_DPRC_MIN=80000  (최소 가격: 8억, 만원 단위)
    # FILTER_DPRC_MAX=130000 (최대 가격: 13억, 만원 단위)
    # FILTER_SPC_MIN=33      (최소 면적: 33평)
    # FILTER_SPC_MAX=99      (최대 면적: 99평)
    dprc_min = EnvConfig.get_price_filter_min()
    dprc_max = EnvConfig.get_price_filter_max()
    spc_min = EnvConfig.get_area_filter_min()
    spc_max = EnvConfig.get_area_filter_max()
    
    # 필터가 설정되면 매매만 수집
    if dprc_min is not None or dprc_max is not None or spc_min is not None or spc_max is not None:
        trad_tp_cd = "A1"  # 필터 조건이 있으면 매매만 수집
    
    print(f"\n부동산 유형: {rlet_tp_cd}")
    print(f"거래 유형: {trad_tp_cd}")
    if dprc_min is not None or dprc_max is not None:
        if dprc_min and dprc_max:
            print(f"가격 필터: {dprc_min:,}만원 ~ {dprc_max:,}만원")
        else:
            filter_str = ""
            if dprc_min:
                filter_str += f"{dprc_min:,}만원 이상"
            if dprc_max:
                if filter_str:
                    filter_str += " ~ "
                filter_str += f"{dprc_max:,}만원 이하"
            print(f"가격 필터: {filter_str}")
    if spc_min is not None or spc_max is not None:
        if spc_min and spc_max:
            print(f"면적 필터: {spc_min}평 ~ {spc_max}평")
        else:
            filter_str = ""
            if spc_min:
                filter_str += f"{spc_min}평 이상"
            if spc_max:
                if filter_str:
                    filter_str += " ~ "
                filter_str += f"{spc_max}평 이하"
            print(f"면적 필터: {filter_str}")
    
    # 3. 수집기 초기화
    api_config = ApiConfig(
        min_delay=1.0,  # API 호출 간 최소 딜레이
        timeout=10,
        max_retries=3
    )
    collector = RegionCollector(api_config)
    
    # 4. 모든 지역 수집
    print("\n" + "=" * 60)
    print("매물 수집 시작")
    print("=" * 60)
    
    all_properties = []
    all_complexes = []
    
    try:
        for idx, region_name in enumerate(region_names, 1):
            try:
                properties, complexes = collect_single_region(
                    collector=collector,
                    region_name=region_name,
                    rlet_tp_cd=rlet_tp_cd,
                    trad_tp_cd=trad_tp_cd,
                    region_index=idx,
                    total_regions=len(region_names),
                    dprc_min=dprc_min,
                    dprc_max=dprc_max,
                    spc_min=spc_min,
                    spc_max=spc_max
                )
                
                all_properties.extend(properties)
                all_complexes.extend(complexes)
                
                print(f"\n[{idx}/{len(region_names)}] {region_name} 수집 완료: {len(properties)}개 매물")
                
            except Exception as e:
                print(f"\n[{idx}/{len(region_names)}] {region_name} 수집 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # 전체 결과 출력
        print("\n" + "=" * 60)
        print("전체 수집 완료")
        print("=" * 60)
        print(f"총 수집된 매물: {len(all_properties)}개")
        print(f"총 수집된 단지: {len(all_complexes)}개")
        
        # 5. 데이터 저장
        print("\n" + "=" * 60)
        print("데이터 저장 중...")
        print("=" * 60)
        
        # 각 지역별로 저장
        date = datetime.now()
        saved_files = []
        
        for region_name in region_names:
            # 해당 지역의 매물만 필터링
            region_properties = [p for p in all_properties if p.region_name == region_name]
            
            if region_properties:
                # Property를 딕셔너리로 변환 (한글 컬럼명 사용)
                def property_to_dict(p):
                    """Property를 한글 컬럼명 딕셔너리로 변환"""
                    return {
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
                        "상위부동산유형코드": p.upr_rlet_tp_cd,
                        "검증타입코드": p.vrfc_tp_cd,
                        "층수정보": p.flr_info,
                        "임대료": p.rent_prc,
                        "전용면적평": p.spc1,
                        "전용면적제곱미터": p.spc2,
                        "방향": p.direction,
                        "매물확인일자": p.atcl_cfm_ymd,
                        "대표이미지URL": p.rep_img_url,
                        "대표이미지타입코드": p.rep_img_tp_cd,
                        "대표이미지썸네일": p.rep_img_thumb,
                        "매물특징설명": p.atcl_fetr_desc,
                        "태그리스트": p.tag_list,
                        "동명": p.bild_nm,
                        "분": p.minute,
                        "동일주소매물개수": p.same_addr_cnt,
                        "동일주소직접거래개수": p.same_addr_direct_cnt,
                        "동일주소해시": p.same_addr_hash,
                        "동일주소최고가": p.same_addr_max_prc,
                        "동일주소최저가": p.same_addr_min_prc,
                        "중개사플랫폼ID": p.cpid,
                        "중개사플랫폼명": p.cp_nm,
                        "중개사개수": p.cp_cnt,
                        "중개사명": p.rltr_nm,
                        "직접거래여부": p.direct_trad_yn,
                        "기타방개수": p.et_room_cnt,
                        "거래가격한글": p.trade_price_han,
                        "거래임대료": p.trade_rent_price,
                        "집주인확인여부": p.trade_checked_by_owner,
                        "상세주소여부": p.dtl_addr_yn,
                        "상세주소": p.dtl_addr,
                        "VR_URL": p.vr_url,
                        "안전임대인여부": p.is_safe_lessor_of_hug
                    }
                
                properties_data = [property_to_dict(p) for p in region_properties]
                
                filename = CSVStore.save_raw_offers(
                    complex_name=region_name,
                    properties=properties_data,
                    date=date
                )
                saved_files.append(filename)
                print(f"저장 완료: {filename} ({len(region_properties)}개 매물)")
        
        # 6. 결과 요약 출력
        print("\n" + "=" * 60)
        print("수집 결과 요약")
        print("=" * 60)
        
        if all_properties:
            # 가격 통계
            prices = [p.price for p in all_properties if p.price > 0]
            if prices:
                min_price = min(prices)
                max_price = max(prices)
                avg_price = sum(prices) / len(prices)
                
                print(f"\n전체 가격 통계 (만원 단위):")
                print(f"  최저가: {min_price:,}만원")
                print(f"  최고가: {max_price:,}만원")
                print(f"  평균가: {avg_price:,.0f}만원")
                print(f"  표본 수: {len(prices)}개")
            
            # 지역별 통계
            print(f"\n지역별 매물 수:")
            region_counts = {}
            for p in all_properties:
                region_name = p.region_name
                region_counts[region_name] = region_counts.get(region_name, 0) + 1
            
            for region_name, count in sorted(region_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"  {region_name}: {count}개")
            
            # 단지별 통계 (상위 10개)
            complex_counts = {}
            for p in all_properties:
                complex_name = p.complex_name if p.complex_name else "미지정"
                complex_counts[complex_name] = complex_counts.get(complex_name, 0) + 1
            
            print(f"\n단지별 매물 수 (상위 10개):")
            sorted_complexes = sorted(complex_counts.items(), key=lambda x: x[1], reverse=True)
            for complex_name, count in sorted_complexes[:10]:
                print(f"  {complex_name}: {count}개")
        
        print("\n" + "=" * 60)
        print("프로그램 종료")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

