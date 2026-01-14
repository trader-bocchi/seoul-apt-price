"""
CSV 저장 공통 유틸리티
"""
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path


class CSVStore:
    """CSV 저장 유틸리티 클래스"""
    
    BASE_DATA_DIR = Path("data")
    RAW_DATA_DIR = BASE_DATA_DIR / "raw"
    TELEGRAM_LOGS_DIR = BASE_DATA_DIR / "telegram_logs"
    
    @staticmethod
    def ensure_directory(path: Path):
        """디렉토리가 없으면 생성"""
        path.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def save_raw_offers(
        complex_name: str,
        properties: List[Dict],
        date: Optional[datetime] = None
    ) -> str:
        """
        Raw 호가 데이터 저장
        
        Args:
            complex_name: 단지명
            properties: 매물 정보 리스트
            date: 수집 일자 (None이면 현재 날짜)
        
        Returns:
            저장된 파일 경로
        
        Raises:
            ValueError: 복수 행정동이 _로 연결된 이름인 경우
        """
        # 복수 행정동이 _로 연결된 이름인지 확인
        # 예: "성남시_수정구_신흥동_서울시_성동구_금호동1가" 같은 패턴
        if CSVStore._is_combined_region_name(complex_name):
            raise ValueError(
                f"복수 행정동이 _로 연결된 이름은 저장할 수 없습니다: {complex_name}"
            )
        
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        complex_dir = CSVStore.RAW_DATA_DIR / complex_name
        CSVStore.ensure_directory(complex_dir)
        
        filename = complex_dir / f"offers_{date_str}.csv"
        
        # 기존 파일이 있으면 삭제 (덮어쓰기 보장)
        if filename.exists():
            filename.unlink()
        
        # 빈 리스트여도 저장 (빈 DataFrame으로)
        if properties:
            df = pd.DataFrame(properties)
        else:
            # 빈 리스트인 경우 빈 DataFrame 생성 (컬럼만 정의)
            df = pd.DataFrame(columns=[
                "item_id", "complex_name", "property_type", "trade_type",
                "price", "price_display", "latitude", "longitude", "collected_at"
            ])
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return str(filename)
    
    @staticmethod
    def _is_combined_region_name(name: str) -> bool:
        """
        복수 행정동이 _로 연결된 이름인지 확인
        
        Args:
            name: 확인할 이름
        
        Returns:
            복수 행정동 이름이면 True
        
        Note:
            "경기도 성남시 중원구 여수동" 같은 경우는 단일 행정동이므로 False를 반환합니다.
            "_"로 연결된 경우만 복수 행정동으로 판단합니다.
            예: "성남시_수정구_신흥동_서울시_성동구_금호동1가"
        """
        # "_"로 연결된 경우만 복수 행정동으로 판단
        # 예: "성남시_수정구_신흥동_서울시_성동구_금호동1가"
        if "_" not in name:
            return False
        
        # "_"로 분리했을 때 시/도 패턴이 2개 이상이면 복수 행정동
        import re
        
        parts = name.split("_")
        city_pattern = r'([가-힣]+(?:시|도))'
        
        city_count = 0
        for part in parts:
            matches = re.findall(city_pattern, part)
            if matches:
                city_count += len(matches)
        
        # 시/도가 2개 이상이면 복수 행정동으로 판단
        return city_count >= 2
    
    @staticmethod
    def save_raw_prices(
        complex_name: str,
        price_data: Dict,
        date: Optional[datetime] = None
    ) -> str:
        """
        Raw 시세 데이터 저장
        
        Args:
            complex_name: 단지명
            price_data: 시세 정보 딕셔너리
            date: 수집 일자 (None이면 현재 날짜)
        
        Returns:
            저장된 파일 경로
        
        Raises:
            ValueError: 복수 행정동이 _로 연결된 이름인 경우
        """
        # 복수 행정동이 _로 연결된 이름인지 확인
        if CSVStore._is_combined_region_name(complex_name):
            raise ValueError(
                f"복수 행정동이 _로 연결된 이름은 저장할 수 없습니다: {complex_name}"
            )
        
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        complex_dir = CSVStore.RAW_DATA_DIR / complex_name
        CSVStore.ensure_directory(complex_dir)
        
        filename = complex_dir / f"prices_{date_str}.csv"
        
        # 단일 행 데이터를 DataFrame으로 변환
        df = pd.DataFrame([price_data])
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return str(filename)
    
    @staticmethod
    def save_telegram_log(
        message_type: str,
        data: Dict,
        date: Optional[datetime] = None
    ) -> str:
        """
        텔레그램 전송 백데이터 저장
        
        Args:
            message_type: 메시지 타입 (summary, drop_alert 등)
            data: 전송 데이터 딕셔너리
            date: 전송 일자 (None이면 현재 날짜)
        
        Returns:
            저장된 파일 경로
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        CSVStore.ensure_directory(CSVStore.TELEGRAM_LOGS_DIR)
        
        filename = CSVStore.TELEGRAM_LOGS_DIR / f"telegram_{message_type}_{date_str}.csv"
        
        # 기존 파일이 있으면 append, 없으면 새로 생성
        if filename.exists():
            df_existing = pd.read_csv(filename)
            df_new = pd.DataFrame([data])
            df = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df = pd.DataFrame([data])
        
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        return str(filename)
    
    @staticmethod
    def load_historical_prices(
        complex_name: str,
        days_back: int = 365
    ) -> Optional[pd.DataFrame]:
        """
        과거 시세 데이터 로드
        
        Args:
            complex_name: 단지명
            days_back: 몇 일 전까지의 데이터를 가져올지
        
        Returns:
            과거 시세 데이터 DataFrame 또는 None
        """
        complex_dir = CSVStore.RAW_DATA_DIR / complex_name
        
        if not complex_dir.exists():
            return None
        
        # 해당 단지의 모든 prices 파일 찾기
        price_files = list(complex_dir.glob("prices_*.csv"))
        
        if not price_files:
            return None
        
        # 파일명에서 날짜 추출하여 정렬
        price_files.sort(key=lambda x: x.name, reverse=True)
        
        # 최근 days_back 일 이내의 파일만 로드
        all_data = []
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for file in price_files:
            try:
                # 파일명에서 날짜 추출 (prices_YYYYMMDD.csv)
                date_str = file.stem.split('_')[1]
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if (cutoff_date - file_date).days <= days_back:
                    df = pd.read_csv(file)
                    df['date'] = file_date
                    all_data.append(df)
            except Exception:
                continue
        
        if not all_data:
            return None
        
        return pd.concat(all_data, ignore_index=True)
    
    @staticmethod
    def save_collection_step(
        region_name: str,
        step_name: str,
        properties: List[Dict],
        complexes: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        수집 단계별 중간 데이터 저장 (디버깅용)
        
        Args:
            region_name: 지역명
            step_name: 단계명 (step1_basic, step2_cluster, step3_matched 등)
            properties: 매물 정보 리스트
            complexes: 단지 정보 리스트 (선택사항)
            metadata: 추가 메타데이터 (선택사항)
        
        Returns:
            저장된 파일 경로
        
        Raises:
            ValueError: 복수 행정동이 _로 연결된 이름인 경우
        """
        # 복수 행정동이 _로 연결된 이름인지 확인
        if CSVStore._is_combined_region_name(region_name):
            raise ValueError(
                f"복수 행정동이 _로 연결된 이름은 저장할 수 없습니다: {region_name}"
            )
        
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_dir = CSVStore.RAW_DATA_DIR / region_name / "debug"
        CSVStore.ensure_directory(debug_dir)
        
        # 매물 데이터 저장
        filename = debug_dir / f"{step_name}_properties_{date_str}.csv"
        if properties:
            df = pd.DataFrame(properties)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        # 단지 데이터 저장 (있는 경우)
        if complexes:
            complex_filename = debug_dir / f"{step_name}_complexes_{date_str}.csv"
            df_complex = pd.DataFrame(complexes)
            df_complex.to_csv(complex_filename, index=False, encoding='utf-8-sig')
        
        # 메타데이터 저장 (있는 경우)
        if metadata:
            metadata_filename = debug_dir / f"{step_name}_metadata_{date_str}.csv"
            df_meta = pd.DataFrame([metadata])
            df_meta.to_csv(metadata_filename, index=False, encoding='utf-8-sig')
        
        return str(filename)

