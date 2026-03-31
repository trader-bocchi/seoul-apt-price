"""
텔레그램 알림 전송
"""
import requests
import math
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
from src.config.env_loader import EnvConfig
from src.storage.csv_store import CSVStore

_WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]
_MAX_MSG_LEN = 4000  # Telegram 한도 4096, 버퍼 확보


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self):
        self.bot_token = EnvConfig.get_telegram_bot_token()
        self.chat_id = EnvConfig.get_telegram_chat_id()

        if not self.bot_token or not self.chat_id:
            raise ValueError("텔레그램 봇 토큰 또는 채팅 ID가 설정되지 않았습니다.")

    def send_message(self, message: str) -> bool:
        url = f"{self.BASE_URL}{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"텔레그램 메시지 전송 실패: {e}")
            return False

    # ──────────────────────────────────────────
    # Public send methods
    # ──────────────────────────────────────────

    def send_all_complexes_analysis(self, all_analyses: Dict[str, Dict]) -> bool:
        """모든 단지 분석을 전송 (4000자 초과 시 단지별로 분할 전송)"""
        my_home = EnvConfig.get_my_home_complex_name() or ""
        header, blocks = _build_complexes_blocks(all_analyses, my_home)

        # 헤더 + 전체 블록이 한 메시지에 들어오면 단건 전송
        full = header + "".join(blocks)
        if len(full) <= _MAX_MSG_LEN:
            return self.send_message(full)

        # 초과 시: 헤더 포함 첫 메시지부터 순서대로 쌓아 전송
        success = True
        current = header
        for block in blocks:
            if len(current) + len(block) > _MAX_MSG_LEN:
                if not self.send_message(current):
                    success = False
                current = block
            else:
                current += block
        if current:
            if not self.send_message(current):
                success = False
        return success

    def send_my_home_detailed_analysis(self, complex_name: str, analysis_data: Dict) -> bool:
        message = _format_my_home_detailed(complex_name, analysis_data)
        return self.send_message(message)

    def send_price_summary(self, complex_name: str, summary_data: Dict) -> bool:
        message = _format_summary_message(complex_name, summary_data)
        success = self.send_message(message)
        if success:
            CSVStore.save_telegram_log("price_summary", {
                "sent_at": datetime.now().isoformat(),
                "complex_name": complex_name,
                "message_type": "summary",
                "message_title": f"[관심단지 리포트] {complex_name}",
                "message_body": message,
                "reference_price": summary_data.get("representative_price"),
                "comparison_target": "week,month,year"
            })
        return success

    def send_price_drop_alert(self, complex_name: str, alert_data: Dict) -> bool:
        message = _format_drop_alert_message(complex_name, alert_data)
        success = self.send_message(message)
        if success:
            CSVStore.save_telegram_log("price_drop_alert", {
                "sent_at": datetime.now().isoformat(),
                "complex_name": complex_name,
                "message_type": "drop_alert",
                "message_title": f"[가격 변동 알림] {complex_name}",
                "message_body": message,
                "reference_price": alert_data.get("current_price"),
                "comparison_target": alert_data.get("trigger_period", "unknown")
            })
        return success

    def send_complex_analysis(self, complex_name: str, analysis_data: Dict) -> bool:
        message = _format_complex_block(complex_name, analysis_data, is_my_home=False)
        success = self.send_message(message)
        if success:
            CSVStore.save_telegram_log("complex_analysis", {
                "sent_at": datetime.now().isoformat(),
                "complex_name": complex_name,
                "message_type": "complex_analysis",
                "message_title": f"[단지 분석] {complex_name}",
                "message_body": message
            })
        return success

    def send_comparison_analysis(self, my_home_data: Dict, target_home_data: Dict) -> bool:
        message = _format_comparison_message(my_home_data, target_home_data)
        success = self.send_message(message)
        if success:
            CSVStore.save_telegram_log("comparison_analysis", {
                "sent_at": datetime.now().isoformat(),
                "message_type": "comparison",
                "message_title": "[호가 차이 분석]",
                "message_body": message
            })
        return success

    def send_all_comparisons(self, my_data: Dict, all_target_data: Dict[str, Dict]) -> bool:
        now = datetime.now()
        header = (
            f"⚖️ <b>가격 비교 분석</b>\n"
            f"<i>{now.strftime(f'%Y-%m-%d ({_WEEKDAY_KR[now.weekday()]}) %H:%M')}</i>\n"
            f"{'─' * 24}\n\n"
        )
        my_home_area = EnvConfig.get_my_home_area()
        blocks = [
            _format_comparison_message(my_data, td, my_home_area) + "\n"
            for td in all_target_data.values()
        ]
        full = header + "".join(blocks)
        if len(full) <= _MAX_MSG_LEN:
            return self.send_message(full)
        success = True
        if not self.send_message(header + blocks[0]):
            success = False
        for block in blocks[1:]:
            if not self.send_message(block):
                success = False
        return success


# ──────────────────────────────────────────
# Formatting helpers (module-level, not static methods)
# ──────────────────────────────────────────

def _now_str() -> str:
    now = datetime.now()
    return now.strftime(f"%Y-%m-%d ({_WEEKDAY_KR[now.weekday()]}) %H:%M")


def _price_table_lines(by_area: Dict) -> List[str]:
    """면적별 가격 분포 → 정렬된 텍스트 줄 리스트"""
    lines = []
    for area in sorted(by_area.keys()):
        d = by_area[area]
        lo  = d.get("min", 0)
        hi  = d.get("max", 0)
        med = d.get("median", 0)
        cnt = d.get("count", 0)
        # 고정폭 컬럼으로 정렬
        area_col  = f"{area:>3}㎡"
        range_col = f"{lo:.1f}~{hi:.1f}억"
        med_col   = f"중앙 {med:.1f}억"
        cnt_col   = f"{cnt}건"
        lines.append(f"{area_col}  {range_col:<12}  {med_col}  {cnt_col}")
    return lines


def _build_complexes_blocks(
    all_analyses: Dict[str, Dict],
    my_home: str,
) -> tuple[str, List[str]]:
    """헤더 문자열 + [단지별 블록 문자열] 반환"""
    header = (
        f"📊 <b>호가 리포트</b>\n"
        f"<i>{_now_str()}</i>\n"
        f"{'─' * 24}\n\n"
    )
    blocks: List[str] = []
    for name, data in all_analyses.items():
        blocks.append(_format_complex_block(name, data, is_my_home=(name == my_home)))
    return header, blocks


def _format_complex_block(complex_name: str, data: Dict, is_my_home: bool) -> str:
    """단지 하나의 포맷 블록"""
    total = data.get("total_count", 0)
    if total == 0:
        icon = "🏠" if is_my_home else "🎯"
        return f"{icon} <b>{complex_name}</b>  데이터 없음\n\n"

    icon = "🏠" if is_my_home else "🎯"
    block = f"{icon} <b>{complex_name}</b>  <i>{total}건</i>\n"

    price_dist = data.get("price_distribution_by_area", {})
    by_area = price_dist.get("by_area", {})

    if by_area:
        lines = _price_table_lines(by_area)
        block += "<pre>" + "\n".join(lines) + "</pre>\n"
    else:
        overall = price_dist.get("overall", {})
        if overall:
            lo  = overall.get("min", 0)
            hi  = overall.get("max", 0)
            med = overall.get("median", 0)
            block += f"<pre>{lo:.1f}~{hi:.1f}억  중앙 {med:.1f}억</pre>\n"

    block += "\n"
    return block


def _format_my_home_detailed(complex_name: str, data: Dict) -> str:
    """내 단지 층/향/동 상세분석 메시지"""
    msg = (
        f"🔍 <b>내 단지 상세분석</b>\n"
        f"🏠 <b>{complex_name}</b>\n"
        f"<i>{_now_str()}</i>\n"
        f"{'─' * 24}\n\n"
    )

    detailed = data.get("detailed_analysis", {})
    price_dist = data.get("price_distribution_by_area", {})
    by_area = price_dist.get("by_area", {})

    if "error" in detailed:
        return msg + "⚠️ 상세 데이터 없음\n"

    sorted_areas = sorted(k for k in detailed if isinstance(k, (int, float)))
    if not sorted_areas:
        return msg + "⚠️ 평형 데이터 없음\n"

    for area_key in sorted_areas[:5]:
        area_data = detailed[area_key]
        cnt = by_area.get(area_key, {}).get("count", 0)
        cnt_str = f"  <i>{cnt}건</i>" if cnt else ""

        msg += f"<b>▪ {area_key}㎡</b>{cnt_str}\n"

        # 층별
        floor_analysis = area_data.get("floor_analysis", {})
        floor_order = ["저층(1-5층)", "중층(6-10층)", "고층(11-15층)", "초고층(16층+)"]
        floor_rows = []
        floor_prices = []
        for cat in floor_order:
            s = floor_analysis.get(cat)
            if not s:
                continue
            avg = s.get("avg_price", 0)
            if not avg or (isinstance(avg, float) and pd.isna(avg)):
                continue
            floor_rows.append(f"  {cat:<13}  {avg:.1f}억  {s.get('count', 0)}건")
            floor_prices.append(avg)
        if len(floor_rows) > 1:
            gap = max(floor_prices) - min(floor_prices)
            floor_rows.append(f"  {'↕ 층간 차이':<13}  {gap:.1f}억")
            msg += "  <b>층별 평균</b>\n<pre>" + "\n".join(floor_rows) + "</pre>\n"
        elif len(floor_rows) == 1:
            msg += "  <b>층별</b>\n<pre>" + floor_rows[0] + "</pre>\n"

        # 향별
        dir_analysis = area_data.get("direction_analysis", {})
        dir_details = dir_analysis.get("details", {})
        if dir_details and dir_analysis.get("total_directions", 0) > 1:
            dir_rows = []
            for d, s in sorted(dir_details.items(), key=lambda x: x[1].get("avg_price", 0), reverse=True):
                avg = s.get("avg_price", 0)
                if not avg or (isinstance(avg, float) and pd.isna(avg)):
                    continue
                dir_rows.append(f"  {d:<4}  {avg:.1f}억  {s.get('count', 0)}건")
            gap = dir_analysis.get("price_gap", 0)
            if gap and not (isinstance(gap, float) and pd.isna(gap)) and gap > 0:
                hi_d = dir_analysis.get("highest_direction", "")
                lo_d = dir_analysis.get("lowest_direction", "")
                dir_rows.append(f"  ↕ 향간 차이  {gap:.1f}억  ({hi_d} › {lo_d})")
            if dir_rows:
                msg += "  <b>향별 평균</b>\n<pre>" + "\n".join(dir_rows) + "</pre>\n"

        # 동별 (summary만 — 많아지면 노이즈)
        dong_analysis = area_data.get("dong_analysis", {})
        total_dongs = dong_analysis.get("total_dongs", 0)
        if total_dongs > 1:
            hi_dong = dong_analysis.get("highest_dong", "")
            lo_dong = dong_analysis.get("lowest_dong", "")
            gap = dong_analysis.get("price_gap", 0)
            if hi_dong and lo_dong and gap and not (isinstance(gap, float) and pd.isna(gap)):
                msg += f"  <b>동별</b>  최고 {hi_dong}  최저 {lo_dong}  차이 {gap:.1f}억\n"

        msg += "\n"

    return msg


# ──────────────────────────────────────────
# Legacy formatters (not in active pipeline — kept for compatibility)
# ──────────────────────────────────────────

def _format_summary_message(complex_name: str, data: Dict) -> str:
    msg = (
        f"🏢 <b>{complex_name}</b>  리포트\n"
        f"<i>{_now_str()}</i>\n"
        f"{'─' * 24}\n\n"
        f"매물 {data.get('total_count', 0)}건\n"
        f"가격  {data.get('min_price', 'N/A')}억 ~ {data.get('max_price', 'N/A')}억\n"
        f"중앙가  {data.get('representative_price', 'N/A')}억\n"
    )
    return msg


def _format_drop_alert_message(complex_name: str, data: Dict) -> str:
    msg = (
        f"🚨 <b>가격 변동 알림</b>\n"
        f"🏢 <b>{complex_name}</b>\n"
        f"<i>{_now_str()}</i>\n"
        f"{'─' * 24}\n\n"
    )
    for label, key in [("전주", "week_change"), ("전월", "month_change"), ("전년", "year_change")]:
        ch = data.get(key, {})
        delta = ch.get("delta", "N/A")
        pct = ch.get("pct", "N/A")
        if delta != "N/A":
            arrow = "⬇️" if delta < 0 else "⬆️"
            msg += f"  {label}  {delta:+.1f}억 ({pct:+.1f}%)  {arrow}\n"
    return msg


def _format_comparison_message(
    my_data: Dict,
    target_data: Dict,
    my_home_area: Optional[float] = None,
) -> str:
    my_name = my_data.get("complex_name", "내 집")
    tgt_name = target_data.get("complex_name", "관심 단지")

    if my_home_area is None:
        my_home_area = EnvConfig.get_my_home_area()

    my_dist = my_data.get("price_distribution_by_area", {}).get("by_area", {})
    tgt_dist = target_data.get("price_distribution_by_area", {}).get("by_area", {})

    msg = f"⚖️ <b>{my_name}</b>  →  <b>{tgt_name}</b>\n"

    if not my_dist or not tgt_dist:
        msg += "비교 불가 (데이터 없음)\n"
        return msg

    if my_home_area:
        base_key = math.floor(my_home_area)
        my_area_key = min(my_dist.keys(), key=lambda x: abs(x - base_key)) if my_dist else None
        my_med = my_dist.get(my_area_key, {}).get("median", 0) if my_area_key else 0

        if my_med:
            msg += f"<i>내 단지 {my_area_key}㎡ 기준  {my_med:.1f}억</i>\n"
            rows = []
            for area in sorted(tgt_dist.keys()):
                tgt_med = tgt_dist[area].get("median", 0)
                if not tgt_med:
                    continue
                diff = tgt_med - my_med
                arrow = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➡️"
                rows.append(f"  {area:>3}㎡  {tgt_med:.1f}억  {diff:+.1f}억 {arrow}")
            if rows:
                msg += "<pre>" + "\n".join(rows) + "</pre>\n"
    else:
        my_overall = my_data.get("price_distribution_by_area", {}).get("overall", {})
        tgt_overall = target_data.get("price_distribution_by_area", {}).get("overall", {})
        my_med = my_overall.get("median", 0)
        tgt_med = tgt_overall.get("median", 0)
        if my_med and tgt_med:
            diff = tgt_med - my_med
            arrow = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➡️"
            msg += f"{my_med:.1f}억  →  {tgt_med:.1f}억  ({diff:+.1f}억 {arrow})\n"

    return msg
