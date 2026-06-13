"""
네이버 부동산 API 클라이언트
"""
from curl_cffi import requests  # Chrome TLS fingerprint 필요 (Naver 봇 차단 우회)
import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ApiConfig:
    """API 설정"""
    base_url: str = "https://fin.land.naver.com"
    min_delay: float = 0.2  # API 호출 간 최소 딜레이 (초) — 너무 짧으면 429 차단 위험
    timeout: int = 10  # 타임아웃 (초)
    max_retries: int = 3  # 최대 재시도 횟수


class NaverLandApiClient:
    """네이버 부동산 API 클라이언트"""
    
    def __init__(self, config: Optional[ApiConfig] = None):
        self.config = config or ApiConfig()
        self.session = requests.Session(impersonate="chrome131")
        self.last_request_time = 0

        # 기본 헤더 설정
        self.session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://fin.land.naver.com/",
            "Origin": "https://fin.land.naver.com",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        })
    
    def _wait_if_needed(self):
        """필요한 경우 딜레이 적용"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.min_delay:
            time.sleep(self.config.min_delay - elapsed)
        self.last_request_time = time.time()
    
    def get_cluster_list(
        self,
        lat: float,
        lon: float,
        zoom: int,
        btm: float,
        lft: float,
        top: float,
        rgt: float,
        rlet_tp_cd: str = "APT:JGC",
        trad_tp_cd: str = "A1",
        p_cortar_no: str = "",
        addon: str = "COMPLEX",
        b_addon: Optional[str] = None,
        is_only_isale: bool = False
    ) -> Dict:
        """
        클러스터 목록 조회
        
        Args:
            lat: 중심 위도
            lon: 중심 경도
            zoom: 줌 레벨
            btm: 하단 경계 위도
            lft: 왼쪽 경계 경도
            top: 상단 경계 위도
            rgt: 오른쪽 경계 경도
            rlet_tp_cd: 부동산 유형 코드
            trad_tp_cd: 거래 유형 코드
            p_cortar_no: 상위 지역 코드
            addon: 추가 정보 타입
            is_only_isale: 전매만 조회 여부
        
        Returns:
            API 응답 데이터
        """
        url = f"{self.config.base_url}/cluster/clusterList"
        
        params = {
            "view": "atcl",
            "rletTpCd": rlet_tp_cd,
            "tradTpCd": trad_tp_cd,
            "z": zoom,
            "lat": lat,
            "lon": lon,
            "btm": btm,
            "lft": lft,
            "top": top,
            "rgt": rgt,
            "pCortarNo": p_cortar_no,
            "addon": addon,
            "isOnlyIsale": "true" if is_only_isale else "false"
        }
        
        # 클러스터 클릭 시 자동 호출되는 API 방식 (방법 A)
        if b_addon:
            params["bAddon"] = b_addon
        
        # 딜레이 적용
        self._wait_if_needed()
        
        # 재시도 로직
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 지수 백오프
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API 호출 실패: {str(e)}")
        
        raise Exception("API 호출 실패: 최대 재시도 횟수 초과")
    
    def _ensure_fin_session(self):
        """fin.land.naver.com 세션 쿠키 초기화 (PROP_TEST_ID 등)"""
        if not getattr(self, '_fin_session_initialized', False):
            try:
                self.session.get(
                    "https://fin.land.naver.com/",
                    timeout=self.config.timeout,
                    allow_redirects=True
                )
                self._fin_session_initialized = True
                time.sleep(1.0)
            except Exception:
                self._fin_session_initialized = True  # 실패해도 계속 진행

    def get_complex_clusters_fin(
        self,
        btm: float,
        lft: float,
        top: float,
        rgt: float,
        trade_types: Optional[list] = None,
        spc_min: Optional[float] = None,
        spc_max: Optional[float] = None,
        real_estate_types: Optional[list] = None,
        precision: int = 15
    ) -> Dict:
        """
        fin.land.naver.com POST API로 범위 내 단지 목록 조회
        (m.land.naver.com/cluster/clusterList의 fin API 대체)

        Args:
            btm/lft/top/rgt: 지도 경계 좌표
            trade_types: 거래 유형 목록 (기본: ["A1"])
            spc_min/spc_max: 공급면적 범위 m²
            real_estate_types: 부동산 유형 (기본: ["A01","A04","B01"])
            precision: 클러스터 정밀도 (높을수록 개별 단지, 기본: 15)

        Returns:
            {"isSuccess": bool, "result": {"list": [{"complexNumber":..., ...}]}}
        """
        url = "https://fin.land.naver.com/front-api/v1/complex/complexClusters"
        _empty = {"isSuccess": False, "result": {"list": []}}

        space_filter: Dict = {}
        if spc_min is not None:
            space_filter["min"] = spc_min
        if spc_max is not None:
            space_filter["max"] = spc_max

        body = {
            "filter": {
                "tradeTypes": trade_types or ["A1"],
                "realEstateTypes": real_estate_types or ["A01", "A04", "B01"],
                "roomCount": [],
                "bathRoomCount": [],
                "optionTypes": [],
                "moveInTypes": [],
                "space": space_filter if space_filter else {"min": 0, "max": 200},
                "filtersExclusiveSpace": False,
                "floorTypes": [],
                "directionTypes": [],
                "hasArticlePhoto": False,
                "isAuthorizedByOwner": False,
                "parkingTypes": [],
                "entranceTypes": [],
                "hasArticle": False
            },
            "boundingBox": {
                "left": lft,
                "right": rgt,
                "top": top,
                "bottom": btm
            },
            "precision": precision,
            "userChannelType": "PC"
        }

        self._ensure_fin_session()
        self._wait_if_needed()

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(url, json=body, headers={"Content-Type": "application/json"}, timeout=self.config.timeout)
                if response.status_code == 429:
                    logger.warning("complexClusters 429 rate limit — 빈 결과 반환 (수집 누락 가능)")
                    return _empty
                response.raise_for_status()
                result = response.json()
                return result if result is not None else _empty
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                else:
                    logger.warning(f"complexClusters 재시도 소진 — 빈 결과 반환 (수집 누락 가능): {e}")
                    return _empty

        return _empty

    def get_complex_article_list_fin(
        self,
        complex_no: str,
        trade_types: Optional[list] = None,
        last_info: Optional[list] = None,
        pyeong_types: Optional[list] = None,
        dong_numbers: Optional[list] = None,
        size: int = 30
    ) -> Dict:
        """
        fin.land.naver.com POST API로 단지별 매물 목록 조회
        (m.land.naver.com/cluster/ajax/articleList 대체)

        Args:
            complex_no: 단지 번호
            trade_types: 거래 유형 목록 (예: ["A1"], ["A1","B1"])
            last_info: 페이지네이션 커서 (이전 응답의 lastInfo 값)
            pyeong_types: 평형 번호 목록 (빈 배열이면 전체)
            dong_numbers: 동 번호 목록 (빈 배열이면 전체)
            size: 페이지당 매물 수 (최대 30)

        Returns:
            {"isSuccess": bool, "result": {"list": [...], "hasNextPage": bool, "totalCount": int, "lastInfo": [...]}}
        """
        url = "https://fin.land.naver.com/front-api/v1/complex/article/list"
        _empty = {"isSuccess": False, "result": {"list": [], "hasNextPage": False, "totalCount": 0, "lastInfo": []}}

        body = {
            "size": size,
            "complexNumber": str(complex_no),
            "tradeTypes": trade_types or ["A1"],
            "pyeongTypes": pyeong_types or [],
            "dongNumbers": dong_numbers or [],
            "userChannelType": "PC",
            "articleSortType": "RANKING_DESC",
            "lastInfo": last_info or []
        }

        self._ensure_fin_session()
        self._wait_if_needed()

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                    timeout=self.config.timeout
                )
                if response.status_code == 429:
                    # rate limit — IP 차단 상태에서 재시도는 의미 없음, 즉시 반환
                    logger.warning(f"article/list 429 rate limit (complex={complex_no}) — 빈 결과 반환 (수집 누락 가능)")
                    return _empty
                response.raise_for_status()
                result = response.json()
                if result is None:
                    return _empty
                return result
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                else:
                    logger.warning(f"article/list 재시도 소진 (complex={complex_no}) — 빈 결과 반환 (수집 누락 가능): {e}")
                    return _empty

        return _empty

    def get_cluster_articles(
        self,
        item_id: str,
        lgeo: str,
        lat: float,
        lon: float,
        zoom: int,
        btm: float,
        lft: float,
        top: float,
        rgt: float,
        rlet_tp_cd: str = "APT",
        trad_tp_cd: str = "A1",
        map_key: str = "",
        cortar_no: str = "",
        show_r0: str = ""
    ) -> Dict:
        """
        클러스터 내부의 개별 매물 목록 조회
        
        Args:
            item_id: 클러스터의 itemId (lgeo와 동일)
            lgeo: 지역 지오코드
            lat: 중심 위도
            lon: 중심 경도
            zoom: 줌 레벨
            btm: 하단 경계 위도
            lft: 왼쪽 경계 경도
            top: 상단 경계 위도
            rgt: 오른쪽 경계 경도
            rlet_tp_cd: 부동산 유형 코드
            trad_tp_cd: 거래 유형 코드
            map_key: 지도 키 (보통 빈 문자열)
            cortar_no: 지역 코드
            show_r0: R0 상태 매물 표시 여부
        
        Returns:
            API 응답 데이터
        """
        url = f"{self.config.base_url}/cluster/ajax/articleList"
        
        params = {
            "itemId": item_id,
            "mapKey": map_key,
            "lgeo": lgeo,
            "rletTpCd": rlet_tp_cd,
            "tradTpCd": trad_tp_cd,
            "z": zoom,
            "lat": lat,
            "lon": lon,
            "btm": btm,
            "lft": lft,
            "top": top,
            "rgt": rgt,
            "cortarNo": cortar_no,
            "showR0": show_r0
        }
        
        # 딜레이 적용
        self._wait_if_needed()
        
        # 재시도 로직
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 지수 백오프
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"클러스터 매물 조회 API 호출 실패: {str(e)}")
        
        raise Exception("클러스터 매물 조회 API 호출 실패: 최대 재시도 횟수 초과")
    
    def get_article_list_by_region(
        self,
        cortar_no: str,
        lat: float,
        lon: float,
        zoom: int,
        btm: float,
        lft: float,
        top: float,
        rgt: float,
        rlet_tp_cd: str = "APT",
        trad_tp_cd: str = "A1",
        page: int = 1,
        tot_cnt: Optional[int] = None,
        show_r0: str = "",
        dprc_min: Optional[int] = None,
        dprc_max: Optional[int] = None,
        spc_min: Optional[int] = None,
        spc_max: Optional[int] = None
    ) -> Dict:
        """
        지역별 매물 목록 조회 (페이지네이션 지원)
        
        이 메서드는 특정 지역(cortarNo)의 모든 매물을 페이지네이션으로 조회합니다.
        사용자가 네이버 부동산에서 "해당 지역만 보기"를 선택하고 "매물목록"을 클릭했을 때
        사용되는 API와 동일한 방식입니다.
        
        Args:
            cortar_no: 지역 코드 (예: 4113110100)
            lat: 중심 위도
            lon: 중심 경도
            zoom: 줌 레벨
            btm: 하단 경계 위도
            lft: 왼쪽 경계 경도
            top: 상단 경계 위도
            rgt: 오른쪽 경계 경도
            rlet_tp_cd: 부동산 유형 코드 (APT, OPST, VL 등)
            trad_tp_cd: 거래 유형 코드 (A1: 매매, B1: 전세, B2: 월세)
            page: 페이지 번호 (1부터 시작)
            tot_cnt: 총 매물 개수 (첫 페이지 응답에서 얻을 수 있음)
            show_r0: R0 상태 매물 표시 여부
            dprc_min: 최소 가격 (만원 단위, 예: 80000 = 8억)
            dprc_max: 최대 가격 (만원 단위, 예: 130000 = 13억)
            spc_min: 최소 면적 (평 단위, 예: 33 = 33평)
            spc_max: 최대 면적 (평 단위, 예: 99 = 99평)
        
        Returns:
            API 응답 데이터
        """
        url = f"{self.config.base_url}/cluster/ajax/articleList"
        
        params = {
            "rletTpCd": rlet_tp_cd,
            "tradTpCd": trad_tp_cd,
            "z": zoom,
            "lat": lat,
            "lon": lon,
            "btm": btm,
            "lft": lft,
            "top": top,
            "rgt": rgt,
            "showR0": show_r0,
            "cortarNo": cortar_no
        }
        
        # 가격 필터 추가
        if dprc_min is not None:
            params["dprcMin"] = str(dprc_min)
        if dprc_max is not None:
            params["dprcMax"] = str(dprc_max)
        
        # 면적 필터 추가
        if spc_min is not None:
            params["spcMin"] = str(spc_min)
        if spc_max is not None:
            params["spcMax"] = str(spc_max)
        
        # totCnt가 제공된 경우 추가
        if tot_cnt is not None:
            params["totCnt"] = str(tot_cnt)
        
        # 페이지 번호 추가 (페이지네이션)
        if page > 1:
            params["page"] = str(page)
        
        # 딜레이 적용
        self._wait_if_needed()
        
        # 디버깅: 실제 요청 URL 출력
        import urllib.parse
        full_url = f"{url}?{urllib.parse.urlencode(params)}"
        print(f"[DEBUG] API 요청 URL: {full_url}")
        
        # 재시도 로직
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"지역별 매물 목록 조회 API 호출 실패: {str(e)}")
        
        raise Exception("지역별 매물 목록 조회 API 호출 실패: 최대 재시도 횟수 초과")
    
    def get_article_basic_info(
        self,
        article_number: str,
        real_estate_type: str = "A01",
        trade_type: str = "A1",
    ) -> Optional[str]:
        """
        개별 매물 basicInfo에서 articleFeatureDescription 반환.
        실패 시 None 반환.
        """
        url = "https://fin.land.naver.com/front-api/v1/article/basicInfo"
        params = {
            "articleNumber": str(article_number),
            "realEstateType": real_estate_type,
            "tradeType": trade_type,
        }
        self._ensure_fin_session()
        self._wait_if_needed()
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                if response.status_code == 429:
                    return None
                response.raise_for_status()
                data = response.json()
                return (
                    data.get("result", {})
                    .get("detailInfo", {})
                    .get("articleDetailInfo", {})
                    .get("articleFeatureDescription", "")
                ) or ""
            except Exception:
                if attempt < self.config.max_retries - 1:
                    time.sleep((attempt + 1) * 1)
                    continue
                return None
        return None

    def search_region_info(
        self,
        region_name: str,
        debug: bool = False
    ) -> Optional[Dict]:
        """
        행정구역명으로 지역 정보 조회
        
        Args:
            region_name: 행정구역명 (예: "성남시 수정구 신흥동")
        
        Returns:
            지역 정보 딕셔너리 (cortarNo, 좌표 등) 또는 None
        """
        # 여러 방법으로 시도
        # 방법 1: geopy를 사용하여 주소를 좌표로 변환
        lat = None
        lon = None
        geopy_success = False
        
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="naver_land_crawler")
            location = geolocator.geocode(region_name, country_codes="kr", timeout=10)
            
            if location:
                lat = location.latitude
                lon = location.longitude
                geopy_success = True
        except Exception as e:
            # geopy 실패 시 계속 진행 (다른 방법 시도)
            pass
        
        # 방법 2: 여러 좌표로 시도 (geopy 실패 시)
        search_coordinates = []
        
        if geopy_success and lat and lon:
            # geopy로 얻은 좌표 사용
            search_coordinates.append((lat, lon, "geopy"))
        else:
            # 한국 주요 도시 좌표로 시도
            # 성남시 좌표
            search_coordinates.append((37.4201, 127.1266, "성남시"))
            # 서울 좌표
            search_coordinates.append((37.5665, 126.9780, "서울"))
            # 경기도 좌표
            search_coordinates.append((37.4138, 127.5183, "경기도"))
        
        # 각 좌표로 시도 - 여러 줌 레벨과 영역 크기 조합
        zoom_area_combinations = [
            (17, 0.001),   # 높은 줌, 작은 영역 (100m)
            (16, 0.002),   # 중간 줌, 작은 영역 (200m)
            (15, 0.005),   # 중간 줌, 중간 영역 (500m)
            (14, 0.01),    # 낮은 줌, 넓은 영역 (1km)
        ]
        
        for search_lat, search_lon, source in search_coordinates:
            if debug:
                print(f"[DEBUG] {source} 좌표로 시도: lat={search_lat}, lon={search_lon}")
            
            # 여러 줌 레벨과 영역 크기 조합 시도
            for zoom, area_size in zoom_area_combinations:
                if debug:
                    print(f"[DEBUG] 줌 레벨 {zoom}, 영역 크기 {area_size}로 시도")
                
                btm = search_lat - area_size
                lft = search_lon - area_size
                top = search_lat + area_size
                rgt = search_lon + area_size
            
                try:
                    if debug:
                        print(f"[DEBUG] API 호출: zoom={zoom}, 영역 크기={area_size}")
                    
                    data = self.get_cluster_list(
                        lat=search_lat,
                        lon=search_lon,
                        zoom=zoom,
                        btm=btm,
                        lft=lft,
                        top=top,
                        rgt=rgt,
                        rlet_tp_cd="APT",
                        trad_tp_cd="A1"
                    )
                    
                    if debug:
                        print(f"[DEBUG] API 응답 코드: {data.get('code')}")
                        print(f"[DEBUG] data 키: {list(data.get('data', {}).keys())}")
                    
                    # 응답 코드 확인
                    if data.get("code") != "success":
                        if debug:
                            print(f"[DEBUG] API 응답이 성공이 아님: {data.get('code')}")
                        continue
                    
                    # cortar 정보 추출
                    cortar_info = data.get("data", {}).get("cortar", {})
                    if not cortar_info:
                        if debug:
                            print(f"[DEBUG] cortar 정보가 없음, 다음 조합 시도")
                        continue  # 다음 줌/영역 조합 시도
                    
                    detail = cortar_info.get("detail", {})
                    
                    if debug:
                        print(f"[DEBUG] cortar 상세 정보: {detail}")
                    
                    if detail.get("cortarNo"):
                        # 지역명 매칭 확인 (부분 일치)
                        region_name_lower = region_name.lower().replace(" ", "").replace("경기도", "").replace("서울시", "").replace("서울", "")
                        found_region_name = detail.get("regionName", "").lower().replace(" ", "").replace("경기도", "").replace("서울시", "").replace("서울", "")
                        found_cortar_nm = detail.get("cortarNm", "").lower().replace(" ", "")
                        
                        if debug:
                            print(f"[DEBUG] 지역명 매칭 시도:")
                            print(f"  입력 (정제): {region_name_lower}")
                            print(f"  찾은 지역명 (정제): {found_region_name}")
                            print(f"  찾은 동명: {found_cortar_nm}")
                        
                        # 지역명이 일치하거나, cortarNm이 일치하는 경우
                        # 입력을 단어로 분리 (공백, 쉼표 등으로 분리)
                        import re
                        input_words = re.split(r'[\s,]+', region_name_lower)
                        input_words = [w for w in input_words if len(w) > 1]
                        
                        match_score = 0
                        for word in input_words:
                            if word in found_region_name or word in found_cortar_nm:
                                match_score += 1
                        
                        # 핵심 단어(구명, 동명 등)가 일치하면 성공으로 간주
                        # "서울시 강서구" -> "강서"가 찾은 지역명에 있으면 매칭
                        if match_score >= 1 or any(word in found_region_name or word in found_cortar_nm for word in input_words if len(word) > 1):
                            if debug:
                                print(f"[DEBUG] ✅ 지역명 매칭 성공! (매칭 점수: {match_score})")
                            
                            return {
                                "cortarNo": detail.get("cortarNo"),
                                "cortarNm": detail.get("cortarNm", ""),
                                "regionName": detail.get("regionName", region_name),
                                "lat": float(detail.get("mapYCrdn", search_lat)),
                                "lon": float(detail.get("mapXCrdn", search_lon)),
                                "cityNm": detail.get("cityNm", ""),
                                "dvsnNm": detail.get("dvsnNm", ""),
                                "secNm": detail.get("secNm", "")
                            }
                        
                        # 매칭이 안 되더라도 첫 번째로 찾은 cortarNo 반환
                        if debug:
                            print(f"[DEBUG] ⚠️ 지역명 매칭 실패 (점수: {match_score}), 하지만 cortarNo는 찾음")
                        
                        return {
                            "cortarNo": detail.get("cortarNo"),
                            "cortarNm": detail.get("cortarNm", ""),
                            "regionName": detail.get("regionName", region_name),
                            "lat": float(detail.get("mapYCrdn", search_lat)),
                            "lon": float(detail.get("mapXCrdn", search_lon)),
                            "cityNm": detail.get("cityNm", ""),
                            "dvsnNm": detail.get("dvsnNm", ""),
                            "secNm": detail.get("secNm", ""),
                            "warning": f"지역명이 정확히 일치하지 않습니다. 찾은 지역: {detail.get('regionName', '')}"
                        }
                    else:
                        if debug:
                            print(f"[DEBUG] cortarNo가 없음, 다음 조합 시도")
                        continue  # 다음 줌/영역 조합 시도
                    
                except Exception as e:
                    # API 호출 실패 시 다음 조합 시도
                    if debug:
                        print(f"[DEBUG] API 호출 오류: {str(e)}, 다음 조합 시도")
                    continue
        
        # 방법 2: articleList API를 사용하여 cortarNo 추출
        # 좌표로 articleList API를 호출하면 첫 번째 매물의 cortarNo를 얻을 수 있음
        if debug:
            print(f"[DEBUG] 방법 2: articleList API로 cortarNo 추출 시도")
        
        # geopy로 얻은 좌표 또는 기본 좌표로 시도
        for search_lat, search_lon, source in search_coordinates:
            try:
                # 넓은 영역으로 articleList API 호출 (사용자 예시와 유사한 크기)
                zoom = 14
                # 사용자 예시: btm=37.4056195, top=37.4889573 (차이: 0.083)
                #            lft=127.0763439, rgt=127.2222561 (차이: 0.146)
                lat_size = 0.04  # 약 4km
                lon_size = 0.07  # 약 6km
                btm = search_lat - lat_size
                lft = search_lon - lon_size
                top = search_lat + lat_size
                rgt = search_lon + lon_size
                
                # 방법 2-1: cortarNo 없이 시도 (빈 문자열)
                try:
                    test_data = self.get_article_list_by_region(
                        cortar_no="",  # 빈 문자열로 시도
                        lat=search_lat,
                        lon=search_lon,
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
                            # 각 매물에서 cortarNo 추출 시도
                            for article in body:
                                extracted_cortar_no = article.get("cortarNo") or article.get("cortarNo")
                                # 다른 필드에서도 시도
                                if not extracted_cortar_no:
                                    extracted_cortar_no = article.get("cortarNo") or article.get("cortarNo")
                                
                                if extracted_cortar_no:
                                    if debug:
                                        print(f"[DEBUG] ✅ articleList API에서 cortarNo 추출 성공: {extracted_cortar_no}")
                                    
                                    return {
                                        "cortarNo": extracted_cortar_no,
                                        "lat": search_lat,
                                        "lon": search_lon,
                                        "regionName": region_name,
                                        "cortarNm": "",
                                        "cityNm": "",
                                        "dvsnNm": "",
                                        "secNm": ""
                                    }
                except Exception as e:
                    if debug:
                        print(f"[DEBUG] cortarNo 없이 호출 실패: {str(e)}")
                
                # 방법 2-2: 지역명 기반 cortarNo 추정 및 검증
                # 성남시 수정구 신흥동 -> 4113110100
                test_cortar_nos = []
                
                # 지역명에서 추정
                if "성남" in region_name or "수정" in region_name or "신흥" in region_name:
                    test_cortar_nos = ["4113110100", "4113100000", "4113000000"]
                elif "서울" in region_name:
                    if "강남" in region_name:
                        test_cortar_nos = ["1168010100", "1168000000"]
                    else:
                        test_cortar_nos = ["1160000000"]
                elif "수원" in region_name:
                    test_cortar_nos = ["4111000000", "4111100000"]
                elif "인천" in region_name:
                    test_cortar_nos = ["2800000000", "2811000000"]
                
                # 추정된 cortarNo로 매물 검증
                for test_cortar_no in test_cortar_nos:
                    try:
                        test_data = self.get_article_list_by_region(
                            cortar_no=test_cortar_no,
                            lat=search_lat,
                            lon=search_lon,
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
                                # 매물이 있으면 이 cortarNo가 유효함
                                if debug:
                                    print(f"[DEBUG] ✅ 추정 cortarNo로 매물 발견: {test_cortar_no} ({len(body)}개)")
                                
                                return {
                                    "cortarNo": test_cortar_no,
                                    "lat": search_lat,
                                    "lon": search_lon,
                                    "regionName": region_name,
                                    "cortarNm": "",
                                    "cityNm": "",
                                    "dvsnNm": "",
                                    "secNm": ""
                                }
                    except Exception:
                        continue
                            
            except Exception as e:
                if debug:
                    print(f"[DEBUG] 방법 2 시도 실패: {str(e)}")
                continue
        
        return None

