"""
배치 수집 및 알림 실행 스크립트
"""
import sys
from datetime import datetime
from src.config.env_loader import EnvConfig
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.collectors.data_collector import DataCollector, Property
from src.collectors.api_client import ApiConfig
from src.storage.csv_store import CSVStore
from src.processors.price_analyzer import PriceAnalyzer
from src.processors.distribution_analyzer import DistributionAnalyzer
from src.notifiers.telegram import TelegramNotifier
# utils는 프로젝트 루트에 있으므로 직접 import
try:
    from utils import geocode_address
except ImportError:
    # utils가 없으면 pass
    def geocode_address(address):
        return None


def collect_interest_complexes():
    """관심 단지 수집 및 분석 (여러 개 지원)"""
    # 환경 변수 검증
    is_valid, missing = EnvConfig.validate_config()
    if not is_valid:
        print(f"❌ 필수 환경 변수가 누락되었습니다: {', '.join(missing)}")
        print("⚠️  .env 파일을 확인하세요.")
        return
    
    # 관심 단지 정보 로드 (여러 개 지원)
    all_complexes = EnvConfig.get_all_interest_complexes()
    current_complex = all_complexes["current"][0] if all_complexes["current"] else None
    target_complexes = all_complexes["target"]
    
    print(f"📋 현재 거주 단지: {current_complex}")
    print(f"🎯 관심 단지 ({len(target_complexes)}개): {', '.join(target_complexes)}")
    
    # 수집기 초기화
    api_config = ApiConfig(min_delay=1.0, timeout=10, max_retries=3)
    collector = DataCollector(api_config)
    
    # 각 관심 단지에 대해 순회하며 처리
    for idx, target_complex in enumerate(target_complexes, 1):
        print(f"\n{'='*60}")
        print(f"📌 [{idx}/{len(target_complexes)}] {target_complex} 처리 중...")
        print(f"{'='*60}")
        
        # 관심 단지 수집 (간단한 좌표 사용 - 실제로는 단지 좌표를 조회해야 함)
        # TODO: 단지명으로 좌표 조회하는 로직 추가 필요
        print(f"\n🔍 {target_complex} 수집 시작...")
        
        # 임시 좌표 (실제로는 단지명으로 좌표 조회 필요)
        center_lat = 37.4514469
        center_lon = 127.1504679
        
        def progress_callback(current, total, message):
            print(f"[{current}%] {message}")
        
        # 관심 단지 필터링하여 수집
        properties, complexes_list = collector.collect_properties(
            region_name=target_complex,
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=17,  # 기본 줌 레벨 17로 변경
            rlet_tp_cd="APT:JGC",
            trad_tp_cd="A1",
            grid_size=3,
            progress_callback=progress_callback,
            filter_complex_name=target_complex
        )
        
        print(f"✅ 수집 완료: {len(properties)}개 매물")
        
        # Raw 데이터 저장 (빈 데이터여도 저장)
        properties_dict = [
            {
                "item_id": p.item_id,
                "complex_name": p.complex_name,
                "property_type": p.property_type,
                "trade_type": p.trade_type,
                "price": p.price,
                "price_display": p.price_display,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "collected_at": p.collected_at.isoformat()
            }
            for p in properties
        ]
        
        offers_file = CSVStore.save_raw_offers(target_complex, properties_dict)
        print(f"💾 Raw 데이터 저장: {offers_file}")
        
        # 매물이 없는 경우 처리
        if not properties:
            print(f"⚠️  {target_complex}에 대한 매물을 찾을 수 없습니다.")
            print(f"💾 빈 데이터는 저장되었습니다: {offers_file}")
            # 빈 데이터도 prices 파일에 저장
            price_data = {
                "complex_name": target_complex,
                "date": datetime.now().isoformat(),
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "count": 0
            }
            prices_file = CSVStore.save_raw_prices(target_complex, price_data)
            print(f"💾 시세 데이터 저장: {prices_file}")
            print(f"⚠️  텔레그램 알림을 건너뜁니다 (매물 없음)")
            print(f"\n✅ [{idx}/{len(target_complexes)}] {target_complex} 처리 완료!")
            continue
        
        # 가격 분석
        print("\n📊 가격 분석 중...")
        min_price, max_price = PriceAnalyzer.calculate_price_range(properties_dict)
        representative_price = PriceAnalyzer.calculate_representative_price(properties_dict)
        
        # 과거 데이터 로드
        historical_data = CSVStore.load_historical_prices(target_complex, days_back=365)
        
        # 변동률 계산
        price_changes = PriceAnalyzer.analyze_price_changes(
            properties_dict,
            historical_data
        )
        
        # 호가 분포 분석
        pyeong_buckets = DistributionAnalyzer.analyze_by_pyeong(properties_dict)
        dong_analysis = DistributionAnalyzer.analyze_by_dong(properties_dict)
        top_property = DistributionAnalyzer.find_highest_price_property(properties_dict)
        
        # 시세 데이터 저장
        price_data = {
            "complex_name": target_complex,
            "date": datetime.now().isoformat(),
            "median_price": representative_price,
            "min_price": min_price,
            "max_price": max_price,
            "count": len(properties)
        }
        
        prices_file = CSVStore.save_raw_prices(target_complex, price_data)
        print(f"💾 시세 데이터 저장: {prices_file}")
        
        # 텔레그램 알림 전송
        notifier = None
        try:
            notifier = TelegramNotifier()
        except ValueError as e:
            print(f"⚠️  텔레그램 설정이 없습니다: {e}")
            print("💡 텔레그램 알림을 받으려면 .env 파일에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
        except Exception as e:
            print(f"⚠️  텔레그램 초기화 실패: {e}")
            print("💡 텔레그램 알림을 받으려면 .env 파일에 TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")
        
        if notifier:
            try:
                # 요약 리포트 데이터 구성
                summary_data = {
                    "source": "배치 수집",
                    "trade_type": "매매",
                    "area_basis": "전체",
                    "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "min_price": min_price,
                    "max_price": max_price,
                    "representative_price": representative_price,
                    "total_count": len(properties),
                    "representative_pyeong": "N/A",  # TODO: 실제 평형 정보 필요
                    "representative_m2": "N/A",
                    "rep_min": min_price,
                    "rep_max": max_price,
                    "rep_count": len(properties),
                    "top_price": top_property.get("price_in_100m") if top_property else "N/A",
                    "top_dong": DistributionAnalyzer._extract_dong(top_property.get("complex_name", "")) if top_property else "N/A",
                    "top_floor": "N/A",  # TODO: 층 정보 필요
                    "top_pyeong": "N/A",  # TODO: 평형 정보 필요
                    "top_tags": "",
                    "stat_basis": "중앙값",
                    "week_change": {
                        "delta": price_changes["week"].delta if price_changes["week"] else "N/A",
                        "pct": price_changes["week"].pct if price_changes["week"] else "N/A",
                        "date": price_changes["week"].comparison_date.strftime("%Y-%m-%d") if price_changes["week"] and price_changes["week"].comparison_date else "N/A"
                    },
                    "month_change": {
                        "delta": price_changes["month"].delta if price_changes["month"] else "N/A",
                        "pct": price_changes["month"].pct if price_changes["month"] else "N/A",
                        "date": price_changes["month"].comparison_date.strftime("%Y-%m-%d") if price_changes["month"] and price_changes["month"].comparison_date else "N/A"
                    },
                    "year_change": {
                        "delta": price_changes["year"].delta if price_changes["year"] else "N/A",
                        "pct": price_changes["year"].pct if price_changes["year"] else "N/A",
                        "date": price_changes["year"].comparison_date.strftime("%Y-%m-%d") if price_changes["year"] and price_changes["year"].comparison_date else "N/A"
                    },
                    "pyeong_buckets": pyeong_buckets,
                    "dong_analysis": dong_analysis,
                    "current_complex_name": current_complex,
                    "gap_info": {
                        "target_median": representative_price,
                        "current_median": "N/A",  # TODO: 현재 거주 단지 데이터 필요
                        "delta": "N/A",
                        "pct": "N/A",
                        "target_min": min_price,
                        "target_max": max_price,
                        "current_min": "N/A",
                        "current_max": "N/A"
                    },
                    "naver_link": f"https://m.land.naver.com/search?q={target_complex}",
                    "csv_filename": offers_file
                }
                
                print("\n📱 텔레그램 요약 리포트 전송 중...")
                notifier.send_price_summary(target_complex, summary_data)
                print("✅ 텔레그램 전송 완료")
                
                # 가격 하락 감지 및 알람
                has_drop, trigger_reason, trigger_change = PriceAnalyzer.detect_price_drop(price_changes)
                
                if has_drop:
                    print(f"\n🚨 가격 하락 감지: {trigger_reason}")
                    
                    alert_data = {
                        "representative_pyeong": "N/A",
                        "stat_basis": "중앙값",
                        "week_change": summary_data["week_change"],
                        "month_change": summary_data["month_change"],
                        "year_change": summary_data["year_change"],
                        "trigger": {
                            "reason": f"{trigger_reason} 대비 하락",
                            "base": f"{trigger_reason} 대비 {trigger_change.delta}억 / {trigger_change.pct}%"
                        },
                        "naver_link": summary_data["naver_link"],
                        "csv_filename": offers_file
                    }
                    
                    notifier.send_price_drop_alert(target_complex, alert_data)
                    print("✅ 가격 하락 알람 전송 완료")
            except Exception as e:
                print(f"❌ 텔레그램 전송 실패: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("⚠️  텔레그램 알림을 건너뜁니다 (설정 없음)")
        
        print(f"\n✅ [{idx}/{len(target_complexes)}] {target_complex} 처리 완료!")
    
    print(f"\n{'='*60}")
    print("✅ 모든 관심 단지 배치 수집 완료!")
    print(f"{'='*60}")


if __name__ == "__main__":
    collect_interest_complexes()

