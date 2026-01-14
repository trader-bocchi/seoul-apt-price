"""
행정구역 기반 매물 수집 로직 (새로운 크롤링 방법)
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from src.collectors.api_client import NaverLandApiClient, ApiConfig
from src.collectors.data_collector import Property, Complex
from src.storage.csv_store import CSVStore
import math
import os
import csv


class RegionCollector:
    """행정구역 기반 매물 수집기"""
    
    # CSV 파일에서 로드한 행정구역 코드 캐시
    _region_code_cache: Optional[Dict[str, str]] = None
    
    def __init__(self, api_config: Optional[ApiConfig] = None):
        self.api_client = NaverLandApiClient(api_config)
        self.properties: List[Property] = []
        self.complexes: List[Complex] = []
    
    @classmethod
    def _load_region_codes_from_csv(cls) -> Dict[str, str]:
        """
        CSV 파일에서 행정구역명과 행정구역코드 매핑 로드
        
        Returns:
            {행정구역명: 행정구역코드} 딕셔너리
        """
        if cls._region_code_cache is not None:
            return cls._region_code_cache
        
        cache = {}
        csv_path = os.path.join('data', 'ref', '국토교통부_행정구역법정동코드_20250807.CSV')
        
        if not os.path.exists(csv_path):
            print(f"[경고] 행정구역 코드 CSV 파일을 찾을 수 없습니다: {csv_path}")
            cls._region_code_cache = cache
            return cache
        
        try:
            # 여러 인코딩 시도
            encodings = ['cp949', 'utf-8-sig', 'utf-8', 'euc-kr']
            for encoding in encodings:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        reader = csv.reader(f)
                        header = next(reader)  # 헤더 스킵
                        
                        for row in reader:
                            if len(row) >= 2:
                                region_code = row[0].strip()  # 행정구역코드 (컬럼 0)
                                region_name = row[1].strip()  # 행정구역명 (컬럼 1)
                                
                                if region_code and region_name:
                                    # 정확한 행정구역명으로 매핑
                                    cache[region_name] = region_code
                                    
                                    # 공백 제거 버전도 추가
                                    cache[region_name.replace(' ', '')] = region_code
                                    
                                    # "경기도" 제거 버전도 추가 (예: "경기도 성남시" -> "성남시")
                                    if region_name.startswith('경기도 '):
                                        short_name = region_name[4:]  # "경기도 " 제거
                                        cache[short_name] = region_code
                                        cache[short_name.replace(' ', '')] = region_code
                                    
                                    # "서울시" -> "서울" 변환
                                    if region_name.startswith('서울시 '):
                                        seoul_name = region_name.replace('서울시 ', '서울시 ')
                                        # 이미 추가됨
                        
                        print(f"[INFO] 행정구역 코드 {len(cache)}개 로드 완료")
                        cls._region_code_cache = cache
                        return cache
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"[경고] CSV 파일 읽기 실패 ({encoding}): {str(e)}")
                    continue
            
            print(f"[경고] 모든 인코딩 시도 실패")
            cls._region_code_cache = cache
            return cache
        except Exception as e:
            print(f"[경고] CSV 파일 로드 실패: {str(e)}")
            cls._region_code_cache = cache
            return cache
    
    def parse_region_name(self, region_name: str) -> Dict[str, Optional[str]]:
        """
        행정구역명을 파싱하여 시/도, 시/군/구, 읍/면/동 추출
        
        Args:
            region_name: 행정구역명 (예: "서울시 강서구", "성남시 수정구 신흥동")
        
        Returns:
            {"city": "서울시", "district": "강서구", "dong": "가양동", "province": None}
        """
        import re
        
        # 공백 제거 및 정규화
        name = region_name.strip()
        
        # 시/도 추출
        province = None
        city = None
        district = None
        dong = None
        
        # 경기도, 서울시, 부산시 등 추출
        province_match = re.search(r'(경기도|서울시|서울|부산시|부산|대구시|대구|인천시|인천|광주시|광주|대전시|대전|울산시|울산|세종시|세종|경상남도|경남|경상북도|경북|전라남도|전남|전라북도|전북|충청남도|충남|충청북도|충북|강원도|강원|제주도|제주)', name)
        if province_match:
            province = province_match.group(1)
            name = name.replace(province, "").strip()
        
        # 시 추출 (구보다 먼저 추출해야 함 - "성남시 수정구" 같은 경우)
        city_match = re.search(r'([가-힣]+시)', name)
        if city_match:
            city = city_match.group(1)
            name = name.replace(city, "").strip()
        
        # 시/군/구 추출 (구, 군, 읍, 면으로 끝나는 것)
        district_match = re.search(r'([가-힣]+(?:구|군|읍|면))', name)
        if district_match:
            district = district_match.group(1)
            name = name.replace(district, "").strip()
        
        # 동 추출
        dong_match = re.search(r'([가-힣0-9]+(?:동|가|리))', name)
        if dong_match:
            dong = dong_match.group(1)
        
        # city가 없으면 province를 city로 사용
        if not city and province:
            if province.endswith("시"):
                city = province
            elif province == "서울" or province == "서울시":
                city = "서울시"
            elif province == "경기도":
                # 경기도는 city가 따로 있음 (성남시, 수원시 등)
                pass
        
        return {
            "province": province,
            "city": city,
            "district": district,
            "dong": dong
        }
    
    def generate_cortar_no_from_region_name(self, region_name: str) -> Optional[str]:
        """
        행정구역명에서 cortarNo 생성 시도
        
        우선순위:
        1. CSV 파일에서 정확한 행정구역명으로 검색
        2. CSV 파일에서 부분 매칭으로 검색
        3. 기존 하드코딩된 매핑 사용 (fallback)
        
        Args:
            region_name: 행정구역명
        
        Returns:
            cortarNo 또는 None
        """
        # 방법 1: CSV 파일에서 직접 검색
        region_codes = self._load_region_codes_from_csv()
        
        # 정확한 매칭 시도
        if region_name in region_codes:
            return region_codes[region_name]
        
        # 공백 제거 버전으로 시도
        region_name_no_space = region_name.replace(' ', '')
        if region_name_no_space in region_codes:
            return region_codes[region_name_no_space]
        
        # "경기도" 추가 버전으로 시도
        if not region_name.startswith('경기도 '):
            gyeonggi_name = f"경기도 {region_name}"
            if gyeonggi_name in region_codes:
                return region_codes[gyeonggi_name]
            if gyeonggi_name.replace(' ', '') in region_codes:
                return region_codes[gyeonggi_name.replace(' ', '')]
        
        # 부분 매칭 시도 (행정구역명이 CSV의 행정구역명에 포함되는 경우)
        for csv_region_name, csv_code in region_codes.items():
            # CSV 행정구역명이 입력된 행정구역명을 포함하거나, 그 반대인 경우
            if region_name in csv_region_name or csv_region_name in region_name:
                # 정확도 향상을 위해 주요 키워드 확인
                parsed = self.parse_region_name(region_name)
                csv_parsed = self.parse_region_name(csv_region_name)
                
                # 시/구/동이 모두 일치하는지 확인
                match = True
                if parsed.get("city") and csv_parsed.get("city"):
                    if parsed["city"] not in csv_parsed["city"] and csv_parsed["city"] not in parsed["city"]:
                        match = False
                if parsed.get("district") and csv_parsed.get("district"):
                    if parsed["district"] != csv_parsed["district"]:
                        match = False
                if parsed.get("dong") and csv_parsed.get("dong"):
                    if parsed["dong"] not in csv_parsed["dong"] and csv_parsed["dong"] not in parsed["dong"]:
                        match = False
                
                if match:
                    return csv_code
        
        # 방법 2: 기존 하드코딩된 매핑 사용 (fallback)
        parsed = self.parse_region_name(region_name)
        
        # 서울시 구 코드 매핑 (cortarNo 패턴 기반)
        # 예: 서울시 강서구 -> 1150010400 (11: 서울, 50: 강서구, 01: ?, 04: ?, 00: ?)
        seoul_district_codes = {
            "강서구": "50",  # 1150010400
            "강동구": "74",  # 1174010300
            "강남구": "68",  # 1168010100
            "강북구": "30",
            "관악구": "20",
            "광진구": "21",
            "구로구": "53",
            "금천구": "55",
            "노원구": "35",
            "도봉구": "32",
            "동대문구": "23",
            "동작구": "26",
            "마포구": "47",
            "서대문구": "41",
            "서초구": "65",
            "성동구": "20",  # 1120010900
            "성북구": "36",
            "송파구": "62",
            "양천구": "44",
            "영등포구": "56",
            "용산구": "17",
            "은평구": "38",
            "종로구": "11",
            "중구": "14",
            "중랑구": "24"
        }
        
        # 경기도 시 코드 매핑
        gyeonggi_city_codes = {
            "성남시": "13",
            "수원시": "11",
            "안양시": "17",
            "부천시": "53",
            "안산시": "31",
            "고양시": "52",
            "용인시": "46",
            "청주시": "11",
            "천안시": "41"
        }
        
        # 성남시 구 코드 매핑
        # 패턴 분석: 성남시 수정구 신흥동 -> 4113110100
        #           4113(경기도 성남시) + 1(수정구) + 1(?) + 01(신흥동) + 00
        seongnam_district_codes = {
            "수정구": "1",  # 4113 + 1 + 1 + 01 + 00
            "중원구": "2",
            "분당구": "3"
        }
        
        cortar_no = None
        
        # 서울시 처리
        if "서울" in region_name or (parsed.get("city") and "서울" in parsed["city"]):
            base_code = "11"  # 서울시
            
            if parsed.get("district"):
                district_name = parsed["district"]
                district_code = seoul_district_codes.get(district_name)
                
                if district_code:
                    if parsed.get("dong"):
                        # 동이 있으면 더 세부 코드 필요
                        # 패턴 분석: 서울시 강서구 가양동 -> 1150010400
                        #            서울시 강동구 상일동 -> 1174010300
                        #            서울시 성동구 금호동1가 -> 1120010900
                        # 패턴: 11 + 구코드(2자리) + 01 + 동코드(2자리) + 00
                        
                        # 특정 동명 매핑 (알려진 것만) - 숫자 추출보다 우선
                        dong_name = parsed["dong"]
                        dong_code = "01"  # 기본값
                        
                        # 동명 패턴 매칭 (부분 일치) - 우선순위 높음
                        if "금호" in dong_name and "1가" in dong_name:
                            dong_code = "09"  # 성동구 금호동1가: 1120010900
                        elif "상일" in dong_name:
                            dong_code = "03"  # 강동구 상일동: 1174010300
                        elif "가양" in dong_name:
                            dong_code = "04"  # 강서구 가양동: 1150010400
                        elif "신흥" in dong_name:
                            dong_code = "01"  # 성남시 수정구 신흥동: 4113110100
                        else:
                            # 동명에서 숫자 추출 시도
                            import re
                            dong_num_match = re.search(r'(\d+)', dong_name)
                            if dong_num_match:
                                dong_num = int(dong_num_match.group(1))
                                dong_code = f"{dong_num:02d}"
                        
                        cortar_no = f"{base_code}{district_code}01{dong_code}00"
                    else:
                        # 구만 있으면 구 코드 + 010400 (예: 서울시 강서구 -> 1150010400)
                        # 패턴 분석: 서울시 강서구 -> 1150010400
                        #            서울시 강동구 -> 1174010300 (상일동이 있지만 구만 있을 때는?)
                        # 구만 있을 때는 기본 동 코드를 사용 (01 + 04 + 00)
                        # 실제로는 구별로 다를 수 있지만, 일단 010400 패턴 사용
                        cortar_no = f"{base_code}{district_code}010400"
        
        # 경기도 성남시 처리
        elif "성남" in region_name or (parsed.get("city") and "성남" in parsed["city"]):
            base_code = "4113"  # 경기도 성남시
            
            if parsed.get("district"):
                district_name = parsed["district"]
                district_code = seongnam_district_codes.get(district_name)
                
                if district_code:
                    if parsed.get("dong"):
                        # 동이 있으면
                        # 패턴: 4113 + 구코드(1자리) + 1 + 동코드(2자리) + 00
                        # 예: 성남시 수정구 신흥동 -> 4113110100
                        dong_code = "01"  # 기본값
                        # 동명 매핑
                        dong_name = parsed["dong"]
                        if "신흥" in dong_name:
                            dong_code = "01"
                        elif "여수" in dong_name:
                            dong_code = "01"  # 성남시 중원구 여수동: 4113210100
                        
                        # 패턴: 4113(4자리) + 구코드(1자리) + 1(1자리) + 동코드(2자리) + 00(2자리) = 10자리
                        cortar_no = f"{base_code}{district_code}1{dong_code}00"
                    else:
                        # 구만 있으면
                        cortar_no = f"{base_code}{district_code}100000"
        
        # 경기도 수원시 처리
        elif "수원" in region_name or (parsed.get("city") and "수원" in parsed["city"]):
            base_code = "4111"  # 경기도 수원시
            cortar_no = f"{base_code}00000000"
        
        return cortar_no
    
    def get_region_info(self, region_name: str, debug: bool = False) -> Optional[Dict]:
        """
        행정구역명으로 지역 정보 조회
        
        Args:
            region_name: 행정구역명 (예: "성남시 수정구 신흥동")
            debug: 디버그 모드 (상세 로그 출력)
        
        Returns:
            지역 정보 딕셔너리 (cortarNo, 좌표 등) 또는 None
        """
        return self.api_client.search_region_info(region_name, debug=debug)
    
    def calculate_region_bounds(
        self,
        center_lat: float,
        center_lon: float,
        zoom: int = 14
    ) -> Tuple[float, float, float, float]:
        """
        지역의 경계 좌표 계산
        
        사용자가 제공한 URL 예시를 참고하여 넓은 영역을 설정합니다.
        예시: btm=37.4056195, lft=127.0763439, top=37.4889573, rgt=127.2222561
        중심: lat=37.4473, lon=127.1493
        
        Args:
            center_lat: 중심 위도
            center_lon: 중심 경도
            zoom: 줌 레벨
        
        Returns:
            (btm, lft, top, rgt) 튜플
        """
        # 정답지 API 예시를 참고하여 넓은 영역 설정
        # 정답지: btm=37.3799052, lft=127.0585439, top=37.4632716, rgt=127.2044561
        # 중심: lat=37.4216, lon=127.1315
        # 차이: top - btm = 37.4632716 - 37.3799052 ≈ 0.0834
        #       rgt - lft = 127.2044561 - 127.0585439 ≈ 0.1459
        # 동 단위 지역구를 커버하기 위해 충분히 넓은 영역 설정
        # 정답지 API와 동일한 비율로 설정
        lat_size = 0.0417  # 약 4.6km (위도 방향) - 정답지 API와 유사
        lon_size = 0.0730  # 약 6.5km (경도 방향) - 정답지 API와 유사
        
        btm = center_lat - lat_size
        lft = center_lon - lon_size
        top = center_lat + lat_size
        rgt = center_lon + lon_size
        
        return btm, lft, top, rgt
    
    def _find_tot_cnt_in_response(self, data: Dict) -> Optional[int]:
        """
        응답 데이터에서 totCnt를 재귀적으로 찾기
        
        Args:
            data: API 응답 데이터
        
        Returns:
            totCnt 값 또는 None
        """
        if isinstance(data, dict):
            # 직접 키 확인
            for key in ["totCnt", "totalCount", "total", "count", "totalCnt"]:
                if key in data:
                    value = data[key]
                    if isinstance(value, (int, str)):
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            pass
            
            # 중첩된 딕셔너리에서 재귀적으로 찾기
            for value in data.values():
                if isinstance(value, dict):
                    result = self._find_tot_cnt_in_response(value)
                    if result is not None:
                        return result
                elif isinstance(value, list) and len(value) > 0:
                    # 리스트의 첫 번째 항목에서 찾기
                    if isinstance(value[0], dict):
                        result = self._find_tot_cnt_in_response(value[0])
                        if result is not None:
                            return result
        
        return None
    
    def extract_properties_from_article_list(self, data: Dict, region_name: str, debug: bool = False, default_cortar_no: Optional[str] = None) -> List[Property]:
        """
        articleList API 응답에서 매물 정보 추출
        
        Args:
            data: API 응답 데이터
            region_name: 지역명
            debug: 디버그 모드
            default_cortar_no: 기본 cortarNo (URL 생성 시 사용한 값, 매물의 cortarNo가 없거나 다를 경우 사용)
        
        Returns:
            매물 정보 리스트
        """
        properties = []
        body = data.get("body", [])
        
        if debug:
            print(f"[DEBUG] extract_properties_from_article_list:")
            print(f"  body 타입: {type(body)}")
            print(f"  body 길이: {len(body) if isinstance(body, list) else 'N/A'}")
            if body and len(body) > 0:
                print(f"  첫 번째 항목 키: {list(body[0].keys()) if isinstance(body, list) else 'N/A'}")
        
        if not isinstance(body, list):
            if debug:
                print(f"[DEBUG] body가 리스트가 아닙니다: {type(body)}")
            return properties
        
        for idx, article in enumerate(body):
            try:
                atcl_no = article.get("atclNo", "")
                if not atcl_no:
                    if debug and idx < 3:
                        print(f"[DEBUG] 항목 {idx}: atclNo가 없음")
                    continue
                
                prc = article.get("prc", 0)
                price = int(prc) if prc else 0
                
                # tagList를 JSON 문자열로 변환
                tag_list = article.get("tagList", [])
                tag_list_str = ""
                if isinstance(tag_list, list):
                    import json
                    tag_list_str = json.dumps(tag_list, ensure_ascii=False)
                
                # cortarNo 처리: 매물의 cortarNo가 있으면 사용, 없거나 다를 경우 URL 생성 시 사용한 값 사용
                article_cortar_no = article.get("cortarNo", "")
                if not article_cortar_no and default_cortar_no:
                    # 매물의 cortarNo가 없으면 URL 생성 시 사용한 값 사용
                    final_cortar_no = default_cortar_no
                elif article_cortar_no and default_cortar_no:
                    # 매물의 cortarNo와 URL 생성 시 사용한 cortarNo가 다를 경우, URL 생성 시 사용한 값 사용
                    # (URL 생성 시 사용한 값이 더 정확함)
                    if article_cortar_no != default_cortar_no:
                        if debug and idx < 3:
                            print(f"[DEBUG] 항목 {idx}: cortarNo 불일치 - 매물={article_cortar_no}, URL생성={default_cortar_no}, URL생성값 사용")
                        final_cortar_no = default_cortar_no
                    else:
                        final_cortar_no = article_cortar_no
                else:
                    # default_cortar_no가 없으면 매물의 cortarNo 사용 (기존 동작)
                    final_cortar_no = str(article_cortar_no) if article_cortar_no else ""
                
                prop = Property(
                    item_id=str(atcl_no),
                    region_name=region_name,
                    complex_name=article.get("atclNm", ""),
                    property_type=article.get("rletTpNm", ""),
                    trade_type=article.get("tradTpNm", ""),
                    trade_type_code=article.get("tradTpCd", ""),
                    price=price,
                    price_display=article.get("hanPrc", ""),
                    latitude=float(article.get("lat", 0.0)),
                    longitude=float(article.get("lng", 0.0)),
                    min_mvi_fee=article.get("minMviFee", 0),
                    max_mvi_fee=article.get("maxMviFee", 0),
                    tour_exist=article.get("isVrExposed", False),
                    collected_at=datetime.now(),
                    lgeo="",
                    # 모든 추가 필드 추출
                    cortar_no=str(final_cortar_no),
                    atcl_stat_cd=article.get("atclStatCd", ""),
                    upr_rlet_tp_cd=article.get("uprRletTpCd", ""),
                    vrfc_tp_cd=article.get("vrfcTpCd", ""),
                    flr_info=article.get("flrInfo", ""),
                    rent_prc=int(article.get("rentPrc", 0)) if article.get("rentPrc") else 0,
                    spc1=article.get("spc1", ""),
                    spc2=article.get("spc2", ""),
                    direction=article.get("direction", ""),
                    atcl_cfm_ymd=article.get("atclCfmYmd", ""),
                    rep_img_url=article.get("repImgUrl", ""),
                    rep_img_tp_cd=article.get("repImgTpCd", ""),
                    rep_img_thumb=article.get("repImgThumb", ""),
                    atcl_fetr_desc=article.get("atclFetrDesc", ""),
                    tag_list=tag_list_str,
                    bild_nm=article.get("bildNm", ""),
                    minute=int(article.get("minute", 0)) if article.get("minute") else 0,
                    same_addr_cnt=int(article.get("sameAddrCnt", 0)) if article.get("sameAddrCnt") else 0,
                    same_addr_direct_cnt=int(article.get("sameAddrDirectCnt", 0)) if article.get("sameAddrDirectCnt") else 0,
                    same_addr_hash=article.get("sameAddrHash", ""),
                    same_addr_max_prc=article.get("sameAddrMaxPrc", ""),
                    same_addr_min_prc=article.get("sameAddrMinPrc", ""),
                    cpid=article.get("cpid", ""),
                    cp_nm=article.get("cpNm", ""),
                    cp_cnt=int(article.get("cpCnt", 0)) if article.get("cpCnt") else 0,
                    rltr_nm=article.get("rltrNm", ""),
                    direct_trad_yn=article.get("directTradYn", ""),
                    et_room_cnt=int(article.get("etRoomCnt", 0)) if article.get("etRoomCnt") else 0,
                    trade_price_han=article.get("tradePriceHan", ""),
                    trade_rent_price=int(article.get("tradeRentPrice", 0)) if article.get("tradeRentPrice") else 0,
                    trade_checked_by_owner=bool(article.get("tradeCheckedByOwner", False)),
                    dtl_addr_yn=article.get("dtlAddrYn", ""),
                    dtl_addr=article.get("dtlAddr", ""),
                    vr_url=article.get("vrUrl", ""),
                    is_safe_lessor_of_hug=bool(article.get("isSafeLessorOfHug", False))
                )
                properties.append(prop)
                
                if debug and idx < 3:
                    print(f"[DEBUG] 항목 {idx} 추출 성공: {atcl_no} - {article.get('atclNm', '')}")
            except Exception as e:
                if debug:
                    print(f"[DEBUG] 항목 {idx} 추출 오류: {str(e)}")
                continue
        
        if debug:
            print(f"[DEBUG] 총 추출된 매물: {len(properties)}개")
        
        return properties
    
    def collect_properties_by_region(
        self,
        region_name: str,
        rlet_tp_cd: str = "APT",
        trad_tp_cd: str = "A1",
        progress_callback=None,
        dprc_min: Optional[int] = None,
        dprc_max: Optional[int] = None,
        spc_min: Optional[int] = None,
        spc_max: Optional[int] = None
    ) -> Tuple[List[Property], List[Complex]]:
        """
        행정구역 기반 매물 수집 (새로운 크롤링 방법)
        
        이 메서드는 사용자가 네이버 부동산에서 "해당 지역만 보기"를 선택하고
        "매물목록"을 클릭했을 때 사용되는 API를 활용하여 모든 매물을 수집합니다.
        
        Args:
            region_name: 행정구역명 (예: "성남시 수정구 신흥동")
            rlet_tp_cd: 부동산 유형 코드 (APT, OPST, VL 등)
            trad_tp_cd: 거래 유형 코드 (A1: 매매, B1: 전세, B2: 월세)
            progress_callback: 진행 상황 콜백 함수 (current, total, message)
            dprc_min: 최소 가격 (만원 단위, 예: 80000 = 8억)
            dprc_max: 최대 가격 (만원 단위, 예: 130000 = 13억)
            spc_min: 최소 면적 (평 단위, 예: 33 = 33평)
            spc_max: 최대 면적 (평 단위, 예: 99 = 99평)
        
        Returns:
            (매물 리스트, 단지 리스트)
        """
        self.properties = []
        self.complexes = []
        
        # 1단계: 지역 정보 조회
        if progress_callback:
            progress_callback(0, 100, f"지역 정보 조회 중: {region_name}")
        
        # 문제점1 해결: .env의 REGION_CORTAR_NO 고정값을 무시하고, 각 region_name마다 자동으로 cortarNo 추출
        # 문제점2 해결: articleList API에서 직접 추출한 cortarNo를 우선 사용 (사용자 제공 URL과 동일한 방식)
        
        from src.config.env_loader import EnvConfig
        direct_coords = EnvConfig.get_region_coordinates()
        
        region_info = None
        
        # 방법 0: 행정구역명에서 cortarNo 자동 생성 시도 (가장 빠름)
        if progress_callback:
            progress_callback(0, 100, "행정구역명에서 cortarNo 자동 생성 시도...")
        
        generated_cortar_no = self.generate_cortar_no_from_region_name(region_name)
        if generated_cortar_no:
            print(f"[DEBUG] 행정구역명에서 생성한 cortarNo: {generated_cortar_no}")
            if progress_callback:
                progress_callback(1, 100, f"생성된 cortarNo: {generated_cortar_no}")
            
            # 생성된 cortarNo로 검증 시도
            try:
                # geopy로 좌표 얻기
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="naver_land_crawler")
                location = geolocator.geocode(region_name, country_codes="kr", timeout=10)
                
                if location:
                    test_lat = location.latitude
                    test_lon = location.longitude
                    
                    zoom = 14
                    lat_size = 0.042
                    lon_size = 0.073
                    btm = test_lat - lat_size
                    lft = test_lon - lon_size
                    top = test_lat + lat_size
                    rgt = test_lon + lon_size
                    
                    # 생성된 cortarNo로 API 호출하여 검증
                    test_data = self.api_client.get_article_list_by_region(
                        cortar_no=generated_cortar_no,
                        lat=test_lat,
                        lon=test_lon,
                        zoom=zoom,
                        btm=btm,
                        lft=lft,
                        top=top,
                        rgt=rgt,
                        rlet_tp_cd="APT",
                        trad_tp_cd="A1",
                        page=1
                    )
                    
                    if test_data.get("code") == "success":
                        body = test_data.get("body", [])
                        if body and len(body) > 0:
                            # body에서 실제 cortarNo 확인
                            actual_cortar_no = body[0].get("cortarNo")
                            if actual_cortar_no:
                                # 생성된 cortarNo와 실제 cortarNo 비교
                                if actual_cortar_no.startswith(generated_cortar_no[:6]) or generated_cortar_no.startswith(actual_cortar_no[:6]):
                                    if progress_callback:
                                        progress_callback(2, 100, f"✅ 생성된 cortarNo 검증 성공: {actual_cortar_no}")
                                    print(f"[DEBUG] 생성된 cortarNo 검증 성공: {actual_cortar_no} (생성: {generated_cortar_no})")
                                    
                                    region_info = {
                                        "cortarNo": actual_cortar_no,  # 실제 cortarNo 사용
                                        "lat": test_lat,
                                        "lon": test_lon,
                                        "regionName": region_name,
                                        "cortarNm": "",
                                        "cityNm": "",
                                        "dvsnNm": "",
                                        "secNm": ""
                                    }
            except Exception as e:
                print(f"[DEBUG] 생성된 cortarNo 검증 실패: {str(e)}")
        
        # 방법 1: get_cluster_list API로 cortarNo 조회 (보조 수단)
        if not region_info:
            if progress_callback:
                progress_callback(3, 100, "get_cluster_list API로 cortarNo 조회 시도...")
            
            region_info = self.get_region_info(region_name, debug=True)  # debug=True로 상세 로그 출력
        
        # 방법 2: geopy로 좌표 얻어서 articleList API에서 cortarNo 자동 추출 (보조 수단)
        if not region_info:
            if progress_callback:
                progress_callback(2, 100, "geopy로 좌표 획득 후 articleList API에서 cortarNo 자동 추출 시도...")
            
            zoom = 14
            lat_size = 0.042
            lon_size = 0.073
            
            # geopy로 좌표 획득 시도
            test_lat = None
            test_lon = None
            
            try:
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="naver_land_crawler")
                location = geolocator.geocode(region_name, country_codes="kr", timeout=10)
                
                if location:
                    test_lat = location.latitude
                    test_lon = location.longitude
                    
                    if progress_callback:
                        progress_callback(3, 100, f"좌표 획득: ({test_lat}, {test_lon})")
                    print(f"[DEBUG] geopy 좌표 획득: ({test_lat}, {test_lon})")
            except Exception as e:
                if progress_callback:
                    progress_callback(3, 100, f"geopy 좌표 획득 실패: {str(e)}")
                print(f"[DEBUG] geopy 좌표 획득 실패: {str(e)}")
            
            # geopy 실패 시 지역명 기반 대략적인 좌표 사용
            if not test_lat or not test_lon:
                if "서울" in region_name:
                    if "강서" in region_name:
                        test_lat, test_lon = 37.5500, 126.8500  # 강서구 대략 좌표
                    elif "강동" in region_name:
                        test_lat, test_lon = 37.5500, 127.1700
                    elif "강남" in region_name:
                        test_lat, test_lon = 37.5172, 127.0473
                    elif "성동" in region_name:
                        test_lat, test_lon = 37.5480, 127.0220
                    else:
                        test_lat, test_lon = 37.5665, 126.9780  # 서울시청 좌표
                elif "성남" in region_name:
                    test_lat, test_lon = 37.4201, 127.1266
                else:
                    test_lat, test_lon = 37.5665, 126.9780  # 기본 서울 좌표
                
                if progress_callback:
                    progress_callback(3, 100, f"지역명 기반 좌표 사용: ({test_lat}, {test_lon})")
                print(f"[DEBUG] 지역명 기반 좌표 사용: ({test_lat}, {test_lon})")
            
            if test_lat and test_lon:
                btm = test_lat - lat_size
                lft = test_lon - lon_size
                top = test_lat + lat_size
                rgt = test_lon + lon_size
                
                try:
                    if progress_callback:
                        progress_callback(4, 100, "articleList API 호출 중 (cortarNo 없이)...")
                    
                    test_data = self.api_client.get_article_list_by_region(
                        cortar_no="",  # cortarNo 없이 호출하여 자동으로 추출
                        lat=test_lat,
                        lon=test_lon,
                        zoom=zoom,
                        btm=btm,
                        lft=lft,
                        top=top,
                        rgt=rgt,
                        rlet_tp_cd="APT",
                        trad_tp_cd="A1",
                        page=1
                    )
                    
                    if test_data.get("code") == "success":
                        body = test_data.get("body", [])
                        if body and len(body) > 0:
                            # 각 매물에서 cortarNo 추출 (첫 번째 매물의 cortarNo 사용)
                            extracted_cortar_no = body[0].get("cortarNo")
                            if extracted_cortar_no:
                                if progress_callback:
                                    progress_callback(5, 100, f"✅ articleList API에서 cortarNo 자동 추출: {extracted_cortar_no}")
                                print(f"[DEBUG] articleList API에서 추출한 cortarNo: {extracted_cortar_no}")
                                
                                region_info = {
                                    "cortarNo": extracted_cortar_no,
                                    "lat": test_lat,
                                    "lon": test_lon,
                                    "regionName": region_name,
                                    "cortarNm": "",
                                    "cityNm": "",
                                    "dvsnNm": "",
                                    "secNm": ""
                                }
                            else:
                                if progress_callback:
                                    progress_callback(5, 100, "⚠️ articleList API 응답에 cortarNo가 없음")
                                print(f"[DEBUG] ⚠️ articleList API 응답에 cortarNo가 없음")
                        else:
                            if progress_callback:
                                progress_callback(5, 100, "⚠️ articleList API 응답에 매물이 없음")
                            print(f"[DEBUG] ⚠️ articleList API 응답에 매물이 없음")
                    else:
                        if progress_callback:
                            progress_callback(5, 100, f"⚠️ articleList API 응답 실패: {test_data.get('code')}")
                        print(f"[DEBUG] ⚠️ articleList API 응답 실패: {test_data.get('code')}")
                except Exception as e:
                    if progress_callback:
                        progress_callback(4, 100, f"articleList API 호출 실패: {str(e)}")
                    print(f"[DEBUG] articleList API 호출 실패: {str(e)}")
            
            if region_info:
                extracted_cortar_no = region_info.get("cortarNo")
                if extracted_cortar_no:
                    print(f"[DEBUG] get_cluster_list에서 추출한 cortarNo: {extracted_cortar_no}")
                    
                    # 검증: articleList API로 이 cortarNo가 유효한지 확인
                    try:
                        test_lat = region_info.get("lat")
                        test_lon = region_info.get("lon")
                        zoom = 14
                        lat_size = 0.042
                        lon_size = 0.073
                        btm = test_lat - lat_size
                        lft = test_lon - lon_size
                        top = test_lat + lat_size
                        rgt = test_lon + lon_size
                        
                        test_data = self.api_client.get_article_list_by_region(
                            cortar_no=extracted_cortar_no,
                            lat=test_lat,
                            lon=test_lon,
                            zoom=zoom,
                            btm=btm,
                            lft=lft,
                            top=top,
                            rgt=rgt,
                            rlet_tp_cd="APT",
                            trad_tp_cd="A1",
                            page=1
                        )
                        
                        if test_data.get("code") == "success":
                            body = test_data.get("body", [])
                            if body and len(body) > 0:
                                # body에서 실제 cortarNo 확인
                                actual_cortar_no = body[0].get("cortarNo")
                                if actual_cortar_no and actual_cortar_no != extracted_cortar_no:
                                    print(f"[DEBUG] ⚠️ cortarNo 불일치: get_cluster_list={extracted_cortar_no}, articleList={actual_cortar_no}")
                                    print(f"[DEBUG] articleList API의 cortarNo를 사용: {actual_cortar_no}")
                                    region_info["cortarNo"] = actual_cortar_no  # articleList의 cortarNo로 교체
                                else:
                                    print(f"[DEBUG] ✅ cortarNo 일치 확인: {extracted_cortar_no}")
                    except Exception as e:
                        print(f"[DEBUG] cortarNo 검증 실패: {str(e)}")
        
        if not region_info:
            error_msg = (
                f"지역 정보를 찾을 수 없습니다: {region_name}\n"
                f"\n가능한 원인:\n"
                f"  1. 행정구역명이 정확하지 않을 수 있습니다.\n"
                f"  2. Geopy 서비스에 접근할 수 없을 수 있습니다.\n"
                f"  3. 네이버 부동산 API에서 해당 지역 정보를 찾을 수 없을 수 있습니다.\n"
                f"\n해결 방법:\n"
                f"  방법 1: 행정구역명을 정확히 입력\n"
                f"    - 예: '성남시 수정구 신흥동'\n"
                f"    - '경기도'를 포함하여 입력해보세요 (예: '경기도 성남시 수정구 신흥동')\n"
                f"\n  방법 2: 인터넷 연결 확인 및 잠시 후 다시 시도\n"
                f"\n참고: 각 지역마다 자동으로 cortarNo를 추출합니다. .env의 REGION_CORTAR_NO는 무시됩니다."
            )
            raise Exception(error_msg)
        
        # 경고 메시지가 있는 경우 출력
        if "warning" in region_info:
            if progress_callback:
                progress_callback(3, 100, f"경고: {region_info['warning']}")
        
        cortar_no = region_info["cortarNo"]
        center_lat = region_info["lat"]
        center_lon = region_info["lon"]
        found_region_name = region_info.get("regionName", region_name)
        
        if progress_callback:
            progress_callback(5, 100, f"지역 코드: {cortar_no}, 좌표: ({center_lat}, {center_lon})")
            if found_region_name != region_name:
                progress_callback(6, 100, f"찾은 지역명: {found_region_name}")
        
        # 2단계: 경계 좌표 계산
        zoom = 14
        btm, lft, top, rgt = self.calculate_region_bounds(center_lat, center_lon, zoom)
        
        # 3단계: 첫 페이지 조회하여 총 매물 개수 확인
        # 핵심: totCnt는 첫 페이지 요청 시 필요하지 않음
        # 사용자가 제공한 URL 예시를 보면 totCnt=209가 파라미터로 있지만,
        # 실제로는 첫 페이지 요청 시 totCnt 없이 요청하고, 페이지네이션을 통해 모든 페이지 수집
        
        if progress_callback:
            progress_callback(10, 100, f"첫 페이지 조회 중... (경계: btm={btm:.6f}, lft={lft:.6f}, top={top:.6f}, rgt={rgt:.6f})")
            progress_callback(11, 100, f"총 매물 수는 페이지네이션을 통해 자동 추정")
        
        try:
            # 디버깅: 첫 페이지 요청 URL 구성
            import urllib.parse
            first_page_params = {
                "rletTpCd": rlet_tp_cd,
                "tradTpCd": trad_tp_cd,
                "z": str(zoom),
                "lat": str(center_lat),
                "lon": str(center_lon),
                "btm": str(btm),
                "lft": str(lft),
                "top": str(top),
                "rgt": str(rgt),
                "showR0": "",
                "cortarNo": cortar_no
            }
            # 첫 페이지는 totCnt 없이 요청
            first_page_url = f"https://m.land.naver.com/cluster/ajax/articleList?{urllib.parse.urlencode(first_page_params)}"
            if progress_callback:
                progress_callback(12, 100, f"[DEBUG] 첫 페이지 요청 URL: {first_page_url}")
            print(f"[DEBUG] 첫 페이지 요청 URL: {first_page_url}")
            
            # 첫 페이지 요청: totCnt 없이 요청
            # 사용자가 제공한 URL (page=1~11)을 그대로 사용하면 데이터가 잘 나옴
            # 따라서 totCnt는 첫 페이지 요청 시 필요하지 않고, 페이지네이션을 통해 추정
            first_page_data = self.api_client.get_article_list_by_region(
                cortar_no=cortar_no,
                lat=center_lat,
                lon=center_lon,
                zoom=zoom,
                btm=btm,
                lft=lft,
                top=top,
                rgt=rgt,
                rlet_tp_cd=rlet_tp_cd,
                trad_tp_cd=trad_tp_cd,
                page=1,
                tot_cnt=None,  # totCnt 없이 요청 (페이지네이션으로 추정)
                dprc_min=dprc_min,
                dprc_max=dprc_max,
                spc_min=spc_min,
                spc_max=spc_max
            )
            
            # API 응답 확인
            if first_page_data.get("code") != "success":
                error_msg = f"API 응답이 성공이 아닙니다: {first_page_data.get('code')}"
                if progress_callback:
                    progress_callback(15, 100, f"오류: {error_msg}")
                raise Exception(error_msg)
            
            # 디버깅: 첫 페이지 응답 로그 (전체 응답 구조 확인)
            if progress_callback:
                debug_msg = f"[DEBUG] 첫 페이지 응답: code={first_page_data.get('code')}, body길이={len(first_page_data.get('body', []))}, more={first_page_data.get('more', False)}"
                debug_msg += f", 응답totCnt={first_page_data.get('totCnt')}, data.totCnt={first_page_data.get('data', {}).get('totCnt')}"
                # 응답의 모든 키 확인
                debug_msg += f", 응답키={list(first_page_data.keys())}"
                progress_callback(18, 100, debug_msg)
            
            # 첫 페이지에서 매물 추출 (디버그 모드)
            # URL 생성 시 사용한 cortarNo를 전달하여 저장 시 일관성 유지
            first_page_properties = self.extract_properties_from_article_list(
                first_page_data, region_name, debug=True, default_cortar_no=cortar_no
            )
            self.properties.extend(first_page_properties)
            
            # 총 매물 개수 확인 (응답에서 추출하거나 body 길이로 추정)
            body = first_page_data.get("body", [])
            items_per_page = len(body)
            more = first_page_data.get("more", False)
            
            # totCnt 추출 시도
            # 핵심: totCnt는 첫 페이지 응답에 없을 수 있음
            # 사용자가 제공한 URL을 보면 totCnt=209가 파라미터로 있지만,
            # 실제로는 첫 페이지 요청 시 totCnt 없이 요청하고, 페이지네이션을 통해 모든 페이지 수집
            
            # 응답에서 totCnt 추출 시도 (여러 위치 확인)
            # 사용자가 제공한 URL 응답을 보면 totCnt 필드가 응답에 없을 수 있음
            # 따라서 응답의 모든 가능한 위치에서 확인
            tot_cnt = (
                first_page_data.get("totCnt") or
                first_page_data.get("data", {}).get("totCnt") or
                first_page_data.get("result", {}).get("totCnt") or
                first_page_data.get("totalCount") or
                first_page_data.get("total") or
                # 응답 전체를 순회하며 totCnt 찾기
                self._find_tot_cnt_in_response(first_page_data)
            )
            
            # totCnt를 정수로 변환
            if tot_cnt is not None:
                try:
                    tot_cnt = int(tot_cnt)
                    if progress_callback:
                        progress_callback(19, 100, f"첫 페이지 응답에서 totCnt 추출: {tot_cnt}")
                except (ValueError, TypeError):
                    tot_cnt = None
            
            if tot_cnt is None:
                # totCnt가 없으면 페이지네이션을 통해 추정
                # more=True이면 계속 수집, more=False이고 body < 20이면 마지막 페이지
                if progress_callback:
                    progress_callback(19, 100, f"totCnt 없음, 페이지네이션으로 모든 페이지 수집 (more={more}, body={items_per_page})")
                # 페이지네이션을 통해 totCnt 추정: 첫 페이지 body 길이와 more 필드로 추정
                # more=True이면 최소 20개 이상, more=False이고 body < 20이면 body 길이가 총 개수
                if not more and items_per_page < 20:
                    tot_cnt = items_per_page
                    if progress_callback:
                        progress_callback(19, 100, f"첫 페이지가 마지막 페이지로 추정: {tot_cnt}개")
                # more=True이면 페이지네이션을 통해 추정 (나중에 업데이트)
            
            if progress_callback:
                if tot_cnt:
                    progress_callback(20, 100, f"첫 페이지 수집 완료: {items_per_page}개 매물 (총 {tot_cnt}개 예상, more={more})")
                else:
                    progress_callback(20, 100, f"첫 페이지 수집 완료: {items_per_page}개 매물 (more={more}, 계속 수집 중...)")
            
            # 디버깅: 매물이 없으면 경고
            if items_per_page == 0:
                if progress_callback:
                    progress_callback(21, 100, f"[경고] 첫 페이지에 매물이 없습니다. API 응답: {first_page_data}")
        except Exception as e:
            error_msg = f"첫 페이지 조회 실패: {str(e)}"
            if progress_callback:
                progress_callback(15, 100, f"오류: {error_msg}")
            raise Exception(error_msg)
        
        # 4단계: 페이지네이션으로 나머지 페이지 수집
        # 핵심: 사용자가 제공한 URL처럼 page=1~11까지만 바꿔서 호출하면 됨
        # totCnt는 첫 페이지 응답에서 얻거나, 페이지네이션으로 추정
        if more or items_per_page >= 20:
            page = 2
            max_pages = 100  # 안전장치: 최대 100페이지까지
            
            # 이전 페이지들이 모두 20개였는지 추적
            all_previous_full = items_per_page == 20
            
            # totCnt가 있으면 총 페이지 수 계산
            if tot_cnt:
                estimated_total_pages = (tot_cnt + 19) // 20  # 올림 계산: 209 -> 11페이지
                max_pages = min(estimated_total_pages + 2, max_pages)  # 여유분 2페이지
                if progress_callback:
                    progress_callback(21, 100, f"총 {tot_cnt}개 매물 예상, 약 {estimated_total_pages}페이지 수집 예정")
            else:
                if progress_callback:
                    progress_callback(21, 100, f"totCnt 없음, more와 body 길이로 판단하여 수집")
            
            while page <= max_pages:
                if progress_callback:
                    if tot_cnt:
                        # totCnt 기반 진행률 계산
                        expected_total = tot_cnt
                        current_total = len(self.properties)
                        progress_pct = min(20 + int((current_total / expected_total) * 75), 95)
                    else:
                        # totCnt 없으면 페이지 기반 진행률
                        progress_pct = min(20 + int((page - 1) / max_pages * 75), 95)
                    
                    progress_callback(
                        progress_pct, 100,
                        f"페이지 {page} 수집 중... (현재 {len(self.properties)}개 매물" + 
                        (f"/{tot_cnt}개" if tot_cnt else "") + ")"
                    )
                
                try:
                    # 디버깅: 요청 파라미터 로그
                    if progress_callback:
                        debug_msg = f"[DEBUG] 페이지 {page} 요청: totCnt={tot_cnt}, 현재 수집된 매물={len(self.properties)}"
                        if tot_cnt:
                            estimated_pages = (tot_cnt + 19) // 20
                            debug_msg += f", 예상 페이지={estimated_pages}"
                        progress_callback(progress_pct, 100, debug_msg)
                    
                    # 디버깅: 실제 요청 URL 구성 (사용자가 제공한 URL 형식과 비교)
                    import urllib.parse
                    request_params = {
                        "rletTpCd": rlet_tp_cd,
                        "tradTpCd": trad_tp_cd,
                        "z": str(zoom),
                        "lat": str(center_lat),
                        "lon": str(center_lon),
                        "btm": str(btm),
                        "lft": str(lft),
                        "top": str(top),
                        "rgt": str(rgt),
                        "showR0": "",
                        "cortarNo": cortar_no
                    }
                    if tot_cnt:
                        request_params["totCnt"] = str(tot_cnt)
                    if page > 1:
                        request_params["page"] = str(page)
                    
                    request_url = f"https://m.land.naver.com/cluster/ajax/articleList?{urllib.parse.urlencode(request_params)}"
                    if progress_callback:
                        progress_callback(progress_pct, 100, f"[DEBUG] 페이지 {page} 요청 URL: {request_url}")
                    
                    # totCnt가 있으면 각 페이지 요청 시 전달
                    # 사용자가 제공한 URL처럼 totCnt를 파라미터로 포함
                    # totCnt가 없으면 None으로 전달 (API가 자동 계산)
                    page_data = self.api_client.get_article_list_by_region(
                        cortar_no=cortar_no,
                        lat=center_lat,
                        lon=center_lon,
                        zoom=zoom,
                        btm=btm,
                        lft=lft,
                        top=top,
                        rgt=rgt,
                        rlet_tp_cd=rlet_tp_cd,
                        trad_tp_cd=trad_tp_cd,
                        page=page,
                        tot_cnt=tot_cnt,  # totCnt 전달 (있으면 포함, 없으면 None)
                        dprc_min=dprc_min,
                        dprc_max=dprc_max,
                        spc_min=spc_min,
                        spc_max=spc_max
                    )
                    
                    # 디버깅: API 응답 로그
                    response_code = page_data.get("code")
                    response_tot_cnt = page_data.get("totCnt")
                    page_body = page_data.get("body", [])
                    more = page_data.get("more", False)
                    
                    if progress_callback:
                        debug_msg = f"[DEBUG] 페이지 {page} 응답: code={response_code}, body길이={len(page_body) if page_body else 0}, more={more}, 응답totCnt={response_tot_cnt}"
                        progress_callback(progress_pct, 100, debug_msg)
                    
                    # API 응답 확인
                    if response_code != "success":
                        if progress_callback:
                            progress_callback(progress_pct, 100, f"페이지 {page} 응답 오류: {response_code}, 전체 응답: {page_data}")
                        break
                    
                    # 응답에서 totCnt 업데이트 (있으면) - 먼저 확인
                    # 두 번째 페이지부터는 첫 페이지에서 추정한 totCnt를 사용하여 요청
                    if response_tot_cnt and not tot_cnt:
                        try:
                            tot_cnt = int(response_tot_cnt)
                            if progress_callback:
                                progress_callback(progress_pct, 100, f"페이지 {page}: 총 매물 수 확인됨 ({tot_cnt}개)")
                        except (ValueError, TypeError):
                            pass
                    
                    # totCnt가 없으면 페이지네이션을 통해 추정
                    # 현재까지 수집된 매물 수와 more 필드로 추정
                    if not tot_cnt:
                        if not more and len(page_body) < 20:
                            # more=False이고 body < 20이면 마지막 페이지
                            # 현재까지 수집된 매물 수가 총 개수
                            tot_cnt = len(self.properties)
                            if progress_callback:
                                progress_callback(progress_pct, 100, f"페이지 {page}: totCnt 추정 완료 ({tot_cnt}개, 마지막 페이지)")
                        elif not more and len(page_body) == 20:
                            # more=False이고 body=20이면 다음 페이지가 있을 수 있음
                            # 한 페이지 더 시도
                            pass
                    
                    # body가 0개면 종료 (totCnt가 없거나 예상 페이지 수를 넘었을 때만)
                    if len(page_body) == 0:
                        if tot_cnt:
                            estimated_total_pages = (tot_cnt + 19) // 20
                            if page <= estimated_total_pages:
                                if progress_callback:
                                    progress_callback(progress_pct, 100, f"페이지 {page}: 빈 페이지이지만 예상 페이지 수 이내 ({page}/{estimated_total_pages}), 다음 페이지 시도...")
                                page += 1
                                continue
                        if progress_callback:
                            progress_callback(progress_pct, 100, f"페이지 {page}: 빈 페이지")
                        break
                    
                    # 매물 추출 및 추가 (중요: 종료 조건 체크 전에 먼저 추가)
                    # URL 생성 시 사용한 cortarNo를 전달하여 저장 시 일관성 유지
                    page_properties = self.extract_properties_from_article_list(
                        page_data, region_name, default_cortar_no=cortar_no
                    )
                    if not page_properties:
                        # totCnt가 있으면 예상 페이지 수까지는 계속 시도
                        if tot_cnt:
                            estimated_total_pages = (tot_cnt + 19) // 20
                            if page <= estimated_total_pages:
                                if progress_callback:
                                    progress_callback(progress_pct, 100, f"페이지 {page}: 매물 추출 실패했지만 예상 페이지 수 이내 ({page}/{estimated_total_pages}), 다음 페이지 시도...")
                                page += 1
                                continue
                        if progress_callback:
                            progress_callback(progress_pct, 100, f"페이지 {page}: 매물 추출 실패 (body는 있지만 추출된 매물 없음)")
                        break
                    
                    # 디버깅: 추출된 매물 수 로그
                    if progress_callback:
                        progress_callback(progress_pct, 100, f"[DEBUG] 페이지 {page}: 추출된 매물 {len(page_properties)}개")
                    
                    # 매물 추가 (중요: 종료 조건 체크 전에 먼저 추가)
                    self.properties.extend(page_properties)
                    
                    # totCnt 기반 종료 조건 확인 (매물 추가 후에 체크)
                    if tot_cnt:
                        # 수집한 매물 수가 totCnt에 도달했는지 확인 (매물 추가 후)
                        if len(self.properties) >= tot_cnt:
                            if progress_callback:
                                progress_callback(progress_pct, 100, f"페이지 {page}: 목표 매물 수 도달 ({len(self.properties)}/{tot_cnt})")
                            break
                        
                        # totCnt 기반으로 필요한 페이지 수 계산
                        estimated_total_pages = (tot_cnt + 19) // 20  # 209 -> 11페이지
                        # 예상 페이지 수에 도달했고 body < 20이면 종료 (page=11에서 body=9개면 종료)
                        if page >= estimated_total_pages and len(page_body) < 20:
                            if progress_callback:
                                progress_callback(progress_pct, 100, f"페이지 {page}: 예상 페이지 수 도달 및 body < 20 (예상 {estimated_total_pages}페이지, 현재 {len(self.properties)}/{tot_cnt}개)")
                            break
                    
                    # more 필드와 body 길이 기반 종료 조건 (totCnt가 없을 때만 사용)
                    more = page_data.get("more", False)
                    
                    # totCnt가 없을 때: more=False이고 body < 20이면 종료
                    # 하지만 이전 페이지들이 모두 20개였다면 한 페이지 더 시도
                    if not tot_cnt:
                        if not more and len(page_body) < 20:
                            # 이전 페이지들이 모두 20개였는지 확인
                            if all_previous_full:
                                # 이전 페이지들이 모두 20개였고 현재 < 20이고 more=False
                                # 실제로는 더 많은 페이지가 있을 수 있으므로 한 페이지 더 시도
                                if progress_callback:
                                    progress_callback(progress_pct, 100, f"페이지 {page}: more=False이고 body < 20이지만 이전 페이지가 모두 20개였으므로 한 페이지 더 시도...")
                                all_previous_full = False  # 다음 반복에서는 이 조건 사용 안 함
                            else:
                                # 이전 페이지가 20개가 아니었거나 이미 한 페이지 더 시도했으므로 종료
                                if progress_callback:
                                    progress_callback(progress_pct, 100, f"페이지 {page}: 마지막 페이지 (more={more}, body={len(page_body)})")
                                break
                        elif len(page_body) == 20:
                            # body가 20개면 다음 페이지가 있을 가능성이 높음
                            all_previous_full = True
                    
                    page += 1
                    
                except Exception as e:
                    if progress_callback:
                        progress_callback(progress_pct, 100, f"페이지 {page} 조회 오류: {str(e)}")
                    break
        
        # 5단계: 중복 제거
        if progress_callback:
            progress_callback(95, 100, "중복 제거 중...")
        
        unique_properties = {}
        for prop in self.properties:
            if prop.item_id not in unique_properties:
                unique_properties[prop.item_id] = prop
        
        self.properties = list(unique_properties.values())
        
        if progress_callback:
            progress_callback(100, 100, f"수집 완료: 매물 {len(self.properties)}개")
        
        return self.properties, self.complexes

