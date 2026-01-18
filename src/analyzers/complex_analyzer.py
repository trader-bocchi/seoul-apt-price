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
        
        # 층/동/향별 상세 분석
        detailed_analysis = self._analyze_detailed_factors(df)
        
        return {
            "complex_name": self.complex_name,
            "total_count": len(df),
            "price_distribution_by_area": price_distribution_by_area,  # 평형대별 가격 분포
            "area_analysis": area_analysis,  # 평형별 분석
            "dong_price_diff": dong_price_diff,
            "detailed_analysis": detailed_analysis  # 층/동/향별 상세 분석
        }
    
    def _analyze_by_area(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        면적별 분석 (전용면적제곱미터 직접 사용)
        
        Args:
            df: 매물 데이터 DataFrame
        
        Returns:
            면적별 분석 결과 딕셔너리
        """
        if '전용면적제곱미터' not in df.columns or '가격' not in df.columns:
            return {"error": "면적 또는 가격 정보 없음"}
        
        # 전용면적제곱미터를 직접 사용 (고유값으로 구분)
        df_clean = df[['전용면적제곱미터', '가격', '동명', '층수정보', '방향']].copy()
        df_clean['전용면적제곱미터'] = pd.to_numeric(df_clean['전용면적제곱미터'], errors='coerce')
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        df_clean = df_clean.dropna(subset=['전용면적제곱미터', '가격_억'])
        
        if df_clean.empty:
            return {"error": "유효한 면적/가격 데이터 없음"}
        
        # 고유 면적값으로 그룹화 (소수점 내림처리: 51.5, 51.7, 51.9 -> 51로 묶기)
        import math
        # 먼저 면적을 내림처리한 컬럼 추가
        df_clean['면적대'] = df_clean['전용면적제곱미터'].apply(lambda x: math.floor(float(x)) if pd.notna(x) else None)
        
        area_groups = {}
        for area_key, group_df in df_clean.groupby('면적대'):
            if pd.isna(area_key):
                continue
            group_prices = group_df['가격_억']
            
            # 가장 많은 향
            directions = group_df['방향'].dropna().tolist()
            most_common_direction = pd.Series(directions).mode()[0] if directions else "N/A"
            
            area_groups[int(area_key)] = {
                "count": len(group_df),
                "min_price": float(group_prices.min()),
                "max_price": float(group_prices.max()),
                "median_price": float(group_prices.median()),
                "mean_price": float(group_prices.mean()),
                "most_common_direction": most_common_direction
            }
        
        # 면적별 정렬 (면적 순)
        sorted_areas = sorted(area_groups.items(), key=lambda x: x[0])
        
        return {
            "area_types": {area: data for area, data in sorted_areas},
            "total_area_types": len(area_groups)
        }
    
    def _calculate_price_distribution_by_area(self, df: pd.DataFrame, area_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        면적대별 가격 분포 계산 (전용면적제곱미터 직접 사용)
        
        Args:
            df: 매물 데이터 DataFrame
            area_analysis: 면적별 분석 결과
        
        Returns:
            면적대별 가격 분포 딕셔너리
        """
        if "error" in area_analysis or not area_analysis.get("area_types"):
            return {"error": "면적별 분석 데이터 없음"}
        
        if '전용면적제곱미터' not in df.columns:
            return {"error": "면적 정보 없음"}
        
        # 전용면적제곱미터를 직접 사용 (고유값으로 구분)
        df_clean = df[['전용면적제곱미터', '가격']].copy()
        df_clean['전용면적제곱미터'] = pd.to_numeric(df_clean['전용면적제곱미터'], errors='coerce')
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        df_clean = df_clean.dropna(subset=['전용면적제곱미터', '가격_억'])
        
        if df_clean.empty:
            return {"error": "유효한 데이터 없음"}
        
        # 고유 면적값으로 그룹화 (소수점 내림처리: 51.5, 51.7, 51.9 -> 51로 묶기)
        import math
        # 먼저 면적을 내림처리한 컬럼 추가
        df_clean['면적대'] = df_clean['전용면적제곱미터'].apply(lambda x: math.floor(float(x)) if pd.notna(x) else None)
        
        distribution_by_area = {}
        for area_key, group_df in df_clean.groupby('면적대'):
            if pd.isna(area_key):
                continue
            group_prices = group_df['가격_억']
            
            distribution_by_area[int(area_key)] = {
                "count": len(group_df),
                "min": float(group_prices.min()),
                "max": float(group_prices.max()),
                "median": float(group_prices.median()),
                "mean": float(group_prices.mean()),
                "q25": float(group_prices.quantile(0.25)),
                "q75": float(group_prices.quantile(0.75))
            }
        
        # 전체 통합 통계 (모든 면적대 통합)
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
    
    def _analyze_detailed_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        층/동/향별 호가 차이 상세 분석 (평형대별로 구분)
        
        Args:
            df: 매물 데이터 DataFrame
        
        Returns:
            평형대별 층/동/향별 분석 결과 딕셔너리
        """
        # 전용면적제곱미터를 직접 사용
        if '전용면적제곱미터' not in df.columns:
            return {"error": "면적 정보 없음"}
        
        # 필요한 컬럼 확인 및 선택
        required_cols = ['가격', '층수정보', '동명', '방향', '전용면적제곱미터']
        if '매물특징설명' in df.columns:
            required_cols.append('매물특징설명')
        df_clean = df[required_cols].copy()
        df_clean['전용면적제곱미터'] = pd.to_numeric(df_clean['전용면적제곱미터'], errors='coerce')
        df_clean['가격_억'] = df_clean['가격'].astype(float) / 10000
        df_clean = df_clean.dropna(subset=['가격_억', '전용면적제곱미터'])
        
        if df_clean.empty:
            return {"error": "유효한 데이터 없음"}
        
        # 면적대별로 그룹화 (소수점 내림처리: 51.5, 51.7, 51.9 -> 51로 묶기)
        import math
        df_clean['면적대'] = df_clean['전용면적제곱미터'].apply(lambda x: math.floor(float(x)) if pd.notna(x) else None)
        
        result = {}
        
        # 평형대별로 분석
        for area_type, area_group in df_clean.groupby('면적대'):
            if pd.isna(area_type):
                continue
            area_key = int(area_type)
            area_result = {}
        
            # 층별 분석
            if '층수정보' in area_group.columns:
                floor_prices = []
                for idx, row in area_group.iterrows():
                    floor_str = str(row.get('층수정보', ''))
                    if '/' in floor_str:
                        try:
                            current_floor = int(floor_str.split('/')[0])
                            floor_prices.append({
                                'floor': current_floor,
                                'price': row['가격_억']
                            })
                        except:
                            continue
                
                if floor_prices:
                    floor_df = pd.DataFrame(floor_prices)
                    # 층을 구간별로 나누기 (저층: 1-5층, 중층: 6-10층, 고층: 11-15층)
                    floor_df['floor_category'] = pd.cut(
                        floor_df['floor'],
                        bins=[0, 5, 10, 15, 100],
                        labels=['저층(1-5층)', '중층(6-10층)', '고층(11-15층)', '초고층(16층+)']
                    )
                    
                    floor_stats = floor_df.groupby('floor_category')['price'].agg(['mean', 'count', 'min', 'max']).to_dict('index')
                    area_result['floor_analysis'] = {
                        k: {
                            'avg_price': float(v['mean']),
                            'count': int(v['count']),
                            'min_price': float(v['min']),
                            'max_price': float(v['max'])
                        }
                        for k, v in floor_stats.items()
                    }
            
            # 동별 분석
            if '동명' in area_group.columns:
                dong_df = area_group[['동명', '가격_억']].dropna(subset=['동명'])
                if not dong_df.empty:
                    dong_stats = dong_df.groupby('동명')['가격_억'].agg(['mean', 'count', 'min', 'max']).to_dict('index')
                    # 평균 가격 기준 정렬
                    sorted_dongs = sorted(dong_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
                    area_result['dong_analysis'] = {
                        'total_dongs': len(dong_stats),
                        'highest_dong': sorted_dongs[0][0] if sorted_dongs else "N/A",
                        'lowest_dong': sorted_dongs[-1][0] if sorted_dongs else "N/A",
                        'price_gap': float(sorted_dongs[0][1]['mean'] - sorted_dongs[-1][1]['mean']) if len(sorted_dongs) > 1 else 0,
                        'details': {
                            dong: {
                                'avg_price': float(stats['mean']),
                                'count': int(stats['count']),
                                'min_price': float(stats['min']),
                                'max_price': float(stats['max'])
                            }
                            for dong, stats in sorted_dongs[:3]  # 상위 3개만
                        }
                    }
            
            # 향별 분석
            if '방향' in area_group.columns:
                direction_df = area_group[['방향', '가격_억']].dropna(subset=['방향'])
                if not direction_df.empty:
                    direction_stats = direction_df.groupby('방향')['가격_억'].agg(['mean', 'count', 'min', 'max']).to_dict('index')
                    # 평균 가격 기준 정렬
                    sorted_directions = sorted(direction_stats.items(), key=lambda x: x[1]['mean'], reverse=True)
                    area_result['direction_analysis'] = {
                        'total_directions': len(direction_stats),
                        'highest_direction': sorted_directions[0][0] if sorted_directions else "N/A",
                        'lowest_direction': sorted_directions[-1][0] if sorted_directions else "N/A",
                        'price_gap': float(sorted_directions[0][1]['mean'] - sorted_directions[-1][1]['mean']) if len(sorted_directions) > 1 else 0,
                        'details': {
                            direction: {
                                'avg_price': float(stats['mean']),
                                'count': int(stats['count']),
                                'min_price': float(stats['min']),
                                'max_price': float(stats['max'])
                            }
                            for direction, stats in sorted_directions[:3]  # 상위 3개만
                        }
                    }
            
            # 매물 특징 분석
            if '매물특징설명' in area_group.columns:
                feature_df = area_group[['매물특징설명', '가격_억']].dropna(subset=['매물특징설명'])
                if not feature_df.empty:
                    # 매물 특징 텍스트에서 주요 키워드 추출 및 분석
                    features = feature_df['매물특징설명'].tolist()
                    feature_text = ' '.join([str(f) for f in features if f])
                    
                    # 주요 키워드 추출 (간단한 빈도 분석)
                    import re
                    from collections import Counter
                    
                    # 한글 단어 추출 (2글자 이상)
                    words = re.findall(r'[가-힣]{2,}', feature_text)
                    word_counts = Counter(words)
                    
                    # 상위 키워드 추출 (빈도 2회 이상)
                    top_keywords = {word: count for word, count in word_counts.most_common(10) if count >= 2}
                    
                    # 매물 특징 요약
                    feature_summary = {
                        'total_with_features': len(feature_df),
                        'top_keywords': top_keywords,
                        'sample_features': [str(f) for f in features[:3] if f]  # 샘플 3개
                    }
                    
                    area_result['feature_analysis'] = feature_summary
            
            if area_result:
                result[area_key] = area_result
        
        return result if result else {"error": "분석 데이터 없음"}
    
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

