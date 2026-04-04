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
    
    @staticmethod
    def normalize_region_name(region_name: str) -> str:
        """
        지역명 정규화 (서울시 → 서울특별시 등)
        
        Args:
            region_name: 원본 지역명
        
        Returns:
            정규화된 지역명
        """
        normalized = region_name.strip()
        
        # 서울시 → 서울특별시 변환
        if "서울시" in normalized and "서울특별시" not in normalized:
            normalized = normalized.replace("서울시", "서울특별시")
        
        return normalized
    
    def parse_region_name(self, region_name: str) -> Dict[str, Optional[str]]:
        """
        행정구역명을 파싱하여 시/도, 시/군/구, 읍/면/동 추출
        
        Args:
            region_name: 행정구역명 (예: "서울시 강서구", "성남시 수정구 신흥동")
        
        Returns:
            {"city": "서울시", "district": "강서구", "dong": "가양동", "province": None}
        """
        import re
        
        # 지역명 정규화 (서울시 → 서울특별시)
        region_name = self.normalize_region_name(region_name)
        
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
                city = "서울특별시"  # 정규화: 서울시 → 서울특별시
            elif province == "경기도":
                # 경기도는 city가 따로 있음 (성남시, 수원시 등)
                pass
        
        # city가 "서울시"로 파싱된 경우 "서울특별시"로 정규화
        if city == "서울시":
            city = "서울특별시"
        
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
        # 지역명 정규화 (서울시 → 서울특별시)
        region_name = self.normalize_region_name(region_name)
        
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
    
    def extract_properties_from_fin_article_list(
        self,
        data: Dict,
        region_name: str,
        complex_no: str = "",
        dprc_min: Optional[int] = None,
        dprc_max: Optional[int] = None,
        spc_min: Optional[float] = None,
        spc_max: Optional[float] = None
    ) -> List[Property]:
        """
        fin.land.naver.com API 응답에서 매물 정보 추출
        (extract_properties_from_article_list의 신 API 대응 버전)
        """
        _TRADE_NAMES = {"A1": "매매", "B1": "전세", "B2": "월세", "B3": "단기임대"}

        def _price_han(won: int, rent_won: int, ttype: str) -> str:
            if ttype in ("B2", "B3"):
                dep = won // 100000000
                dep_man = (won % 100000000) // 10000
                rnt = rent_won // 10000
                dep_str = (f"{dep}억 {dep_man:,}만" if dep and dep_man
                           else f"{dep}억" if dep else f"{dep_man:,}만")
                return f"{dep_str}/{rnt:,}만"
            eok = won // 100000000
            man = (won % 100000000) // 10000
            if eok and man:
                return f"{eok}억 {man:,}만"
            elif eok:
                return f"{eok}억"
            return f"{man:,}만"

        properties = []
        if not data.get("isSuccess"):
            return properties

        items = data.get("result", {}).get("list", [])

        for item in items:
            try:
                # representativeArticleInfo가 공유 기본 데이터 소스
                # (supplySpace m², address.coordinates, complexName, brokerInfo 등은 여기에만 있음)
                rep = item.get("representativeArticleInfo", {})
                if not rep:
                    continue

                dup_info = item.get("duplicatedArticleInfo", {})

                # rep에서 공유 필드 추출
                rep_space = rep.get("spaceInfo", {})
                supply_space = float(rep_space.get("supplySpace", 0) or 0)
                exclusive_space = float(rep_space.get("exclusiveSpace", 0) or 0)

                # 면적 필터 (공급면적 m²)
                if spc_min is not None and supply_space < spc_min:
                    continue
                if spc_max is not None and supply_space > spc_max:
                    continue

                article_no = rep.get("articleNumber", "")
                if not article_no:
                    continue

                trade_code = rep.get("tradeType", "A1")
                price_info = rep.get("priceInfo", {})

                deal_won = int(price_info.get("dealPrice", 0) or 0)
                rent_won = int(price_info.get("rentPrice", 0) or 0)
                warranty_won = int(price_info.get("warrantyPrice", 0) or 0)

                if trade_code == "A1":
                    price_man = deal_won // 10000
                    display_won = deal_won
                elif trade_code == "B1":
                    price_man = warranty_won // 10000
                    display_won = warranty_won
                else:  # B2, B3
                    price_man = warranty_won // 10000
                    display_won = warranty_won

                # 가격 필터 (만원 단위)
                if dprc_min is not None and price_man < dprc_min:
                    continue
                if dprc_max is not None and price_man > dprc_max:
                    continue

                rep_coords = rep.get("address", {}).get("coordinates", {})
                lat = float(rep_coords.get("yCoordinate", 0.0) or 0.0)
                lon = float(rep_coords.get("xCoordinate", 0.0) or 0.0)
                complex_name = rep.get("complexName", "")
                broker = rep.get("brokerInfo", {})
                media = rep.get("articleMediaDto", rep.get("articleMedia", {}))
                detail = rep.get("articleDetail", {})
                verif = rep.get("verificationInfo", {})
                rep_mgmt = int(price_info.get("managementFeeAmount", 0) or 0)

                prop = Property(
                    item_id=str(article_no),
                    region_name=region_name,
                    complex_name=complex_name,
                    property_type="아파트",
                    trade_type=_TRADE_NAMES.get(trade_code, trade_code),
                    trade_type_code=trade_code,
                    price=price_man,
                    price_display=_price_han(display_won, rent_won, trade_code),
                    latitude=lat,
                    longitude=lon,
                    min_mvi_fee=rep_mgmt // 10000,
                    max_mvi_fee=rep_mgmt // 10000,
                    tour_exist=bool(media.get("isVrExposed", False)),
                    collected_at=datetime.now(),
                    lgeo=str(complex_no),
                    cortar_no="",
                    flr_info=detail.get("floorInfo", ""),
                    rent_prc=rent_won // 10000,
                    spc1=str(supply_space),
                    spc2=str(exclusive_space),
                    direction=detail.get("direction", ""),
                    atcl_cfm_ymd=verif.get("articleConfirmDate", ""),
                    bild_nm=rep.get("dongName", ""),
                    cpid=broker.get("cpId", ""),
                    cp_nm=broker.get("cpId", ""),
                    rltr_nm=broker.get("brokerName", ""),
                    direct_trad_yn="Y" if detail.get("directTrade") else "N",
                    is_safe_lessor_of_hug=bool(detail.get("isSafeLessorOfHug", False)),
                    cp_cnt=dup_info.get("realtorCount", 0),
                    same_addr_cnt=dup_info.get("realtorCount", 0),
                )
                properties.append(prop)
            except Exception:
                continue

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
        
        # 방법 0: CSV에서 cortarNo 조회 + geopy 좌표 (가장 빠름, 검증 불필요 — 정부 공식 데이터)
        if progress_callback:
            progress_callback(0, 100, "행정구역명에서 cortarNo 자동 생성 시도...")

        generated_cortar_no = self.generate_cortar_no_from_region_name(region_name)
        if generated_cortar_no:
            print(f"[DEBUG] 행정구역명에서 생성한 cortarNo: {generated_cortar_no}")
            coords_lat, coords_lon = None, None
            try:
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="naver_land_crawler")
                location = geolocator.geocode(region_name, country_codes="kr", timeout=10)
                if location:
                    coords_lat, coords_lon = location.latitude, location.longitude
                    print(f"[DEBUG] geopy 좌표: ({coords_lat}, {coords_lon})")
            except Exception as e:
                print(f"[DEBUG] geopy 실패: {e}")

            if not coords_lat:
                # 지역명 기반 기본 좌표 (geopy 실패 시)
                if "서울" in region_name:
                    coords_lat, coords_lon = 37.5665, 126.9780
                elif "성남" in region_name:
                    coords_lat, coords_lon = 37.4201, 127.1266
                elif "경기" in region_name:
                    coords_lat, coords_lon = 37.4138, 127.5183
                else:
                    coords_lat, coords_lon = 37.5665, 126.9780
                print(f"[DEBUG] 기본 좌표 사용: ({coords_lat}, {coords_lon})")

            region_info = {
                "cortarNo": generated_cortar_no,
                "lat": coords_lat,
                "lon": coords_lon,
                "regionName": region_name,
                "cortarNm": "",
                "cityNm": "",
                "dvsnNm": "",
                "secNm": ""
            }
        
        # 방법 1: get_cluster_list API로 cortarNo 조회 (보조 수단)
        if not region_info:
            if progress_callback:
                progress_callback(3, 100, "get_cluster_list API로 cortarNo 조회 시도...")
            
            region_info = self.get_region_info(region_name, debug=True)  # debug=True로 상세 로그 출력
        
        # (방법 2 제거됨: m.land.naver.com/cluster/ajax/articleList는 null을 반환하여 폐기됨)
        
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
        
        # 행정구역명에서 매칭한 값만 사용 (하드코딩된 알려진 지역 정보 사용하지 않음)
        cortar_no = region_info["cortarNo"]
        center_lat = region_info["lat"]
        center_lon = region_info["lon"]
        found_region_name = region_info.get("regionName", region_name)
        
        if progress_callback:
            progress_callback(5, 100, f"지역 코드: {cortar_no}, 좌표: ({center_lat}, {center_lon})")
            if found_region_name != region_name:
                progress_callback(6, 100, f"찾은 지역명: {found_region_name}")
        
        # 2단계: 경계 좌표 계산
        # 동 단위일 때는 줌 레벨 15 사용 (제공된 URL 예시: z=15)
        parsed = self.parse_region_name(region_name)
        zoom = 15 if parsed.get("dong") else 14  # 동이 있으면 15, 없으면 14
        btm, lft, top, rgt = self.calculate_region_bounds(center_lat, center_lon, zoom)
        
        # 3단계: fin.land.naver.com complexClusters로 단지 번호 목록 조회
        if progress_callback:
            progress_callback(10, 100, f"단지 목록 조회 중... (cortarNo: {cortar_no})")

        trade_types_list = [t for t in trad_tp_cd.split(":") if t]

        try:
            cluster_data = self.api_client.get_complex_clusters_fin(
                btm=btm,
                lft=lft,
                top=top,
                rgt=rgt,
                trade_types=trade_types_list,
                spc_min=float(spc_min) if spc_min is not None else None,
                spc_max=float(spc_max) if spc_max is not None else None,
                precision=15
            )
            if not cluster_data.get("isSuccess"):
                raise Exception(f"complexClusters 응답 실패: isSuccess=False")

            # 응답 구조에 따라 리스트 추출 (complexes 또는 list 키)
            result_data = cluster_data.get("result", {})
            complex_list = (
                result_data.get("complexes")
                or result_data.get("list")
                or result_data.get("clusters")
                or []
            )
            if not isinstance(complex_list, list):
                complex_list = []

            if progress_callback:
                progress_callback(15, 100, f"단지 {len(complex_list)}개 발견, 매물 수집 시작...")
        except Exception as e:
            raise Exception(f"단지 목록 조회 실패: {str(e)}")

        # 4단계: 각 단지별 fin.land.naver.com POST API로 매물 조회
        total_complexes = len(complex_list)

        for idx, cluster in enumerate(complex_list):
            # complexClusters 응답에서 complexNumber 추출
            complex_no = str(
                cluster.get("complexNumber")
                or cluster.get("complexNo")
                or cluster.get("id")
                or ""
            )
            if not complex_no:
                continue

            if progress_callback:
                pct = 15 + int((idx / max(total_complexes, 1)) * 75)
                progress_callback(pct, 100, f"단지 {idx+1}/{total_complexes} 수집 중 (complexNo: {complex_no})...")

            # cursor 기반 페이지네이션
            last_info_cursor: list = []
            while True:
                try:
                    page_data = self.api_client.get_complex_article_list_fin(
                        complex_no=complex_no,
                        trade_types=trade_types_list,
                        last_info=last_info_cursor,
                        size=30
                    )
                    page_props = self.extract_properties_from_fin_article_list(
                        page_data,
                        region_name,
                        complex_no=complex_no,
                        dprc_min=dprc_min,
                        dprc_max=dprc_max,
                        spc_min=float(spc_min) if spc_min is not None else None,
                        spc_max=float(spc_max) if spc_max is not None else None
                    )
                    self.properties.extend(page_props)

                    result = page_data.get("result", {})
                    if not result.get("hasNextPage"):
                        break
                    last_info_cursor = result.get("lastInfo", [])
                    if not last_info_cursor:
                        break
                except Exception:
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

