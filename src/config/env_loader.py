"""
.env 파일에서 단지명 및 설정 로드
"""
import os
from typing import Optional, List
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


class EnvConfig:
    """환경 변수 설정 클래스"""
    
    @staticmethod
    def get_current_home_complex_name() -> Optional[str]:
        """
        현재 거주 중인 단지명 반환 (하위 호환성)
        
        Returns:
            단지명 또는 None
        """
        return EnvConfig.get_my_home_complex_name() or os.getenv("CURRENT_HOME_COMPLEX_NAME")
    
    @staticmethod
    def get_my_home_complex_name() -> Optional[str]:
        """
        내 집 단지명 반환 (MY_HOME_COMPLEX_NAME)
        
        Returns:
            단지명 또는 None
        """
        return os.getenv("MY_HOME_COMPLEX_NAME")
    
    @staticmethod
    def get_target_home_complex_name() -> Optional[str]:
        """
        향후 거주 희망 단지명 반환 (단일 값, 하위 호환성)
        
        Returns:
            첫 번째 관심 단지명 또는 None
        """
        names = EnvConfig.get_target_home_complex_names()
        return names[0] if names else None
    
    @staticmethod
    def get_target_home_complex_names() -> List[str]:
        """
        향후 거주 희망 단지명 리스트 반환 (여러 개 지원)
        
        .env 파일에서 쉼표(,)로 구분된 단지명을 파싱하여 리스트로 반환
        
        Returns:
            단지명 리스트 (빈 리스트 가능)
        """
        target_complex = os.getenv("TARGET_HOME_COMPLEX_NAME")
        if not target_complex:
            return []
        
        # 쉼표로 구분하여 리스트로 변환
        complexes = [name.strip() for name in target_complex.split(",") if name.strip()]
        return complexes
    
    @staticmethod
    def get_telegram_bot_token() -> Optional[str]:
        """
        텔레그램 봇 토큰 반환
        
        Returns:
            봇 토큰 또는 None
        """
        return os.getenv("TELEGRAM_BOT_TOKEN")
    
    @staticmethod
    def get_telegram_chat_id() -> Optional[str]:
        """
        텔레그램 채팅 ID 반환
        
        Returns:
            채팅 ID 또는 None
        """
        return os.getenv("TELEGRAM_CHAT_ID")
    
    @staticmethod
    def validate_config() -> tuple[bool, list[str]]:
        """
        필수 환경 변수 검증
        
        Returns:
            (검증 성공 여부, 누락된 변수 리스트)
        """
        missing = []
        
        if not EnvConfig.get_current_home_complex_name():
            missing.append("CURRENT_HOME_COMPLEX_NAME")
        
        # 여러 개의 단지명이 설정되어 있는지 확인
        target_complexes = EnvConfig.get_target_home_complex_names()
        if not target_complexes:
            missing.append("TARGET_HOME_COMPLEX_NAME")
        
        return len(missing) == 0, missing
    
    @staticmethod
    def get_interest_complexes() -> dict[str, Optional[str]]:
        """
        관심 단지 정보 반환 (하위 호환성)
        
        Returns:
            {"current": 현재 거주 단지명, "target": 관심 단지명 (첫 번째)}
        """
        target_complexes = EnvConfig.get_target_home_complex_names()
        return {
            "current": EnvConfig.get_current_home_complex_name(),
            "target": target_complexes[0] if target_complexes else None
        }
    
    @staticmethod
    def get_all_interest_complexes() -> dict[str, List[str]]:
        """
        모든 관심 단지 정보 반환 (여러 개 지원)
        
        Returns:
            {"current": [현재 거주 단지명], "target": [관심 단지명 리스트]}
        """
        current = EnvConfig.get_current_home_complex_name()
        return {
            "current": [current] if current else [],
            "target": EnvConfig.get_target_home_complex_names()
        }
    
    @staticmethod
    def get_region_name() -> Optional[str]:
        """
        행정구역명 반환 (단일 값, 하위 호환성)
        
        .env 파일에서 REGION_NAME 환경 변수를 읽어 반환합니다.
        예: "성남시 수정구 신흥동"
        
        Returns:
            첫 번째 행정구역명 또는 None
        """
        names = EnvConfig.get_region_names()
        return names[0] if names else None
    
    @staticmethod
    def get_region_names() -> List[str]:
        """
        행정구역명 리스트 반환 (여러 개 지원)
        
        .env 파일에서 쉼표(,)로 구분된 행정구역명을 파싱하여 리스트로 반환합니다.
        예: REGION_NAME=성남시 수정구 신흥동,서울시 강남구 역삼동
        
        Returns:
            행정구역명 리스트 (빈 리스트 가능)
        """
        region_name = os.getenv("REGION_NAME")
        if not region_name:
            return []
        
        # 쉼표로 구분하여 리스트로 변환
        regions = [name.strip() for name in region_name.split(",") if name.strip()]
        return regions
    
    @staticmethod
    def validate_region_config() -> tuple[bool, list[str]]:
        """
        행정구역 설정 검증
        
        Returns:
            (검증 성공 여부, 누락된 변수 리스트)
        """
        missing = []
        
        region_names = EnvConfig.get_region_names()
        if not region_names:
            missing.append("REGION_NAME")
        
        return len(missing) == 0, missing
    
    @staticmethod
    def get_region_cortar_no() -> Optional[str]:
        """
        직접 지정한 cortarNo 반환 (선택사항)
        
        .env 파일에서 REGION_CORTAR_NO 환경 변수를 읽어 반환합니다.
        지역 정보 조회가 실패할 경우 이 값을 사용할 수 있습니다.
        
        Returns:
            cortarNo 또는 None
        """
        return os.getenv("REGION_CORTAR_NO")
    
    @staticmethod
    def get_region_coordinates() -> Optional[tuple[float, float]]:
        """
        직접 지정한 좌표 반환 (선택사항)
        
        .env 파일에서 REGION_LAT, REGION_LON 환경 변수를 읽어 반환합니다.
        형식: REGION_LAT=37.4473, REGION_LON=127.1493
        
        Returns:
            (lat, lon) 튜플 또는 None
        """
        lat_str = os.getenv("REGION_LAT")
        lon_str = os.getenv("REGION_LON")
        
        if lat_str and lon_str:
            try:
                return (float(lat_str), float(lon_str))
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def get_region_tot_cnt() -> Optional[int]:
        """
        직접 지정한 총 매물 개수 반환 (선택사항)
        
        .env 파일에서 REGION_TOT_CNT 환경 변수를 읽어 반환합니다.
        형식: REGION_TOT_CNT=209
        
        Returns:
            총 매물 개수 또는 None
        """
        tot_cnt_str = os.getenv("REGION_TOT_CNT")
        if tot_cnt_str:
            try:
                return int(tot_cnt_str)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def get_price_filter_min() -> Optional[int]:
        """
        가격 필터 최소값 반환 (선택사항)
        
        .env 파일에서 FILTER_DPRC_MIN 환경 변수를 읽어 반환합니다.
        형식: FILTER_DPRC_MIN=80000 (8억, 만원 단위)
        
        Returns:
            최소 가격 (만원 단위) 또는 None
        """
        dprc_min_str = os.getenv("FILTER_DPRC_MIN")
        if dprc_min_str:
            try:
                return int(dprc_min_str)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def get_price_filter_max() -> Optional[int]:
        """
        가격 필터 최대값 반환 (선택사항)
        
        .env 파일에서 FILTER_DPRC_MAX 환경 변수를 읽어 반환합니다.
        형식: FILTER_DPRC_MAX=130000 (13억, 만원 단위)
        
        Returns:
            최대 가격 (만원 단위) 또는 None
        """
        dprc_max_str = os.getenv("FILTER_DPRC_MAX")
        if dprc_max_str:
            try:
                return int(dprc_max_str)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def get_area_filter_min() -> Optional[int]:
        """
        면적 필터 최소값 반환 (선택사항)
        
        .env 파일에서 FILTER_SPC_MIN 환경 변수를 읽어 반환합니다.
        형식: FILTER_SPC_MIN=33 (33평)
        
        Returns:
            최소 면적 (평 단위) 또는 None
        """
        spc_min_str = os.getenv("FILTER_SPC_MIN")
        if spc_min_str:
            try:
                return int(spc_min_str)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def get_area_filter_max() -> Optional[int]:
        """
        면적 필터 최대값 반환 (선택사항)
        
        .env 파일에서 FILTER_SPC_MAX 환경 변수를 읽어 반환합니다.
        형식: FILTER_SPC_MAX=99 (99평)
        
        Returns:
            최대 면적 (평 단위) 또는 None
        """
        spc_max_str = os.getenv("FILTER_SPC_MAX")
        if spc_max_str:
            try:
                return int(spc_max_str)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def get_my_home_area() -> Optional[float]:
        """
        내 집 면적 반환 (선택사항)
        
        .env 파일에서 MY_HOME_AREA 환경 변수를 읽어 반환합니다.
        형식: MY_HOME_AREA=51.0 (m² 단위)
        
        Returns:
            면적 (m²) 또는 None
        """
        area_str = os.getenv("MY_HOME_AREA")
        if area_str:
            try:
                return float(area_str)
            except ValueError:
                return None
        return None

