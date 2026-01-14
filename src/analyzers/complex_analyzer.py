"""
단지별 매물 분석 모듈
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ComplexAnalyzer:
    """단지별 매물 분석기"""
    
    def __init__(self, complex_name: str):
        """
        Args:
            complex_name: 단지명
        """
        self.complex_name = complex_name
        self.data_dir = Path("data/raw") / complex_name
    
    def load_recent_offers(self, days: int = None) -> Optional[pd.DataFrame]:
        """
        매물 데이터 로드 (전체 매물, days 파라미터는 무시)
        
        Args:
            days: 사용 안 함 (전체 매물 로드)
        
        Returns:
            DataFrame 또는 None
        """
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return None
        
        # offers 파일 찾기
        offer_files = list(self.data_dir.glob("offers_*.csv"))
        if not offer_files:
            logger.warning(f"No offer files found in {self.data_dir}")
            return None
        
        # 최신 파일 로드 (전체 매물, 날짜 필터링 없음)
        offer_files.sort(key=lambda x: x.name, reverse=True)
        latest_file = offer_files[0]
        
        try:
            df = pd.read_csv(latest_file, encoding='utf-8-sig')
            return df
        except Exception as e:
            logger.error(f"Error loading offers: {e}")
            return None
    
    def analyze_complex(self, days: int = None) -> Dict[str, Any]:
        """
        단지 매물 분석 (전체 매물 분석)
        
        Args:
            days: 사용 안 함 (전체 매물 분석)
        
        Returns:
            분석 결과 딕셔너리
        """
        df = self.load_recent_offers(days)
        
        if df is None or df.empty:
            return {
                "complex_name": self.complex_name,
                "total_count": 0,
                "error": "데이터 없음"
            }
        
        return self.analyze_complex_from_dataframe(df, days=days)
    
    def analyze_complex_from_dataframe(self, df: pd.DataFrame, days: int = None) -> Dict[str, Any]:
        """
        DataFrame을 직접 받아서 단지 매물 분석 (전체 매물 분석, 평형별 분리)
        
        Args:
            df: 매물 데이터 DataFrame
            days: 사용 안 함 (전체 매물 분석)
        
        Returns:
            분석 결과 딕셔너리 (평형별 분석 포함)
        """
        if df is None or df.empty:
            return {
                "complex_name": self.complex_name,
                "total_count": 0,
                "error": "데이터 없음"
            }
        
        # 가격 정보 (만원 단위로 변환)
        prices = df['가격'].astype(float) / 10000  # 억 단위
        
        # 평형별 분석 (평형대별 가격 분포 포함)
        area_analysis = self._analyze_by_area(df)
        
        # 평형대별 가격 분포 계산
        price_distribution_by_area = self._calculate_price_distribution_by_area(df, area_analysis)
        
        # 동별 가격 차이
        dong_price_diff = self._analyze_dong_price_difference(df)
        
        return {
            "complex_name": self.complex_name,
            "total_count": len(df),
            "price_distribution_by_area": price_distribution_by_area,  # 평형대별 가격 분포
            "area_analysis": area_analysis,  # 평형별 분석
            "dong_price_diff": dong_price_diff
        }
    
    def _analyze_by_area(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        평형별 분석 (제곱미터를 평으로 변환: 1평 = 3.3058m²)
        
        Args:
            df: 매물 데이터 DataFrame
        
        Returns:
            평형별 분석 결과 딕셔너리
        """
        # 제곱미터를 평으로 변환하는 것이 더 정확함 (1평 = 3.3058m²)
        PYEONG_TO_M2 = 3.3058
        
        if '전용면적제곱미터' in df.columns and '가격' in df.columns:
            # 제곱미터를 평으로 변환
            df_clean = df[['전용면적제곱미터', '가격', '동명', '층수정보', '방향']].copy()
            df_clean['전용면적평'] = pd.to_numeric(df_clean['전용면적제곱미터'], errors='coerce') / PYEONG_TO_M2
        elif '전용면적평' in df.columns and '가격' in df.columns:
            # 이미 평 단위인 경우
            df_clean = df[['전용면적평', '가격', '동명', '층수정보', '방향']].copy()
            df_clean['전용면적평'] = pd.to_numeric(df_clean['전용면적평'], errors='coerce')
        else:
            return {"error": "면적 또는 가격 정보 없음"}
        
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        df_clean = df_clean.dropna(subset=['전용면적평', '가격_억'])
        
        if df_clean.empty:
            return {"error": "유효한 면적/가격 데이터 없음"}
        
        # 평형대별로 그룹화 (5평 단위로 반올림)
        df_clean['평형대'] = (df_clean['전용면적평'] / 5).round() * 5
        df_clean['평형대'] = df_clean['평형대'].astype(int)
        
        area_groups = {}
        for area_type, group_df in df_clean.groupby('평형대'):
            group_prices = group_df['가격_억']
            
            # 가장 많은 향
            directions = group_df['방향'].dropna().tolist()
            most_common_direction = pd.Series(directions).mode()[0] if directions else "N/A"
            
            area_groups[int(area_type)] = {
                "count": len(group_df),
                "min_price": float(group_prices.min()),
                "max_price": float(group_prices.max()),
                "median_price": float(group_prices.median()),
                "mean_price": float(group_prices.mean()),
                "most_common_direction": most_common_direction
            }
        
        # 평형대별 정렬 (면적 순)
        sorted_areas = sorted(area_groups.items(), key=lambda x: x[0])
        
        return {
            "area_types": {area: data for area, data in sorted_areas},
            "total_area_types": len(area_groups)
        }
    
    def _calculate_price_distribution_by_area(self, df: pd.DataFrame, area_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        평형대별 가격 분포 계산
        
        Args:
            df: 매물 데이터 DataFrame
            area_analysis: 평형별 분석 결과
        
        Returns:
            평형대별 가격 분포 딕셔너리
        """
        if "error" in area_analysis or not area_analysis.get("area_types"):
            return {"error": "평형별 분석 데이터 없음"}
        
        # 제곱미터를 평으로 변환하는 것이 더 정확함 (1평 = 3.3058m²)
        PYEONG_TO_M2 = 3.3058
        
        # 면적 데이터 준비
        if '전용면적제곱미터' in df.columns:
            df_clean = df[['전용면적제곱미터', '가격']].copy()
            df_clean['전용면적평'] = pd.to_numeric(df_clean['전용면적제곱미터'], errors='coerce') / PYEONG_TO_M2
        elif '전용면적평' in df.columns:
            df_clean = df[['전용면적평', '가격']].copy()
            df_clean['전용면적평'] = pd.to_numeric(df_clean['전용면적평'], errors='coerce')
        else:
            return {"error": "면적 정보 없음"}
        
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        df_clean = df_clean.dropna(subset=['전용면적평', '가격_억'])
        
        if df_clean.empty:
            return {"error": "유효한 데이터 없음"}
        
        # 평형대별로 그룹화 (5평 단위로 반올림)
        df_clean['평형대'] = (df_clean['전용면적평'] / 5).round() * 5
        df_clean['평형대'] = df_clean['평형대'].astype(int)
        
        # 평형대별 가격 분포 계산
        distribution_by_area = {}
        for area_type, group_df in df_clean.groupby('평형대'):
            group_prices = group_df['가격_억']
            
            distribution_by_area[int(area_type)] = {
                "count": len(group_df),
                "min": float(group_prices.min()),
                "max": float(group_prices.max()),
                "median": float(group_prices.median()),
                "mean": float(group_prices.mean()),
                "q25": float(group_prices.quantile(0.25)),
                "q75": float(group_prices.quantile(0.75))
            }
        
        # 전체 통합 통계 (모든 평형대 통합)
        all_prices = df_clean['가격_억']
        overall = {
            "min": float(all_prices.min()),
            "max": float(all_prices.max()),
            "median": float(all_prices.median()),
            "mean": float(all_prices.mean())
        }
        
        return {
            "by_area": distribution_by_area,
            "overall": overall
        }
    
    def _analyze_floors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """층수 분석"""
        if '층수정보' not in df.columns:
            return {"error": "층수 정보 없음"}
        
        floors = []
        for floor_str in df['층수정보'].dropna():
            try:
                # "22/29" 형식 파싱
                if '/' in str(floor_str):
                    current, total = str(floor_str).split('/')
                    floors.append({
                        "current": int(current),
                        "total": int(total),
                        "ratio": int(current) / int(total) if int(total) > 0 else 0
                    })
            except:
                continue
        
        if not floors:
            return {"error": "층수 파싱 실패"}
        
        floor_currents = [f["current"] for f in floors]
        floor_totals = [f["total"] for f in floors]
        floor_ratios = [f["ratio"] for f in floors]
        
        # 로얄층 판단 (상위 20%)
        royal_threshold = np.percentile(floor_ratios, 80)
        royal_floors = [f for f in floors if f["ratio"] >= royal_threshold]
        
        return {
            "avg_floor": np.mean(floor_currents),
            "min_floor": np.min(floor_currents),
            "max_floor": np.max(floor_currents),
            "avg_total_floors": np.mean(floor_totals),
            "royal_floor_count": len(royal_floors),
            "royal_floor_ratio": len(royal_floors) / len(floors) if floors else 0,
            "floor_distribution": {
                "low": len([f for f in floor_currents if f <= 10]),
                "mid": len([f for f in floor_currents if 10 < f <= 20]),
                "high": len([f for f in floor_currents if f > 20])
            }
        }
    
    def _analyze_directions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """향 분석"""
        if '방향' not in df.columns:
            return {"error": "향 정보 없음"}
        
        directions = df['방향'].dropna().tolist()
        if not directions:
            return {"error": "향 데이터 없음"}
        
        direction_counts = pd.Series(directions).value_counts()
        
        return {
            "most_common": direction_counts.index[0] if len(direction_counts) > 0 else "N/A",
            "distribution": direction_counts.to_dict(),
            "total_varieties": len(direction_counts)
        }
    
    def _analyze_price_distribution(self, prices: pd.Series) -> Dict[str, Any]:
        """가격 분포 분석"""
        return {
            "min": float(prices.min()),
            "max": float(prices.max()),
            "median": float(prices.median()),
            "mean": float(prices.mean()),
            "std": float(prices.std()),
            "q25": float(prices.quantile(0.25)),
            "q75": float(prices.quantile(0.75)),
            "price_ranges": {
                "under_10": len(prices[prices < 10]),
                "10_15": len(prices[(prices >= 10) & (prices < 15)]),
                "15_20": len(prices[(prices >= 15) & (prices < 20)]),
                "over_20": len(prices[prices >= 20])
            }
        }
    
    def _calculate_statistics(self, prices: pd.Series, df: pd.DataFrame) -> Dict[str, Any]:
        """통계값 계산"""
        stats = {
            "count": len(prices),
            "min_price": float(prices.min()),
            "max_price": float(prices.max()),
            "median_price": float(prices.median()),
            "mean_price": float(prices.mean()),
            "std_price": float(prices.std())
        }
        
        # 면적별 가격 (있는 경우)
        if '전용면적제곱미터' in df.columns:
            areas = df['전용면적제곱미터'].astype(float)
            price_per_m2 = prices * 10000 / areas  # 만원/m²
            stats["price_per_m2"] = {
                "mean": float(price_per_m2.mean()),
                "median": float(price_per_m2.median())
            }
        
        return stats
    
    def _analyze_dong_price_difference(self, df: pd.DataFrame) -> Dict[str, Any]:
        """동별 가격 차이 분석"""
        if '동명' not in df.columns or '가격' not in df.columns:
            return {"error": "동명 또는 가격 정보 없음"}
        
        df_clean = df[['동명', '가격']].dropna()
        if df_clean.empty:
            return {"error": "데이터 없음"}
        
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        
        dong_stats = df_clean.groupby('동명')['가격_억'].agg(['mean', 'count', 'min', 'max']).to_dict('index')
        
        # 평균 가격 기준 정렬
        sorted_dongs = sorted(
            dong_stats.items(), 
            key=lambda x: x[1]['mean'], 
            reverse=True
        )
        
        return {
            "dong_count": len(dong_stats),
            "highest_avg_dong": sorted_dongs[0][0] if sorted_dongs else "N/A",
            "lowest_avg_dong": sorted_dongs[-1][0] if sorted_dongs else "N/A",
            "price_gap": sorted_dongs[0][1]['mean'] - sorted_dongs[-1][1]['mean'] if len(sorted_dongs) > 1 else 0,
            "details": {dong: {
                "avg_price": float(stats['mean']),
                "count": int(stats['count']),
                "min_price": float(stats['min']),
                "max_price": float(stats['max'])
            } for dong, stats in dong_stats.items()}
        }
    
    def _extract_special_notes(self, df: pd.DataFrame) -> List[str]:
        """특이사항 추출"""
        notes = []
        
        # 최고가/최저가
        if '가격' in df.columns:
            prices = df['가격'].astype(float)
            max_price_idx = prices.idxmax()
            min_price_idx = prices.idxmin()
            
            max_price_row = df.loc[max_price_idx]
            min_price_row = df.loc[min_price_idx]
            
            notes.append(f"최고가: {max_price_row.get('가격표시', 'N/A')} ({max_price_row.get('동명', 'N/A')}동, {max_price_row.get('층수정보', 'N/A')})")
            notes.append(f"최저가: {min_price_row.get('가격표시', 'N/A')} ({min_price_row.get('동명', 'N/A')}동, {min_price_row.get('층수정보', 'N/A')})")
        
        # 로얄층/로얄동
        if '층수정보' in df.columns and '동명' in df.columns:
            # 상위층 비율이 높은 동
            dong_floor_stats = df.groupby('동명')['층수정보'].apply(
                lambda x: self._calculate_high_floor_ratio(x)
            )
            if not dong_floor_stats.empty:
                top_dong = dong_floor_stats.idxmax()
                notes.append(f"고층 비율 높은 동: {top_dong}")
        
        return notes
    
    def _calculate_high_floor_ratio(self, floor_series: pd.Series) -> float:
        """고층 비율 계산"""
        high_count = 0
        total = 0
        
        for floor_str in floor_series.dropna():
            try:
                if '/' in str(floor_str):
                    current, total_floors = str(floor_str).split('/')
                    ratio = int(current) / int(total_floors) if int(total_floors) > 0 else 0
                    if ratio >= 0.8:  # 상위 20%
                        high_count += 1
                    total += 1
            except:
                continue
        
        return high_count / total if total > 0 else 0

