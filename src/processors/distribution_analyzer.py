"""
호가 분포 분석
"""
from typing import Dict, List, Optional, Tuple
from collections import Counter
import statistics
import re


class DistributionAnalyzer:
    """호가 분포 분석기"""
    
    @staticmethod
    def analyze_by_pyeong(properties: List[Dict]) -> List[Dict]:
        """
        평형대별 호가 분포 분석
        
        Args:
            properties: 매물 정보 리스트
        
        Returns:
            평형대별 통계 리스트 (상위 3개)
        """
        # 평형별로 그룹화 (평형 정보가 없는 경우 건너뛰기)
        # 실제로는 매물 정보에 평형 정보가 포함되어야 함
        # 여기서는 가격만으로 추정하거나, 별도 필드 필요
        
        # 임시로 가격대별로 분류 (실제로는 평형 정보 필요)
        # TODO: 실제 평형 정보가 수집 데이터에 포함되면 수정 필요
        
        price_buckets = {}
        
        for prop in properties:
            price = prop.get("price", 0)
            if price <= 0:
                continue
            
            # 가격을 억 단위로 변환
            price_in_100m = price / 10000
            
            # 가격대별로 그룹화 (임시)
            # 실제로는 평형 정보를 사용해야 함
            bucket_key = f"{int(price_in_100m)}억대"
            
            if bucket_key not in price_buckets:
                price_buckets[bucket_key] = []
            
            price_buckets[bucket_key].append(price_in_100m)
        
        # 각 버킷별 통계 계산
        results = []
        for bucket, prices in sorted(price_buckets.items(), key=lambda x: len(x[1]), reverse=True)[:3]:
            if prices:
                results.append({
                    "pyeong": bucket,  # 실제로는 평형 정보
                    "min": round(min(prices), 2),
                    "max": round(max(prices), 2),
                    "median": round(statistics.median(prices), 2),
                    "count": len(prices)
                })
        
        return results
    
    @staticmethod
    def analyze_by_dong(properties: List[Dict]) -> Dict[str, List[Dict]]:
        """
        동별 호가 분포 분석
        
        Args:
            properties: 매물 정보 리스트
        
        Returns:
            {"top": 상위 동 리스트, "low": 하위 동 리스트}
        """
        # 동별로 그룹화
        dong_groups = {}
        
        for prop in properties:
            # 동 정보 추출 (complex_name이나 별도 필드에서)
            # 예: "산성역포레스티아 101동" -> "101동"
            complex_name = prop.get("complex_name", "")
            
            # 동 정보 파싱 (실제 데이터 구조에 맞게 수정 필요)
            dong = DistributionAnalyzer._extract_dong(complex_name)
            
            if not dong:
                continue
            
            price = prop.get("price", 0)
            if price <= 0:
                continue
            
            price_in_100m = price / 10000
            
            if dong not in dong_groups:
                dong_groups[dong] = []
            
            dong_groups[dong].append(price_in_100m)
        
        # 동별 중앙값 계산
        dong_stats = []
        for dong, prices in dong_groups.items():
            if prices:
                dong_stats.append({
                    "dong": dong,
                    "median": statistics.median(prices),
                    "count": len(prices)
                })
        
        # 중앙값 기준으로 정렬
        dong_stats.sort(key=lambda x: x["median"], reverse=True)
        
        # 상위 2개, 하위 2개 반환
        top_dongs = dong_stats[:2] if len(dong_stats) >= 2 else dong_stats
        low_dongs = dong_stats[-2:] if len(dong_stats) >= 2 else []
        low_dongs.reverse()  # 하위는 오름차순
        
        return {
            "top": top_dongs,
            "low": low_dongs
        }
    
    @staticmethod
    def _extract_dong(complex_name: str) -> Optional[str]:
        """
        단지명에서 동 정보 추출
        
        Args:
            complex_name: 단지명 (예: "산성역포레스티아 101동")
        
        Returns:
            동 정보 (예: "101동") 또는 None
        """
        if not complex_name:
            return None
        
        # "동"이 포함된 경우 추출
        import re
        match = re.search(r'(\d+동)', complex_name)
        if match:
            return match.group(1)
        
        return None
    
    @staticmethod
    def find_highest_price_property(properties: List[Dict]) -> Optional[Dict]:
        """
        최고가 매물 찾기
        
        Args:
            properties: 매물 정보 리스트
        
        Returns:
            최고가 매물 정보 또는 None
        """
        if not properties:
            return None
        
        max_price = 0
        max_prop = None
        
        for prop in properties:
            price = prop.get("price", 0)
            if price > max_price:
                max_price = price
                max_prop = prop
        
        if max_prop:
            # 억 단위로 변환하여 추가
            max_prop["price_in_100m"] = round(max_price / 10000, 2)
        
        return max_prop
    
    @staticmethod
    def analyze_royal_dong_floor(property_info: Dict) -> Dict[str, bool]:
        """
        로얄동/로얄층 여부 판단
        
        Args:
            property_info: 매물 정보
        
        Returns:
            {"is_royal_dong": bool, "is_royal_floor": bool, "reason": str}
        """
        # 로얄동/로얄층 판단 로직
        # 실제로는 단지별로 다른 기준이 있을 수 있음
        # 여기서는 간단한 예시만 제공
        
        complex_name = property_info.get("complex_name", "")
        dong = DistributionAnalyzer._extract_dong(complex_name)
        
        is_royal_dong = False
        is_royal_floor = False
        reason = ""
        
        # 동 정보가 있고 특정 동이면 로얄동으로 판단 (예시)
        if dong:
            dong_num = int(re.search(r'(\d+)', dong).group(1)) if re.search(r'(\d+)', dong) else 0
            # 예: 101동, 201동 등이 로얄동 (실제 기준은 단지별로 다름)
            if dong_num in [101, 201, 301]:
                is_royal_dong = True
                reason += f"{dong}은 로얄동입니다. "
        
        # 층 정보가 있으면 로얄층 판단 (예시)
        # 실제로는 층 정보가 매물 데이터에 포함되어야 함
        # TODO: 층 정보 필드 추가 필요
        
        return {
            "is_royal_dong": is_royal_dong,
            "is_royal_floor": is_royal_floor,
            "reason": reason.strip()
        }

