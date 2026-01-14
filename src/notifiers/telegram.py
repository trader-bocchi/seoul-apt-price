"""
텔레그램 알림 전송
"""
import requests
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
        """단지 분석 메시지 포맷팅 (면적대별 가격 분포 포함)"""
        total_count = data.get("total_count", 0)
        if total_count == 0:
            return f"🏢 {complex_name}: 데이터 없음\n"
        
        msg = f"🏢 <b>{complex_name}</b>\n"
        msg += f"매물: {total_count}개\n"
        
        # 면적대별 가격 분포
        price_dist_by_area = data.get("price_distribution_by_area", {})
        if "error" not in price_dist_by_area and price_dist_by_area.get("by_area"):
            by_area = price_dist_by_area.get("by_area", {})
            sorted_areas = sorted(by_area.items(), key=lambda x: x[0])
            
            for area, dist_data in sorted_areas:
                count = dist_data.get("count", 0)
                median = dist_data.get("median", 0)
                min_price = dist_data.get("min", 0)
                max_price = dist_data.get("max", 0)
                msg += f"{area}m²: {min_price:.1f}억 ~ {max_price:.1f}억 (중앙: {median:.1f}억, {count}개)\n"
        else:
            # 폴백: 전체 가격 정보
            overall = price_dist_by_area.get("overall", {})
            if overall:
                msg += f"가격: {overall.get('min', 0):.1f}억 ~ {overall.get('max', 0):.1f}억 (중앙: {overall.get('median', 0):.1f}억)\n"
        
        return msg
    
    @staticmethod
    def _format_all_complexes_analysis_message(all_analyses: Dict[str, Dict]) -> str:
        """모든 단지 분석을 하나의 메시지로 통합"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"📊 <b>단지 분석 리포트</b>\n"
        msg += f"{now}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
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
    def _format_comparison_message(my_data: Dict, target_data: Dict) -> str:
        """단일 비교 분석 메시지 포맷팅 (면적대별 비교)"""
        my_name = my_data.get("complex_name", "내 집")
        target_name = target_data.get("complex_name", "관심 단지")
        
        msg = f"<b>{my_name} vs {target_name}</b>\n"
        
        # 면적대별 가격 분포 비교
        my_price_dist = my_data.get("price_distribution_by_area", {})
        target_price_dist = target_data.get("price_distribution_by_area", {})
        
        if "error" in my_price_dist or "error" in target_price_dist:
            return f"{my_name} vs {target_name}: 비교 불가 (데이터 없음)\n"
        
        my_by_area = my_price_dist.get("by_area", {})
        target_by_area = target_price_dist.get("by_area", {})
        
        # 공통 면적대 찾기
        common_areas = set(my_by_area.keys()) & set(target_by_area.keys())
        
        if not common_areas:
            # 공통 면적대가 없으면 전체 통계 비교
            my_overall = my_price_dist.get("overall", {})
            target_overall = target_price_dist.get("overall", {})
            
            my_median = my_overall.get("median", 0)
            target_median = target_overall.get("median", 0)
            
            if my_median == 0 or target_median == 0:
                return f"{my_name} vs {target_name}: 비교 불가\n"
            
            price_diff = target_median - my_median
            price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
            direction = "높음" if price_diff > 0 else "낮음" if price_diff < 0 else "동일"
            
            msg += f"전체 중앙가: {my_median:.1f}억 → {target_median:.1f}억 (차이: {price_diff:+.1f}억, {price_diff_pct:+.1f}%, {direction})\n"
        else:
            # 공통 면적대별로 비교
            for area in sorted(common_areas):
                my_dist = my_by_area[area]
                target_dist = target_by_area[area]
                
                my_median = my_dist.get("median", 0)
                target_median = target_dist.get("median", 0)
                
                if my_median == 0 or target_median == 0:
                    continue
                
                price_diff = target_median - my_median
                price_diff_pct = (price_diff / my_median) * 100 if my_median > 0 else 0
                direction = "높음" if price_diff > 0 else "낮음" if price_diff < 0 else "동일"
                
                msg += f"{area}m²: {my_median:.1f}억 → {target_median:.1f}억 (차이: {price_diff:+.1f}억, {price_diff_pct:+.1f}%, {direction})\n"
        
        return msg
    
    @staticmethod
    def _format_all_comparisons_message(my_data: Dict, all_target_data: Dict[str, Dict]) -> str:
        """모든 비교 분석을 하나의 메시지로 통합"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        msg = f"⚖️ <b>가격 비교 분석</b>\n"
        msg += f"{now}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for target_name, target_data in all_target_data.items():
            comparison_msg = TelegramNotifier._format_comparison_message(my_data, target_data)
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

