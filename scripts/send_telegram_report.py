"""
텔레그램 리포트 전송 스크립트
"""
import logging
import sys
from pathlib import Path
from typing import List, Dict
import pandas as pd
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.env_loader import EnvConfig
from src.analyzers.complex_analyzer import ComplexAnalyzer
from src.notifiers.telegram import TelegramNotifier

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_all_offers_by_complex(complex_names: List[str], days: int = None) -> Dict[str, pd.DataFrame]:
    """
    data/raw의 모든 파일을 읽어서 단지명으로 필터링 (전체 매물)
    
    Args:
        complex_names: 분석할 단지명 리스트
        days: 사용 안 함 (전체 매물 로드)
    
    Returns:
        {단지명: DataFrame} 딕셔너리
    """
    import pandas as pd
    
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        logger.warning(f"Data directory not found: {raw_dir}")
        return {}
    
    # 모든 지역 폴더의 offers 파일 찾기
    all_offers = []
    for region_dir in raw_dir.iterdir():
        if not region_dir.is_dir():
            continue
        
        offer_files = list(region_dir.glob("offers_*.csv"))
        for offer_file in offer_files:
            try:
                df = pd.read_csv(offer_file, encoding='utf-8-sig')
                if '단지명' not in df.columns:
                    continue
                all_offers.append(df)
            except Exception as e:
                logger.warning(f"Error reading {offer_file}: {e}")
                continue
    
    if not all_offers:
        logger.warning("No offer files found in data/raw")
        return {}
    
    # 모든 데이터 합치기 (전체 매물, 날짜 필터링 없음)
    combined_df = pd.concat(all_offers, ignore_index=True)
    
    # 단지명으로 필터링 및 그룹화
    result = {}
    for complex_name in complex_names:
        # 단지명이 정확히 일치하거나 포함되는 경우
        filtered = combined_df[
            combined_df['단지명'].str.contains(complex_name, na=False, case=False)
        ]
        if not filtered.empty:
            result[complex_name] = filtered
            logger.info(f"  {complex_name}: {len(filtered)}개 매물 발견")
    
    return result


def main():
    """메인 실행 함수"""
    try:
        # 환경 변수 확인
        my_home = EnvConfig.get_my_home_complex_name()
        target_homes = EnvConfig.get_target_home_complex_names()
        
        # 분석할 단지명 리스트 구성
        complex_names = []
        if my_home:
            complex_names.append(my_home)
        if target_homes:
            complex_names.extend(target_homes)
        
        if not complex_names:
            logger.error("MY_HOME_COMPLEX_NAME 또는 TARGET_HOME_COMPLEX_NAME이 설정되지 않았습니다.")
            sys.exit(1)
        
        # 텔레그램 설정 확인
        try:
            notifier = TelegramNotifier()
        except ValueError as e:
            logger.error(f"텔레그램 설정 오류: {e}")
            logger.info("텔레그램 알림을 받으려면 .env 파일에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
            sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("텔레그램 리포트 전송 시작")
        logger.info("=" * 60)
        
        # data/raw의 모든 파일을 읽어서 단지명으로 필터링 (전체 매물)
        logger.info(f"\n[1/2] data/raw에서 단지별 매물 데이터 로드 중...")
        logger.info(f"분석 대상 단지: {', '.join(complex_names)}")
        
        complex_data = load_all_offers_by_complex(complex_names, days=None)  # 전체 매물
        
        if not complex_data:
            logger.error("분석할 데이터가 없습니다. data/raw에 CSV 파일이 있는지 확인하세요.")
            sys.exit(1)
        
        # 각 단지별로 분석
        logger.info(f"\n[2/2] 단지별 분석 및 리포트 전송 중...")
        
        my_analysis = None
        target_analyses = {}
        all_analyses = {}  # 모든 단지 분석 (통합 메시지용)
        
        # 1단계: 모든 단지 분석
        for complex_name in complex_names:
            if complex_name not in complex_data:
                logger.warning(f"{complex_name}에 대한 데이터가 없습니다.")
                continue
            
            logger.info(f"\n{complex_name} 분석 중...")
            df = complex_data[complex_name]
            
            analyzer = ComplexAnalyzer(complex_name)
            analysis = analyzer.analyze_complex_from_dataframe(df)
            
            if analysis.get("total_count", 0) == 0:
                logger.warning(f"{complex_name}에 대한 분석 결과가 없습니다.")
                continue
            
            logger.info(f"✓ {complex_name} 분석 완료 ({analysis['total_count']}개 매물)")
            
            # 모든 분석 저장
            all_analyses[complex_name] = analysis
            
            # MY_HOME인 경우 저장
            if complex_name == my_home:
                my_analysis = analysis
            else:
                target_analyses[complex_name] = analysis
        
        # 2단계: 첫 번째 메시지 - 모든 단지 분석 통합 리포트
        if all_analyses:
            logger.info(f"\n[메시지 1/2] 모든 단지 분석 리포트 전송 중...")
            success = notifier.send_all_complexes_analysis(all_analyses)
            if success:
                logger.info(f"✓ 단지 분석 리포트 전송 완료")
            else:
                logger.error(f"✗ 단지 분석 리포트 전송 실패")
        
        # 3단계: 두 번째 메시지 - 가격 비교 분석 통합 리포트
        if my_analysis and my_analysis.get("total_count", 0) > 0 and target_analyses:
            # 유효한 타겟만 필터링
            valid_targets = {
                name: data for name, data in target_analyses.items()
                if data.get("total_count", 0) > 0
            }
            
            if valid_targets:
                logger.info(f"\n[메시지 2/2] 가격 비교 분석 리포트 전송 중...")
                success = notifier.send_all_comparisons(my_analysis, valid_targets)
                if success:
                    logger.info(f"✓ 가격 비교 분석 리포트 전송 완료")
                else:
                    logger.error(f"✗ 가격 비교 분석 리포트 전송 실패")
        
        logger.info("\n" + "=" * 60)
        logger.info("모든 리포트 전송 완료!")
        logger.info("=" * 60)
    
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

