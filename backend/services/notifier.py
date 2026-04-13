"""
LINE Notify integration.

Environment variable required:
    LINE_NOTIFY_TOKEN  — https://notify-bot.line.me/my/
"""
from __future__ import annotations

import os
from datetime import datetime

import httpx

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"

_token = os.getenv("LINE_NOTIFY_TOKEN", "")


def _refresh_token() -> str:
    """Re-read env var at call time so hot-reload of .env works in dev."""
    return os.getenv("LINE_NOTIFY_TOKEN", "")


async def send(message: str) -> tuple[bool, str]:
    """
    Send a LINE Notify message.

    Returns (success: bool, detail: str).
    """
    token = _refresh_token()
    if not token:
        return False, "LINE_NOTIFY_TOKEN 未設定"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                LINE_NOTIFY_URL,
                headers={"Authorization": f"Bearer {token}"},
                data={"message": message},
            )
        if r.status_code == 200:
            return True, "ok"
        return False, f"LINE API 回應 {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)


# ── Message builder ───────────────────────────────────────────────────────────

def build_scan_message(tw_results: list[dict], us_results: list[dict]) -> str:
    """Format scan results into a LINE Notify message string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"\n📊 股票訊號掃描報告 ({now})"]

    def _section(title: str, items: list[dict], sig: str) -> None:
        filtered = [r for r in items if r["signal"] == sig]
        if not filtered:
            return
        icon = "✅" if sig == "BUY" else "🔴"
        lines.append(f"\n【{title} - {'買入' if sig == 'BUY' else '賣出'}訊號】")
        for r in filtered:
            strat_str = "+".join(r["strategies"]) if r["strategies"] else ""
            chg = f"{'+' if r['change_pct'] >= 0 else ''}{r['change_pct']:.1f}%"
            lines.append(
                f"{icon} {r['name']}({r['symbol']}) {strat_str} "
                f"| 價格:{r['price']} ({chg})"
            )

    _section("台股", tw_results, "BUY")
    _section("台股", tw_results, "SELL")
    _section("美股", us_results, "BUY")
    _section("美股", us_results, "SELL")

    # If nothing signal-worthy
    has_signals = any(
        r["signal"] != "NONE" for r in tw_results + us_results
    )
    if not has_signals:
        lines.append("\n本次掃描無明顯買賣訊號。")

    return "\n".join(lines)
