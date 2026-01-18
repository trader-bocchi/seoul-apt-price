"""
텔레그램 알림 전송
"""
import requests
import math
import pandas as pd
from typing import Dict, Optional
from datetime import datetime
from src.config.env_loader import EnvConfig
from src.storage.csv_store import CSVStore


class TelegramNotifier:
    """텔레그램 알림 클래스"""
    
    BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self):
        self.bot_token = EnvConfig.get_telegram_bot_token()
        self.chat_id = EnvConfig.get_telegram_chat_id()
        
        if not self.bot_token or not self.chat_id:
            raise ValueError("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")
    
    def send_message(self, message: str) -> bool:
        """
        텔레그램 메시지 전송
        
        Args:
            message: 전송할 메시지
        
        Returns:
            전송 성공 여부
        """
        url = f"{self.BASE_URL}{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"텔레그램 메시지 전송 실패: {e}")
            return False
    
    def send_price_summary(
        self,
        complex_name: str,
        summary_data: Dict
    ) -> bool:
        """
        가격 요약 리포트 전송
        
        Args:
            complex_name: 단지명
            summary_data: 요약 데이터
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_summary_message(complex_name, summary_data)
        
        success = self.send_message(message)
        
        if success:
            # 백데이터 저장
            CSVStore.save_telegram_log(
                "price_summary",
                {
                    "sent_at": datetime.now().isoformat(),
                    "complex_name": complex_name,
                    "message_type": "summary",
                    "message_title": f"[관심단지 리포트] {complex_name}",
                    "message_body": message,
                    "reference_price": summary_data.get("representative_price"),
                    "comparison_target": "week,month,year"
                }
            )
        
        return success
    
    def send_price_drop_alert(
        self,
        complex_name: str,
        alert_data: Dict
    ) -> bool:
        """
        가격 하락 알람 전송
        
        Args:
            complex_name: 단지명
            alert_data: 알람 데이터
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_drop_alert_message(complex_name, alert_data)
        
        success = self.send_message(message)
        
        if success:
            # 백데이터 저장
            CSVStore.save_telegram_log(
                "price_drop_alert",
                {
                    "sent_at": datetime.now().isoformat(),
                    "complex_name": complex_name,
                    "message_type": "drop_alert",
                    "message_title": f"[가격 변동 알림] {complex_name}",
                    "message_body": message,
                    "reference_price": alert_data.get("current_price"),
                    "comparison_target": alert_data.get("trigger_period", "unknown")
                }
            )
        
        return success
    
    @staticmethod
    def _format_summary_message(complex_name: str, data: Dict) -> str:
        """요약 메시지 포맷팅 (간소화 버전)"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 기본 정보
        msg = f"🏢 {complex_name} 리포트 {now}\n"
        msg += f"━━━━━━━━━━━━━━━━\n\n"
        
        # 핵심 가격 정보
        msg += f"💰 가격 범위: {data.get('min_price', 'N/A')}억 ~ {data.get('max_price', 'N/A')}억\n"
        msg += f"📊 표본: {data.get('total_count', 0)}개\n"
        msg += f"📈 중앙가: {data.get('representative_price', 'N/A')}억\n\n"
        
        # 변동률 (간소화)
        wow = data.get('week_change', {})
        mom = data.get('month_change', {})
        yoy = data.get('year_change', {})
        
        msg += "📉 변동률:\n"
        if wow and wow.get('delta') != 'N/A':
            wow_arrow = "⬇️" if wow.get('delta', 0) < 0 else "⬆️"
            msg += f"  전주: {wow.get('delta', 'N/A')}억 ({wow.get('pct', 'N/A')}%) {wow_arrow}\n"
        if mom and mom.get('delta') != 'N/A':
            mom_arrow = "⬇️" if mom.get('delta', 0) < 0 else "⬆️"
            msg += f"  전월: {mom.get('delta', 'N/A')}억 ({mom.get('pct', 'N/A')}%) {mom_arrow}\n"
        if yoy and yoy.get('delta') != 'N/A':
            yoy_arrow = "⬇️" if yoy.get('delta', 0) < 0 else "⬆️"
            msg += f"  전년: {yoy.get('delta', 'N/A')}억 ({yoy.get('pct', 'N/A')}%) {yoy_arrow}\n"
        msg += "\n"
        
        # 최고가 정보 (간소화)
        top_price = data.get('top_price', 'N/A')
        top_dong = data.get('top_dong', 'N/A')
        if top_price != 'N/A' and top_dong != 'N/A':
            msg += f"🏆 최고가: {top_price}억 ({top_dong}동)\n\n"
        
        # 링크
        msg += f"🔗 {data.get('naver_link', 'N/A')}\n"
        
        return msg
    
    @staticmethod
    def _format_drop_alert_message(complex_name: str, data: Dict) -> str:
        """가격 하락 알람 메시지 포맷팅"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"🚨 [가격 변동 알림] {now}\n"
        msg += f"🏢 {complex_name} / 대표 {data.get('representative_pyeong', 'N/A')}평 기준\n\n"
        
        msg += f"📉 변동률 요약({data.get('stat_basis', '중앙값')})\n"
        
        wow = data.get('week_change', {})
        mom = data.get('month_change', {})
        yoy = data.get('year_change', {})
        
        wow_arrow = "⬇️" if wow.get('delta', 0) < 0 else "⬆️"
        mom_arrow = "⬇️" if mom.get('delta', 0) < 0 else "⬆️"
        yoy_arrow = "⬇️" if yoy.get('delta', 0) < 0 else "⬆️"
        
        msg += f"• 전주 대비: {wow.get('delta', 'N/A')}억 ({wow.get('pct', 'N/A')}%)  {wow_arrow}\n"
        msg += f"• 전월 대비: {mom.get('delta', 'N/A')}억 ({mom.get('pct', 'N/A')}%)  {mom_arrow}\n"
        msg += f"• 전년 대비: {yoy.get('delta', 'N/A')}억 ({yoy.get('pct', 'N/A')}%)  {yoy_arrow}\n\n"
        
        trigger = data.get('trigger', {})
        msg += f"🔎 트리거: {trigger.get('reason', 'N/A')}\n"
        msg += f"- 기준: {trigger.get('base', 'N/A')}\n"
        msg += f"- 비교 기준일: 주={wow.get('date', 'N/A')}, 월={mom.get('date', 'N/A')}, 년={yoy.get('date', 'N/A')}\n\n"
        
        msg += f"🔗 {data.get('naver_link', 'N/A')}\n"
        msg += f"🗂 백데이터: {data.get('csv_filename', 'N/A')}\n"
        
        return msg
    
    def send_complex_analysis(
        self,
        complex_name: str,
        analysis_data: Dict
    ) -> bool:
        """
        단지 분석 리포트 전송
        
        Args:
            complex_name: 단지명
            analysis_data: 분석 데이터
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_complex_analysis_message(complex_name, analysis_data)
        
        success = self.send_message(message)
        
        if success:
            CSVStore.save_telegram_log(
                "complex_analysis",
                {
                    "sent_at": datetime.now().isoformat(),
                    "complex_name": complex_name,
                    "message_type": "complex_analysis",
                    "message_title": f"[단지 분석] {complex_name}",
                    "message_body": message
                }
            )
        
        return success
    
    @staticmethod
    def _format_complex_analysis_message(complex_name: str, data: Dict) -> str:
        """단지 분석 메시지 포맷팅 (면적대별 가격 분포 포함, 소수점 첫번째 자리에서 내림)"""
        
        total_count = data.get("total_count", 0)
        if total_count == 0:
            return f"🏢 {complex_name}: 데이터 없음\n"
        
        msg = f"🏢 <b>{complex_name}</b>\n"
        msg += f"📊 매물: {total_count}개\n"
        
        # 면적대별 가격 분포 (소수점 첫번째 자리에서 내림)
        price_dist_by_area = data.get("price_distribution_by_area", {})
        if "error" not in price_dist_by_area and price_dist_by_area.get("by_area"):
            by_area = price_dist_by_area.get("by_area", {})
            sorted_areas = sorted(by_area.items(), key=lambda x: x[0])
            
            for area, dist_data in sorted_areas:
                count = dist_data.get("count", 0)
                median = dist_data.get("median", 0)  # 호가 소수점 내림처리 취소
                min_price = dist_data.get("min", 0)
                max_price = dist_data.get("max", 0)
                msg += f"  📐 {area}m²: {min_price:.1f}억 ~ {max_price:.1f}억 (중앙: {median:.1f}억, {count}개)\n"
        else:
            # 폴백: 전체 가격 정보
            overall = price_dist_by_area.get("overall", {})
            if overall:
                min_price = overall.get('min', 0)  # 호가 소수점 내림처리 취소
                max_price = overall.get('max', 0)
                median = overall.get('median', 0)
                msg += f"💰 가격: {min_price:.1f}억 ~ {max_price:.1f}억 (중앙: {median:.1f}억)\n"
        
        return msg
    
    @staticmethod
    def _format_all_complexes_analysis_message(all_analyses: Dict[str, Dict]) -> str:
        """모든 단지 분석을 하나의 메시지로 통합"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"📊 <b>단지 분석 리포트</b>\n"
        msg += f"📅 {now}\n"
        msg += "━━━━━━━━━━━━━━━━\n\n"
        
        for complex_name, data in all_analyses.items():
            complex_msg = TelegramNotifier._format_complex_analysis_message(complex_name, data)
            msg += complex_msg + "\n"
        
        return msg
    
    def send_comparison_analysis(
        self,
        my_home_data: Dict,
        target_home_data: Dict
    ) -> bool:
        """
        두 단지 간 비교 분석 전송
        
        Args:
            my_home_data: 내 집 분석 데이터
            target_home_data: 관심 단지 분석 데이터
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_comparison_message(my_home_data, target_home_data)
        
        success = self.send_message(message)
        
        if success:
            CSVStore.save_telegram_log(
                "comparison_analysis",
                {
                    "sent_at": datetime.now().isoformat(),
                    "message_type": "comparison",
                    "message_title": "[호가 차이 분석]",
                    "message_body": message
                }
            )
        
        return success
    
    @staticmethod
    def _format_comparison_message(my_data: Dict, target_data: Dict, my_home_area: Optional[float] = None) -> str:
        """단일 비교 분석 메시지 포맷팅 (내 단지 특정 면적 기준 비교)"""
        
        my_name = my_data.get("complex_name", "내 집")
        target_name = target_data.get("complex_name", "관심 단지")
        
        msg = f"🏢 <b>{my_name}</b> vs <b>{target_name}</b>\n"
        
        # 내 단지 면적 (환경 변수 또는 기본값)
        if my_home_area is None:
            my_home_area = EnvConfig.get_my_home_area()
        
        # 면적대별 가격 분포 비교
        my_price_dist = my_data.get("price_distribution_by_area", {})
        target_price_dist = target_data.get("price_distribution_by_area", {})
        
        if "error" in my_price_dist or "error" in target_price_dist:
            return f"{my_name} vs {target_name}: 비교 불가 (데이터 없음)\n"
        
        my_by_area = my_price_dist.get("by_area", {})
        target_by_area = target_price_dist.get("by_area", {})
        
        # 내 단지의 특정 면적 기준으로 비교 (MY_HOME_AREA)
        if my_home_area:
            import math
            my_area_key = math.floor(my_home_area)
            
            # 내 단지에서 해당 면적대 찾기
            my_dist = None
            my_median = 0
            
            if my_area_key in my_by_area:
                my_dist = my_by_area[my_area_key]
                my_median = my_dist.get("median", 0)
            elif my_by_area:
                # 가장 가까운 면적대 찾기
                closest_my_area = min(my_by_area.keys(), key=lambda x: abs(x - my_area_key))
                my_dist = my_by_area[closest_my_area]
                my_median = my_dist.get("median", 0)
                my_area_key = closest_my_area  # 실제 찾은 면적대로 업데이트
            
            if my_median > 0:
                # 내 단지 MY_HOME_AREA 호가 표시
                msg += f"📐 내 단지 {my_area_key}m²: {my_median:.1f}억\n\n"
                
                # 타 단지의 모든 평형대와 MY_HOME_AREA 호가 비교
                if target_by_area:
                    comparisons = []
                    for target_area, target_dist in target_by_area.items():
                        target_median = target_dist.get("median", 0)
                        if target_median > 0:
                            # MY_HOME_AREA 호가와의 차이 계산
                            price_diff = target_median - my_median
                            price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
                            direction = "⬆️" if price_diff > 0 else "⬇️" if price_diff < 0 else "➡️"
                            comparisons.append({
                                "area": target_area,
                                "median": target_median,
                                "diff": price_diff,
                                "diff_pct": price_diff_pct,
                                "direction": direction
                            })
                    
                    if comparisons:
                        # 면적 순으로 정렬
                        comparisons.sort(key=lambda x: x['area'])
                        msg += "📊 타 단지 평형대별 호가 차이:\n"
                        for item in comparisons:
                            msg += f"  {item['area']}m²: {item['median']:.1f}억 (차이: {item['diff']:+.1f}억, {item['diff_pct']:+.1f}% {item['direction']})\n"
                    else:
                        msg += "⚠️ 타 단지 평형대 데이터 없음\n"
                else:
                    msg += "⚠️ 타 단지 평형대 데이터 없음\n"
            else:
                msg += f"⚠️ 내 단지 {my_area_key}m² 호가 데이터 없음\n"
            
            return msg
        
        # 내 단지 면적이 설정되지 않은 경우 기존 로직 사용
        if not my_by_area or not target_by_area:
            # 면적대가 없으면 전체 통계 비교
            my_overall = my_price_dist.get("overall", {})
            target_overall = target_price_dist.get("overall", {})
            
            my_median = my_overall.get("median", 0)
            target_median = target_overall.get("median", 0)
            
            if my_median == 0 or target_median == 0:
                return f"{my_name} vs {target_name}: 비교 불가\n"
            
            price_diff = target_median - my_median
            price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
            direction = "높음" if price_diff > 0 else "낮음" if price_diff < 0 else "동일"
            
            direction_emoji = "⬆️" if price_diff > 0 else "⬇️" if price_diff < 0 else "➡️"
            
            msg += f"💰 전체 중앙가: {my_median:.1f}억 → {target_median:.1f}억 (차이: {price_diff:+.1f}억, {price_diff_pct:+.1f}% {direction_emoji})\n"
        else:
            # 내 단지 면적대 기준으로 목표 단지 면적대 분류
            my_areas = sorted(my_by_area.keys())
            my_min_area = min(my_areas)
            my_max_area = max(my_areas)
            
            # 유사한 평형: 내 단지 면적대와 차이가 ±5m² 이내
            similar_areas = []
            wider_areas = []  # 넓은 평형: 내 단지 최대 면적보다 큰 경우
            narrower_areas = []  # 낮은 평형: 내 단지 최소 면적보다 작은 경우
            
            for target_area in sorted(target_by_area.keys()):
                target_dist = target_by_area[target_area]
                target_median = target_dist.get("median", 0)
                
                if target_median == 0:
                    continue
                
                # 내 단지에 동일한 면적대가 있는지 확인
                if target_area in my_by_area:
                    my_dist = my_by_area[target_area]
                    my_median = my_dist.get("median", 0)
                    if my_median > 0:
                        price_diff = target_median - my_median
                        price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
                        direction = "높음" if price_diff > 0 else "낮음" if price_diff < 0 else "동일"
                        similar_areas.append({
                            "area": target_area,
                            "my_median": my_median,
                            "target_median": target_median,
                            "diff": price_diff,
                            "diff_pct": price_diff_pct,
                            "direction": direction
                        })
                else:
                    # 내 단지에 없는 면적대인 경우, 가장 가까운 내 단지 면적대 찾기
                    closest_my_area = min(my_areas, key=lambda x: abs(x - target_area))
                    diff_from_closest = abs(target_area - closest_my_area)
                    
                    if diff_from_closest <= 5.0:
                        # 유사한 평형 (±5m² 이내)
                        my_dist = my_by_area[closest_my_area]
                        my_median = my_dist.get("median", 0)
                        if my_median > 0:
                            price_diff = target_median - my_median
                            price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
                            direction = "높음" if price_diff > 0 else "낮음" if price_diff < 0 else "동일"
                            similar_areas.append({
                                "area": target_area,
                                "my_area": closest_my_area,
                                "my_median": my_median,
                                "target_median": target_median,
                                "diff": price_diff,
                                "diff_pct": price_diff_pct,
                                "direction": direction
                            })
                    elif target_area > my_max_area:
                        # 넓은 평형
                        wider_areas.append({
                            "area": target_area,
                            "median": target_median
                        })
                    elif target_area < my_min_area:
                        # 낮은 평형
                        narrower_areas.append({
                            "area": target_area,
                            "median": target_median
                        })
            
            # 유사한 평형 비교 (호가 소수점 내림처리 취소)
            if similar_areas:
                msg += "🔹 유사한 평형:\n"
                for item in similar_areas[:5]:  # 최대 5개
                    if "my_area" in item:
                        # 내 단지에 없는 면적대지만 유사한 경우
                        direction_emoji = "⬆️" if item['diff'] > 0 else "⬇️" if item['diff'] < 0 else "➡️"
                        msg += f"  {item['area']}m²: {item['my_area']}m²({item['my_median']:.1f}억) → {item['target_median']:.1f}억 ({item['diff']:+.1f}억, {item['diff_pct']:+.1f}% {direction_emoji})\n"
                    else:
                        # 동일한 면적대
                        direction_emoji = "⬆️" if item['diff'] > 0 else "⬇️" if item['diff'] < 0 else "➡️"
                        msg += f"  {item['area']}m²: {item['my_median']:.1f}억 → {item['target_median']:.1f}억 ({item['diff']:+.1f}억, {item['diff_pct']:+.1f}% {direction_emoji})\n"
            
            # 넓은 평형 (호가 소수점 내림처리 취소)
            if wider_areas:
                msg += "🔹 넓은 평형:\n"
                for item in wider_areas[:3]:  # 최대 3개
                    msg += f"  {item['area']}m²: {item['median']:.1f}억\n"
            
            # 낮은 평형 (호가 소수점 내림처리 취소)
            if narrower_areas:
                msg += "🔹 낮은 평형:\n"
                for item in narrower_areas[:3]:  # 최대 3개
                    msg += f"  {item['area']}m²: {item['median']:.1f}억\n"
        
        return msg
    
    @staticmethod
    def _format_all_comparisons_message(my_data: Dict, all_target_data: Dict[str, Dict]) -> str:
        """모든 비교 분석을 하나의 메시지로 통합"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"⚖️ <b>가격 비교 분석</b>\n"
        msg += f"📅 {now}\n"
        msg += "━━━━━━━━━━━━━━━━\n\n"
        
        from src.config.env_loader import EnvConfig
        my_home_area = EnvConfig.get_my_home_area()
        
        for target_name, target_data in all_target_data.items():
            comparison_msg = TelegramNotifier._format_comparison_message(my_data, target_data, my_home_area)
            msg += comparison_msg + "\n"
        
        return msg
    
    def send_all_complexes_analysis(self, all_analyses: Dict[str, Dict]) -> bool:
        """
        모든 단지 분석을 하나의 메시지로 전송
        
        Args:
            all_analyses: {단지명: 분석데이터} 딕셔너리
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_all_complexes_analysis_message(all_analyses)
        return self.send_message(message)
    
    def send_all_comparisons(self, my_data: Dict, all_target_data: Dict[str, Dict]) -> bool:
        """
        모든 비교 분석을 하나의 메시지로 전송
        
        Args:
            my_data: 내 집 분석 데이터
            all_target_data: {목표단지명: 분석데이터} 딕셔너리
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_all_comparisons_message(my_data, all_target_data)
        return self.send_message(message)
    
    def send_my_home_detailed_analysis(self, complex_name: str, analysis_data: Dict) -> bool:
        """
        내 단지 상세분석 리포트 전송 (층/동/향별)
        
        Args:
            complex_name: 단지명
            analysis_data: 분석 데이터
        
        Returns:
            전송 성공 여부
        """
        message = TelegramNotifier._format_my_home_detailed_message(complex_name, analysis_data)
        return self.send_message(message)
    
    @staticmethod
    def _format_my_home_detailed_message(complex_name: str, data: Dict) -> str:
        """내 단지 상세분석 메시지 포맷팅 (평형대별 층/동/향별 호가 차이)"""
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"📋 <b>내 단지 상세분석</b>\n"
        msg += f"🏢 {complex_name}\n"
        msg += f"📅 {now}\n"
        msg += "━━━━━━━━━━━━━━━━\n\n"
        
        detailed = data.get("detailed_analysis", {})
        if "error" in detailed:
            msg += "⚠️ 상세 분석 데이터 없음\n"
            return msg
        
        # 평형대별로 분석 결과 표시
        sorted_areas = sorted([k for k in detailed.keys() if isinstance(k, (int, float))])
        
        if not sorted_areas:
            msg += "⚠️ 평형대별 데이터 없음\n"
            return msg
        
        for area_key in sorted_areas[:5]:  # 최대 5개 평형대만 표시
            area_data = detailed[area_key]
            msg += f"📐 <b>{area_key}m²</b>\n"
            
            # 층별 분석
            if "floor_analysis" in area_data:
                floor_analysis = area_data["floor_analysis"]
                msg += "  🏗 층별: "
                floor_items = []
                for floor_cat, stats in floor_analysis.items():
                    avg_price_val = stats.get('avg_price', 0)
                    if pd.isna(avg_price_val) or avg_price_val == 0:
                        continue
                    avg_price = float(avg_price_val)  # 호가 소수점 내림처리 취소
                    count = stats.get('count', 0)
                    floor_items.append(f"{floor_cat} {avg_price:.1f}억({count}개)")
                if floor_items:
                    msg += ", ".join(floor_items) + "\n"
            
            # 동별 분석
            if "dong_analysis" in area_data:
                dong_analysis = area_data["dong_analysis"]
                msg += f"  🏘 동별: "
                dong_items = []
                if dong_analysis.get('highest_dong') != "N/A":
                    dong_items.append(f"최고 {dong_analysis['highest_dong']}")
                if dong_analysis.get('lowest_dong') != "N/A":
                    dong_items.append(f"최저 {dong_analysis['lowest_dong']}")
                price_gap_val = dong_analysis.get('price_gap', 0)
                if not pd.isna(price_gap_val) and price_gap_val > 0:
                    price_gap = float(price_gap_val)  # 호가 소수점 내림처리 취소
                    dong_items.append(f"차이 {price_gap:.1f}억")
                if dong_items:
                    msg += ", ".join(dong_items) + "\n"
            
            # 향별 분석
            if "direction_analysis" in area_data:
                direction_analysis = area_data["direction_analysis"]
                msg += f"  🧭 향별: "
                direction_items = []
                if direction_analysis.get('highest_direction') != "N/A":
                    direction_items.append(f"최고 {direction_analysis['highest_direction']}")
                if direction_analysis.get('lowest_direction') != "N/A":
                    direction_items.append(f"최저 {direction_analysis['lowest_direction']}")
                price_gap_val = direction_analysis.get('price_gap', 0)
                if not pd.isna(price_gap_val) and price_gap_val > 0:
                    price_gap = float(price_gap_val)  # 호가 소수점 내림처리 취소
                    direction_items.append(f"차이 {price_gap:.1f}억")
                if direction_items:
                    msg += ", ".join(direction_items) + "\n"
            
            # 매물 특징 분석
            if "feature_analysis" in area_data:
                feature_analysis = area_data["feature_analysis"]
                msg += f"  📝 특징: "
                feature_items = []
                
                # 상위 키워드 표시
                top_keywords = feature_analysis.get('top_keywords', {})
                if top_keywords:
                    keyword_list = [f"{word}({count})" for word, count in list(top_keywords.items())[:5]]
                    feature_items.append(", ".join(keyword_list))
                
                # 특징이 있는 매물 수
                total_with_features = feature_analysis.get('total_with_features', 0)
                if total_with_features > 0:
                    feature_items.append(f"특징매물 {total_with_features}개")
                
                if feature_items:
                    msg += " | ".join(feature_items) + "\n"
            
            msg += "\n"
        
        return msg
    
    @staticmethod
    def _generate_insights(my_data: Dict, target_data: Dict) -> List[str]:
        """동적 인사이트 생성 (최대 3줄)"""
        insights = []
        
        # 가격 차이 인사이트
        my_price_dist = my_data.get("price_distribution", {})
        target_price_dist = target_data.get("price_distribution", {})
        
        my_median = my_price_dist.get("median", 0)
        target_median = target_price_dist.get("median", 0)
        
        if my_median > 0 and target_median > 0:
            diff_pct = ((target_median - my_median) / my_median) * 100
            if abs(diff_pct) > 5:
                if diff_pct > 0:
                    insights.append(f"관심 단지가 내 집보다 약 {diff_pct:.1f}% 비쌉니다.")
                else:
                    insights.append(f"관심 단지가 내 집보다 약 {abs(diff_pct):.1f}% 저렴합니다.")
        
        # 동별 가격 차이 인사이트
        target_dong_diff = target_data.get("dong_price_diff", {})
        if "error" not in target_dong_diff and target_dong_diff.get("price_gap", 0) > 2:
            highest = target_dong_diff.get("highest_avg_dong", "N/A")
            lowest = target_dong_diff.get("lowest_avg_dong", "N/A")
            gap = target_dong_diff.get("price_gap", 0)
            insights.append(f"관심 단지 내 동별 가격 차이가 {gap:.1f}억으로 큽니다 ({highest}동 vs {lowest}동).")
        
        # 매물 개수 인사이트
        my_count = my_data.get("total_count", 0)
        target_count = target_data.get("total_count", 0)
        if target_count > my_count * 1.5:
            insights.append(f"관심 단지의 매물이 내 집보다 {target_count - my_count}개 더 많아 선택의 폭이 넓습니다.")
        
        return insights[:3]  # 최대 3개

