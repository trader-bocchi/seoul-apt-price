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
            success = self.send_message(full)
        else:
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

        if success:
            CSVStore.save_telegram_log("all_complexes_analysis", {
                "sent_at": datetime.now().isoformat(),
                "message_type": "all_complexes_analysis",
                "complex_names": ",".join(all_analyses.keys()),
                "message_body": full,
            })
        return success

    def send_my_home_detailed_analysis(self, complex_name: str, analysis_data: Dict) -> bool:
        message = _format_my_home_detailed(complex_name, analysis_data)
        success = self.send_message(message)
        if success:
            CSVStore.save_telegram_log("my_home_detailed_analysis", {
                "sent_at": datetime.now().isoformat(),
                "message_type": "my_home_detailed_analysis",
                "complex_name": complex_name,
                "message_body": message,
            })
        return success

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

    def send_migration_report(self, report: Dict) -> bool:
        """이사 비교 레포트 전송 (스냅샷 메시지 + 추세 메시지)"""
        msg1 = _format_migration_snapshot(report)
        ok1 = self.send_message(msg1)

        msg2 = _format_migration_trend(report)
        ok2 = self.send_message(msg2) if msg2 else True

        return ok1 and ok2

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

    lease_by_area = data.get("lease_distribution_by_area", {}).get("by_area", {})

    for area_key in sorted_areas[:5]:
        area_data = detailed[area_key]
        sale_cnt = by_area.get(area_key, {}).get("count", 0)
        sale_med = by_area.get(area_key, {}).get("median")
        lease_info = lease_by_area.get(area_key, {})
        lease_cnt = lease_info.get("count", 0)
        lease_med = lease_info.get("median")

        # 헤더: 평형 + 매매/전세 중위 요약
        header_parts = [f"<b>▪ {area_key}㎡</b>"]
        if sale_med is not None:
            header_parts.append(f"매매 {sale_med:.1f}억({sale_cnt}건)")
        if lease_med is not None:
            gap = round(sale_med - lease_med, 2) if sale_med is not None else None
            gap_str = f"  갭 {gap:.1f}억" if gap is not None else ""
            header_parts.append(f"전세 {lease_med:.1f}억({lease_cnt}건){gap_str}")
        msg += "  ".join(header_parts) + "\n"

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

        # 특이 매물 (매물특징설명 키워드 기반)
        special = area_data.get("special_listings", {})
        kw_groups = special.get("keyword_groups", {})
        if kw_groups:
            median_p = special.get("median_price", 0)
            rows = []
            for kw, s in kw_groups.items():
                sign = "+" if s["premium"] >= 0 else ""
                rows.append(
                    f"  [{kw}] {s['count']}건  평균 {s['avg_price']:.1f}억"
                    f"  ({sign}{s['premium']:.1f}억 vs 중앙 {median_p:.1f}억)"
                )
                for listing in s.get("listings", [])[:3]:
                    dev = listing["price"] - median_p
                    sign2 = "+" if dev >= 0 else ""
                    floor = listing.get("floor", "")
                    direction = listing.get("direction", "")
                    rows.append(
                        f"    {listing['price']:.1f}억  {floor}층  {direction}"
                        f"  ({sign2}{dev:.1f}억)"
                    )
            msg += "  <b>특이 매물</b>\n<pre>" + "\n".join(rows) + "</pre>\n"

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


def _fmt_price(val: Optional[float], suffix: str = "억") -> str:
    """None이면 '-', 아니면 소수점 1자리 + suffix"""
    if val is None:
        return "-"
    return f"{val:.1f}{suffix}"


def _fmt_pyeong(val: Optional[int]) -> str:
    if val is None:
        return "-"
    return f"{val:,}만"


def _format_migration_snapshot(report: Dict) -> str:
    """
    메시지 1: 이사 비교 분석 — 단지별 블록 형식

    🏠 내 단지: 산들마을  전용 51㎡
    매매 9.3억 | 평당 5,920만 | 전세 6.8억 | 갭 2.5억

    🏢 산성역포레스티아
      59㎡  매매 14.5억 | 평당 8,010만 | 전세 7.2억 | 갭 7.3억
      84㎡  매매 16.0억 | 평당 6,229만 | 전세 8.5억 | 갭 7.5억
    ...
    """
    now = datetime.now()
    my = report["my_home"]
    targets = report["targets"]

    my_stats = my.get("stats") or {}
    my_sale = _fmt_price(my_stats.get("sale_median"))
    my_pyeong = _fmt_pyeong(my_stats.get("price_per_pyeong"))
    my_lease = _fmt_price(my_stats.get("lease_median"))
    my_gap = _fmt_price(my_stats.get("lease_gap"))

    msg = (
        f"🔄 <b>이사 비교 분석</b>\n"
        f"<i>{now.strftime(f'%Y-%m-%d ({_WEEKDAY_KR[now.weekday()]}) %H:%M')}</i>\n"
        f"{'─' * 24}\n\n"
        f"🏠 <b>내 단지: {my['name']}</b>  전용 {my['area']}㎡\n"
        f"  매매 {my_sale} | 평당 {my_pyeong} | 전세 {my_lease} | 갭 {my_gap}\n"
    )

    if not targets:
        return msg + "\n비교 데이터 없음\n"

    sub_notes: List[str] = []

    for t in targets:
        name = t["name"]
        area_matched = t["area_matched"]
        snapshots = t["snapshots"]

        msg += f"\n🏢 <b>{name}</b>\n"

        for t_area in [59, 84]:
            if t_area not in area_matched:
                continue
            actual = area_matched[t_area]
            stats = snapshots.get(t_area) or {}

            area_label = f"{actual}㎡"
            note = ""
            if actual != t_area:
                note = f"*"
                sub_notes.append(f"*{name} {t_area}→{actual}㎡")

            sale = _fmt_price(stats.get("sale_median"))
            pyeong = _fmt_pyeong(stats.get("price_per_pyeong"))
            lease = _fmt_price(stats.get("lease_median"))
            gap = _fmt_price(stats.get("lease_gap"))

            msg += (
                f"  {area_label}{note}  "
                f"매매 {sale} | 평당 {pyeong} | 전세 {lease} | 갭 {gap}\n"
            )

    if sub_notes:
        msg += "\n<i>" + "  ".join(sub_notes) + " (인근 평형 대체)</i>\n"

    return msg


def _format_migration_trend(report: Dict) -> str:
    """
    메시지 2: 매매 중위 추세 (억)

    📈 매매 중위 추세 (억)
    <pre>
                  현재   1M전   3M전   6M전   1Y전
    내단지 51㎡   10.5   10.2      -      -      -
    원베일리 59㎡ 23.0   22.5   22.0      -      -
    ...
    </pre>
    데이터 없는 구간은 열 자체를 숨김.
    """
    my = report["my_home"]
    targets = report["targets"]

    # 어떤 기간 컬럼이 실제로 존재하는지 파악
    all_period_labels = [label for label, *_ in [("1M",), ("3M",), ("6M",), ("1Y",)]]
    # 실제 순서 유지
    period_order = ["1M", "3M", "6M", "1Y"]

    used_periods: set = set()
    # 내 단지 trend
    my_trend = my.get("trend", {})
    used_periods.update(k for k, v in my_trend.items() if v is not None)
    # 타겟 trend
    for t in targets:
        for period_label, area_vals in t.get("trend", {}).items():
            if any(v is not None for v in area_vals.values()):
                used_periods.add(period_label)

    active_periods = [p for p in period_order if p in used_periods]

    if not active_periods and not my_trend:
        return ""  # 시계열 데이터 없으면 메시지 미전송

    # 헤더 행
    period_headers = "  ".join(f"{p:>6}" for p in active_periods)
    header = f"{'':16}  {'현재':>6}  {period_headers}"

    rows: List[str] = []

    # 내 단지 행
    my_current = my.get("stats", {}) or {}
    my_current_val = _fmt_price(my_current.get("sale_median"), "")
    my_period_vals = "  ".join(
        f"{_fmt_price(my_trend.get(p), ''):>6}" for p in active_periods
    )
    my_label = f"{my['name'][:6]} {my['area']}㎡"
    rows.append(f"{my_label:<16}  {my_current_val:>6}  {my_period_vals}")

    # 타겟 단지 행
    for t in targets:
        name_short = t["name"][:6]
        trend = t.get("trend", {})
        snapshots = t.get("snapshots", {})
        area_matched = t.get("area_matched", {})

        for t_area in [59, 84]:
            if t_area not in area_matched:
                continue
            actual = area_matched[t_area]
            current_stats = snapshots.get(t_area) or {}
            current_val = _fmt_price(current_stats.get("sale_median"), "")

            period_vals = "  ".join(
                f"{_fmt_price((trend.get(p) or {}).get(t_area), ''):>6}"
                for p in active_periods
            )
            label = f"{name_short} {actual}㎡"
            rows.append(f"{label:<16}  {current_val:>6}  {period_vals}")

    table = header + "\n" + "\n".join(rows)
    now = datetime.now()
    return (
        f"📈 <b>매매 중위 추세</b> (억)\n"
        f"<i>{now.strftime(f'%Y-%m-%d ({_WEEKDAY_KR[now.weekday()]}) %H:%M')}</i>\n"
        f"{'─' * 24}\n"
        f"<pre>{table}</pre>\n"
    )


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
