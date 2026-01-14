"""
가격 분석 및 변동률 계산
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass


@dataclass
class PriceChange:
    """가격 변동 정보"""
    delta: float  # 변화량 (억)
    pct: float    # 변동률 (%)
    prev_price: float  # 이전 가격
    current_price: float  # 현재 가격
    comparison_date: Optional[datetime]  # 비교 기준일


class PriceAnalyzer:
    """가격 분석기"""
    
    @staticmethod
    def calculate_representative_price(
        properties: List[Dict],
        pyeong: Optional[float] = None
    ) -> Optional[float]:
        """
        대표 가격 계산 (중앙값)
        
        Args:
            properties: 매물 정보 리스트
            pyeong: 특정 평형 지정 (None이면 전체)
        
        Returns:
            중앙값 가격 (억 단위) 또는 None
        """
        if not properties:
            return None
        
        # 가격 필터링
        prices = []
        for prop in properties:
            price = prop.get("price", 0)
            if price > 0:
                # 만원 단위를 억 단위로 변환
                price_in_100m = price / 10000
                prices.append(price_in_100m)
        
        if not prices:
            return None
        
        # 중앙값 계산
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        
        if n % 2 == 0:
            median = (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
        else:
            median = prices_sorted[n // 2]
        
        return round(median, 2)
    
    @staticmethod
    def calculate_price_range(properties: List[Dict]) -> Tuple[Optional[float], Optional[float]]:
        """
        가격 범위 계산
        
        Args:
            properties: 매물 정보 리스트
        
        Returns:
            (최저가, 최고가) (억 단위)
        """
        if not properties:
            return None, None
        
        prices = []
        for prop in properties:
            price = prop.get("price", 0)
            if price > 0:
                price_in_100m = price / 10000
                prices.append(price_in_100m)
        
        if not prices:
            return None, None
        
        return round(min(prices), 2), round(max(prices), 2)
    
    @staticmethod
    def calculate_price_change(
        current_price: float,
        historical_data: pd.DataFrame,
        days: int
    ) -> Optional[PriceChange]:
        """
        가격 변동 계산
        
        Args:
            current_price: 현재 가격 (억)
            historical_data: 과거 데이터 DataFrame
            days: 비교할 일수
        
        Returns:
            PriceChange 객체 또는 None
        """
        if historical_data is None or historical_data.empty:
            return None
        
        # 비교 기준일 계산
        target_date = datetime.now() - timedelta(days=days)
        
        # 가장 가까운 과거 데이터 찾기
        historical_data['date_diff'] = (target_date - pd.to_datetime(historical_data['date'])).dt.days
        valid_data = historical_data[historical_data['date_diff'] >= 0]
        
        if valid_data.empty:
            return None
        
        # 가장 가까운 날짜 선택
        closest = valid_data.loc[valid_data['date_diff'].idxmin()]
        prev_price = closest.get('median_price', None)
        
        if prev_price is None or prev_price == 0:
            return None
        
        # 변화량 및 변동률 계산
        delta = current_price - prev_price
        pct = (delta / prev_price) * 100 if prev_price > 0 else 0
        
        return PriceChange(
            delta=round(delta, 2),
            pct=round(pct, 1),
            prev_price=round(prev_price, 2),
            current_price=round(current_price, 2),
            comparison_date=closest['date']
        )
    
    @staticmethod
    def analyze_price_changes(
        current_properties: List[Dict],
        historical_data: Optional[pd.DataFrame],
        representative_pyeong: Optional[float] = None
    ) -> Dict[str, Optional[PriceChange]]:
        """
        가격 변동 분석 (전주/전월/전년)
        
        Args:
            current_properties: 현재 매물 정보
            historical_data: 과거 데이터
            representative_pyeong: 대표 평형
        
        Returns:
            {"week": PriceChange, "month": PriceChange, "year": PriceChange}
        """
        # 현재 대표 가격 계산
        current_price = PriceAnalyzer.calculate_representative_price(
            current_properties,
            representative_pyeong
        )
        
        if current_price is None:
            return {
                "week": None,
                "month": None,
                "year": None
            }
        
        # 각 기간별 변동 계산
        week_change = PriceAnalyzer.calculate_price_change(
            current_price, historical_data, 7
        )
        month_change = PriceAnalyzer.calculate_price_change(
            current_price, historical_data, 30
        )
        year_change = PriceAnalyzer.calculate_price_change(
            current_price, historical_data, 365
        )
        
        return {
            "week": week_change,
            "month": month_change,
            "year": year_change
        }
    
    @staticmethod
    def detect_price_drop(
        price_changes: Dict[str, Optional[PriceChange]]
    ) -> Tuple[bool, Optional[str], Optional[PriceChange]]:
        """
        가격 하락 감지
        
        Args:
            price_changes: 가격 변동 정보
        
        Returns:
            (하락 감지 여부, 트리거 이유, PriceChange 객체)
        """
        for period, change in price_changes.items():
            if change is not None and change.delta < 0:
                period_name = {
                    "week": "전주",
                    "month": "전월",
                    "year": "전년"
                }.get(period, period)
                
                return True, period_name, change
        
        return False, None, None

