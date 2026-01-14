"""
네이버 부동산 API 클라이언트
"""
import requests
import time
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ApiConfig:
    """API 설정"""
    base_url: str = "https://m.land.naver.com"
    min_delay: float = 1.0  # API 호출 간 최소 딜레이 (초)
    timeout: int = 10  # 타임아웃 (초)
    max_retries: int = 3  # 최대 재시도 횟수


class NaverLandApiClient:
    """네이버 부동산 API 클라이언트"""
    
    def __init__(self, config: Optional[ApiConfig] = None):
        self.config = config or ApiConfig()
        self.session = requests.Session()
        self.last_request_time = 0
        
        # 기본 헤더 설정
        self.session.headers.update({
            "Accept": "application/json",
            "Referer": "https://m.land.naver.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 지수 백오프
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"API 호출 실패: {str(e)}")
        
        raise Exception("API 호출 실패: 최대 재시도 횟수 초과")
    
    def get_articles_by_complex(
        self,
        complex_no: str,
        rlet_tp_cd: str = "APT:JGC",
        trad_tp_cd: str = "A1",
        page: int = 1
    ) -> Dict:
        """
        단지별 매물 목록 조회 (new.land.naver.com API)
        
        Args:
            complex_no: 단지 번호
            rlet_tp_cd: 부동산 유형 코드
            trad_tp_cd: 거래 유형 코드
            page: 페이지 번호
        
        Returns:
            API 응답 데이터
        """
        # new.land.naver.com API 사용 시도
        url = "https://new.land.naver.com/api/articles/complex/" + complex_no
        
        params = {
            "realEstateType": rlet_tp_cd,
            "tradeType": trad_tp_cd if trad_tp_cd else "",
            "tag": ":::::::::",
            "rentPriceMin": "0",
            "rentPriceMax": "900000000",
            "priceMin": "0",
            "priceMax": "900000000",
            "areaMin": "0",
            "areaMax": "900000000",
            "priceType": "RETAIL",
            "page": str(page),
            "complexNo": complex_no,
            "type": "list",
            "order": "rank"
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
                # 404는 단지 정보가 없는 경우이므로 무시
                if response.status_code == 404:
                    return {"data": {"articleList": []}}
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    time.sleep(wait_time)
                    continue
                else:
                    # 실패해도 계속 진행
                    return {"data": {"articleList": []}}
        
        return {"data": {"articleList": []}}
    
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
            except requests.exceptions.RequestException as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 지수 백오프
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"클러스터 매물 조회 API 호출 실패: {str(e)}")
        
        raise Exception("클러스터 매물 조회 API 호출 실패: 최대 재시도 횟수 초과")

