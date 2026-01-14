"""
데이터 수집 로직
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from api_client import NaverLandApiClient, ApiConfig
import math


@dataclass
class Property:
    """매물 정보"""
    item_id: str
    region_name: str
    complex_name: str
    property_type: str
    trade_type: str
    trade_type_code: str
    price: int  # 만원 단위
    price_display: str
    latitude: float
    longitude: float
    min_mvi_fee: int
    max_mvi_fee: int
    tour_exist: bool
    collected_at: datetime
    lgeo: str = ""  # 지역 지오코드 (단지 매칭용)


@dataclass
class Complex:
    """단지 정보"""
    item_id: str
    complex_name: str
    latitude: float
    longitude: float
    deal_median_unit_price: str
    lease_median_rate: str
    build_year: str
    tour_exist: bool
    article_count: int
    lgeo: str = ""  # 지역 지오코드 (매칭용)


class DataCollector:
    """데이터 수집기"""
    
    def __init__(self, api_config: Optional[ApiConfig] = None):
        self.api_client = NaverLandApiClient(api_config)
        self.properties: List[Property] = []
        self.complexes: List[Complex] = []
    
    def calculate_bounds(
        self,
        center_lat: float,
        center_lon: float,
        zoom: int,
        grid_size: int = 1,
        area_size: Optional[float] = None,
        region_radius: Optional[float] = None
    ) -> List[Tuple[float, float, float, float, int]]:
        """
        중심 좌표를 기준으로 지역구 전체를 커버하는 영역을 분할
        
        Args:
            center_lat: 중심 위도
            center_lon: 중심 경도
            zoom: 줌 레벨
            grid_size: 그리드 크기 (분할 개수)
            area_size: 각 그리드의 영역 크기 (None이면 자동 계산)
            region_radius: 지역구 반경 (도 단위, None이면 자동 계산)
        
        Returns:
            (lat, lon, btm, lft, top, rgt, effective_zoom) 튜플 리스트
        """
        # 줌 레벨을 높여서 더 많은 개별 매물을 수집
        effective_zoom = max(zoom, 18)  # 최소 18로 설정
        
        if area_size is None:
            # 줌 레벨에 따른 각 그리드의 영역 크기 계산
            # 줌 18: 약 0.001도 (약 100m)
            # 줌 19: 약 0.0005도 (약 50m)
            base_size = 0.001 * (2 ** (18 - effective_zoom))
        else:
            base_size = area_size
        
        # 지역구 전체를 커버하기 위한 전체 영역 크기
        if region_radius is not None:
            # region_radius가 지정된 경우, 전체 영역 크기를 region_radius * 2로 설정
            # 각 그리드의 크기를 전체 영역을 grid_size로 나눈 값으로 계산
            total_size = region_radius * 2
            base_size = total_size / grid_size
        else:
            # region_radius가 None인 경우, 그리드 크기에 따라 전체 영역 크기 조정
            # grid_size x base_size가 전체 영역 크기
            total_size = grid_size * base_size
        
        bounds_list = []
        for i in range(grid_size):
            for j in range(grid_size):
                # 그리드 오프셋 계산 (중심에서 시작)
                # 전체 영역을 grid_size로 나눈 각 그리드의 중심 위치 계산
                lat_offset = (i - (grid_size - 1) / 2) * base_size
                lon_offset = (j - (grid_size - 1) / 2) * base_size
                
                lat = center_lat + lat_offset
                lon = center_lon + lon_offset
                
                # 각 그리드의 경계 계산
                half_size = base_size / 2
                btm = lat - half_size
                top = lat + half_size
                lft = lon - half_size
                rgt = lon + half_size
                
                bounds_list.append((lat, lon, btm, lft, top, rgt, effective_zoom))
        
        return bounds_list
    
    def extract_properties(self, data: Dict, region_name: str) -> List[Property]:
        """API 응답에서 매물 정보 추출"""
        properties = []
        articles = data.get("data", {}).get("ARTICLE", [])
        
        for article in articles:
            if article.get("count") == 1 and "itemId" in article:
                prop = Property(
                    item_id=article.get("itemId", ""),
                    region_name=region_name,
                    complex_name="",  # 나중에 매칭
                    property_type=article.get("rletNm", ""),
                    trade_type=article.get("tradNm", ""),
                    trade_type_code=article.get("tradTpCd", ""),
                    price=int(article.get("prc", 0)) if article.get("prc") else 0,
                    price_display=article.get("priceTtl", ""),
                    latitude=article.get("lat", 0.0),
                    longitude=article.get("lon", 0.0),
                    min_mvi_fee=article.get("minMviFee", 0),
                    max_mvi_fee=article.get("maxMviFee", 0),
                    tour_exist=article.get("tourExist", False),
                    collected_at=datetime.now(),
                    lgeo=article.get("lgeo", "")
                )
                properties.append(prop)
        
        return properties
    
    def extract_properties_from_complex_api(self, data: Dict, region_name: str, complex_name: str = "") -> List[Property]:
        """단지별 매물 API 응답에서 매물 정보 추출"""
        properties = []
        
        # 다양한 응답 구조 지원
        article_list = (
            data.get("data", {}).get("articleList", []) or
            data.get("articleList", []) or
            data.get("data", {}).get("list", []) or
            []
        )
        
        for article in article_list:
            try:
                # new.land.naver.com API 응답 구조 파싱
                article_no = article.get("articleNo") or article.get("articleNo") or article.get("id", "")
                deal_price = article.get("dealPrice") or article.get("price") or 0
                price = int(deal_price / 10000) if deal_price else 0
                
                prop = Property(
                    item_id=str(article_no),
                    region_name=region_name,
                    complex_name=complex_name,
                    property_type=article.get("realEstateTypeName") or article.get("propertyType", ""),
                    trade_type=article.get("tradeTypeName") or article.get("tradeType", ""),
                    trade_type_code=article.get("tradeType") or article.get("tradeTypeCode", ""),
                    price=price,
                    price_display=article.get("priceDisplay") or article.get("priceStr", ""),
                    latitude=float(article.get("latitude") or article.get("lat", 0.0)),
                    longitude=float(article.get("longitude") or article.get("lon", 0.0)),
                    min_mvi_fee=article.get("maintenanceCost") or article.get("mviFee", 0),
                    max_mvi_fee=article.get("maintenanceCost") or article.get("mviFee", 0),
                    tour_exist=article.get("vrExist") or article.get("tourExist", False),
                    collected_at=datetime.now()
                )
                properties.append(prop)
            except Exception:
                continue
        
        return properties
    
    def extract_complexes(self, data: Dict) -> List[Complex]:
        """API 응답에서 단지 정보 추출"""
        complexes = []
        complex_list = data.get("data", {}).get("COMPLEX", [])
        
        for comp in complex_list:
            # itemId가 없으면 건너뛰기
            item_id = comp.get("itemId", "")
            if not item_id:
                continue
            
            complex_obj = Complex(
                item_id=item_id,
                complex_name=comp.get("ttl", ""),
                latitude=float(comp.get("lat", 0.0)) if comp.get("lat") else 0.0,
                longitude=float(comp.get("lon", 0.0)) if comp.get("lon") else 0.0,
                deal_median_unit_price=comp.get("dealMedianUnitPrice", ""),
                lease_median_rate=comp.get("leaseMedianRate", ""),
                build_year=comp.get("si1", ""),  # 건축년도 추정
                tour_exist=comp.get("isComplexTourExist", False),
                article_count=comp.get("articleCount", 0),
                lgeo=comp.get("lgeo", "")
            )
            complexes.append(complex_obj)
        
        return complexes
    
    def extract_properties_from_cluster_articles(self, data: Dict, region_name: str) -> List[Property]:
        """
        cluster/ajax/articleList API 응답에서 매물 정보 추출
        
        Args:
            data: API 응답 데이터
            region_name: 지역명
        
        Returns:
            매물 정보 리스트
        """
        properties = []
        body = data.get("body", [])
        
        for article in body:
            try:
                # atclNo를 item_id로 사용
                atcl_no = article.get("atclNo", "")
                if not atcl_no:
                    continue
                
                # 가격 처리 (prc는 만원 단위)
                prc = article.get("prc", 0)
                price = int(prc) if prc else 0
                
                prop = Property(
                    item_id=str(atcl_no),
                    region_name=region_name,
                    complex_name=article.get("atclNm", ""),  # 단지명이 이미 포함되어 있음
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
                    lgeo=""  # cluster/ajax/articleList 응답에는 lgeo가 없을 수 있음
                )
                properties.append(prop)
            except Exception as e:
                # 파싱 오류는 무시하고 계속 진행
                continue
        
        return properties
    
    def match_complex_to_property(self, prop: Property) -> str:
        """매물에 가장 가까운 단지 매칭"""
        if not self.complexes:
            return ""
        
        # 1단계: lgeo 기반 매칭 (가장 정확)
        if prop.lgeo:
            for comp in self.complexes:
                if comp.lgeo and prop.lgeo.startswith(comp.lgeo[:10]):  # lgeo 앞부분이 일치하면 같은 지역
                    # 좌표 거리도 확인
                    distance = self._haversine_distance(
                        prop.latitude, prop.longitude,
                        comp.latitude, comp.longitude
                    )
                    if distance < 0.005:  # 500m 이내
                        return comp.complex_name
        
        # 2단계: 좌표 기반 매칭
        min_distance = float('inf')
        matched_complex = ""
        
        for comp in self.complexes:
            # 하버사인 공식으로 거리 계산
            distance = self._haversine_distance(
                prop.latitude, prop.longitude,
                comp.latitude, comp.longitude
            )
            
            # 거리 임계값을 500m로 증가 (단지가 넓을 수 있음)
            if distance < min_distance and distance < 0.005:  # 약 500m 이내
                min_distance = distance
                matched_complex = comp.complex_name
        
        return matched_complex
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """하버사인 공식으로 두 좌표 간 거리 계산 (km)"""
        R = 6371  # 지구 반지름 (km)
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def collect_properties(
        self,
        region_name: str,
        center_lat: float,
        center_lon: float,
        zoom: int,
        rlet_tp_cd: str = "APT:JGC",
        trad_tp_cd: str = "A1",
        grid_size: int = 3,
        progress_callback=None
    ) -> Tuple[List[Property], List[Complex]]:
        """
        지역구 전체 매물 수집 (다단계 프로세스)
        
        Args:
            region_name: 지역명
            center_lat: 중심 위도
            center_lon: 중심 경도
            zoom: 줌 레벨
            rlet_tp_cd: 부동산 유형 코드
            trad_tp_cd: 거래 유형 코드
            grid_size: 그리드 크기
            progress_callback: 진행 상황 콜백 함수 (current, total, message)
                            total은 100으로 고정, current는 0-100 사이 값
        
        Returns:
            (매물 리스트, 단지 리스트)
        """
        self.properties = []
        self.complexes = []
        
        # ========== 1단계: 기본 영역 수집 (0-60%) ==========
        if progress_callback:
            progress_callback(0, 100, "1단계: 기본 영역 수집 준비 중...")
        
        # 영역 분할 - 줌 레벨을 높이고 더 작은 영역으로 분할
        effective_zoom = max(zoom, 18)
        # 그리드 크기를 늘려서 지역구 전체를 커버
        # 동 단위 지역구를 커버하려면 충분한 그리드 필요
        if effective_zoom >= 19:
            adjusted_grid_size = max(grid_size, 10)  # 줌 19 이상이면 최소 10x10 그리드 (100개 영역)
        elif effective_zoom >= 18:
            adjusted_grid_size = max(grid_size, 8)  # 줌 18이면 최소 8x8 그리드 (64개 영역)
        else:
            adjusted_grid_size = max(grid_size, 5)  # 줌 17 이하면 최소 5x5 그리드 (25개 영역)
        
        # 지역구 전체를 커버하기 위해 약 1.5km x 1.5km 영역 설정
        # 동 단위 지역구는 보통 1-2km 범위이므로 충분한 영역 설정
        bounds_list = self.calculate_bounds(
            center_lat, center_lon, effective_zoom, adjusted_grid_size,
            region_radius=0.008  # 약 800m 반경 (동 단위 지역구 전체 커버)
        )
        total_bounds = len(bounds_list)
        
        # 클러스터 정보 저장 (2단계에서 재수집용)
        clusters_to_expand = []
        existing_item_ids = set()
        
        for idx, (lat, lon, btm, lft, top, rgt, zoom_level) in enumerate(bounds_list):
            # 진행률 계산: 1단계는 0-60%
            progress_pct = int((idx + 1) / total_bounds * 60)
            if progress_callback:
                progress_callback(
                    progress_pct, 100,
                    f"1단계: 영역 {idx + 1}/{total_bounds} 수집 중... (줌 {zoom_level})"
                )
            
            try:
                # API 호출
                data = self.api_client.get_cluster_list(
                    lat=lat,
                    lon=lon,
                    zoom=zoom_level,
                    btm=btm,
                    lft=lft,
                    top=top,
                    rgt=rgt,
                    rlet_tp_cd=rlet_tp_cd,
                    trad_tp_cd=trad_tp_cd
                )
                
                # 매물 추출
                properties = self.extract_properties(data, region_name)
                # 중복 제거하면서 추가
                for prop in properties:
                    if prop.item_id and prop.item_id not in existing_item_ids:
                        self.properties.append(prop)
                        existing_item_ids.add(prop.item_id)
                
                # 단지 추출
                complexes = self.extract_complexes(data)
                # 중복 제거
                existing_complex_ids = {c.item_id for c in self.complexes}
                for comp in complexes:
                    if comp.item_id and comp.item_id not in existing_complex_ids:
                        self.complexes.append(comp)
                        existing_complex_ids.add(comp.item_id)
                
                # 클러스터 정보 수집 (count > 1인 경우)
                articles = data.get("data", {}).get("ARTICLE", [])
                for article in articles:
                    count = article.get("count", 0)
                    if count > 1:
                        # 중복 클러스터 제거 (lgeo 기준)
                        lgeo = article.get("lgeo", "")
                        is_duplicate = any(
                            c.get("lgeo") == lgeo 
                            for c in clusters_to_expand
                        )
                        if not is_duplicate:
                            clusters_to_expand.append({
                                "lat": article.get("lat"),
                                "lon": article.get("lon"),
                                "count": count,
                                "lgeo": lgeo
                            })
            
            except Exception as e:
                if progress_callback:
                    progress_callback(progress_pct, 100, f"오류: {str(e)}")
                continue
        
        # ========== 2단계: 클러스터 확장 수집 (60-90%) ==========
        if clusters_to_expand:
            max_clusters = min(len(clusters_to_expand), 50)  # 최대 50개 클러스터 처리
            clusters_to_expand = clusters_to_expand[:max_clusters]
            
            if progress_callback:
                progress_callback(60, 100, f"2단계: 클러스터 {max_clusters}개 상세 수집 시작...")
            
            for idx, cluster in enumerate(clusters_to_expand):
                try:
                    # 진행률 계산: 2단계는 60-90%
                    progress_pct = 60 + int((idx + 1) / max_clusters * 30)
                    if progress_callback:
                        progress_callback(
                            progress_pct, 100,
                            f"2단계: 클러스터 {idx + 1}/{max_clusters} 수집 중... (매물 {len(self.properties)}개, 단지 {len(self.complexes)}개)"
                        )
                    
                    cluster_lat = cluster.get("lat", 0.0)
                    cluster_lon = cluster.get("lon", 0.0)
                    cluster_lgeo = cluster.get("lgeo", "")
                    cluster_count = cluster.get("count", 0)
                    
                    if not cluster_lgeo or not cluster_lat or not cluster_lon:
                        continue
                    
                    # 2-1. 클러스터 내부 숨겨진 단지 정보 수집
                    # 클러스터 중심으로 작은 영역을 설정하고 높은 줌 레벨로 재수집
                    cluster_zoom = 19 if cluster_count > 5 else 20  # 클러스터 크기에 따라 줌 레벨 조정
                    small_size = 0.0003 if cluster_count > 10 else 0.0002  # 약 20-30m 영역
                    
                    try:
                        # 클러스터 내부 단지 정보 수집을 위한 cluster/clusterList 재호출
                        cluster_data = self.api_client.get_cluster_list(
                            lat=cluster_lat,
                            lon=cluster_lon,
                            zoom=cluster_zoom,
                            btm=cluster_lat - small_size,
                            lft=cluster_lon - small_size,
                            top=cluster_lat + small_size,
                            rgt=cluster_lon + small_size,
                            rlet_tp_cd=rlet_tp_cd,
                            trad_tp_cd=trad_tp_cd,
                            addon="COMPLEX"  # 단지 정보 포함
                        )
                        
                        # 클러스터 내부에서 발견된 단지 정보 추출
                        hidden_complexes = self.extract_complexes(cluster_data)
                        existing_complex_ids = {c.item_id for c in self.complexes}
                        for comp in hidden_complexes:
                            if comp.item_id and comp.item_id not in existing_complex_ids:
                                self.complexes.append(comp)
                                existing_complex_ids.add(comp.item_id)
                    except Exception as e:
                        # 단지 정보 수집 실패는 무시하고 계속 진행
                        pass
                    
                    # 2-2. 클러스터 내부 개별 매물 수집
                    # itemId와 lgeo는 동일한 값 사용
                    cluster_item_id = cluster_lgeo
                    
                    # cluster/ajax/articleList API 호출
                    article_data = self.api_client.get_cluster_articles(
                        item_id=cluster_item_id,
                        lgeo=cluster_lgeo,
                        lat=cluster_lat,
                        lon=cluster_lon,
                        zoom=cluster_zoom,
                        btm=cluster_lat - small_size,
                        lft=cluster_lon - small_size,
                        top=cluster_lat + small_size,
                        rgt=cluster_lon + small_size,
                        rlet_tp_cd=rlet_tp_cd.replace(":JGC", ""),  # APT:JGC -> APT
                        trad_tp_cd=trad_tp_cd
                    )
                    
                    # 매물 추출 (cluster/ajax/articleList 응답 파싱)
                    properties = self.extract_properties_from_cluster_articles(article_data, region_name)
                    # 중복 제거 (itemId 기준)
                    for prop in properties:
                        if prop.item_id and prop.item_id not in existing_item_ids:
                            self.properties.append(prop)
                            existing_item_ids.add(prop.item_id)
                
                except Exception as e:
                    continue
        
        # ========== 3단계: 데이터 정제 및 매칭 (90-100%) ==========
        if progress_callback:
            progress_callback(90, 100, "3단계: 단지 정보 매칭 중...")
        
        # 매물에 단지 정보 매칭
        for prop in self.properties:
            prop.complex_name = self.match_complex_to_property(prop)
        
        if progress_callback:
            progress_callback(95, 100, "3단계: 단지 매칭 개선 중...")
        
        # 단지 매칭 개선
        self._improve_complex_matching(region_name)
        
        if progress_callback:
            progress_callback(100, 100, f"수집 완료: 매물 {len(self.properties)}개, 단지 {len(self.complexes)}개")
        
        return self.properties, self.complexes
    
    def _improve_complex_matching(self, region_name: str):
        """단지 매칭 개선"""
        # 단지별로 좌표 범위 내의 매물 그룹화
        complex_property_map = {}
        
        for comp in self.complexes:
            complex_property_map[comp.item_id] = {
                "complex": comp,
                "properties": []
            }
        
        # 각 매물을 가장 가까운 단지에 할당
        for prop in self.properties:
            if prop.complex_name:  # 이미 매칭된 경우
                # 이미 매칭된 경우에도 거리 확인하여 더 가까운 단지가 있으면 업데이트
                current_distance = float('inf')
                for comp in self.complexes:
                    if comp.complex_name == prop.complex_name:
                        current_distance = self._haversine_distance(
                            prop.latitude, prop.longitude,
                            comp.latitude, comp.longitude
                        )
                        break
            else:
                current_distance = float('inf')
            
            min_distance = current_distance
            matched_complex_id = None
            
            for comp in self.complexes:
                distance = self._haversine_distance(
                    prop.latitude, prop.longitude,
                    comp.latitude, comp.longitude
                )
                
                # 거리 임계값을 500m로 증가 (단지가 넓을 수 있음)
                if distance < min_distance and distance < 0.005:
                    min_distance = distance
                    matched_complex_id = comp.item_id
            
            if matched_complex_id:
                prop.complex_name = complex_property_map[matched_complex_id]["complex"].complex_name
                complex_property_map[matched_complex_id]["properties"].append(prop)

