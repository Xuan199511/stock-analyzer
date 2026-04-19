"""Extended FinMind queries for institutional/margin data.

Re-uses the low-level ``_fetch`` helper logic from ``services.finmind`` but
adds datasets the original file didn't cover.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import httpx

from ..logging_config import logger

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
_TOKEN = os.getenv("FINMIND_API_KEY") or os.getenv("FINMIND_TOKEN", "")
_log = logger.bind(section="finmind")


async def _fetch(dataset: str, data_id: str, start: str, end: str) -> list[dict]:
    params = {
        "dataset":    dataset,
        "data_id":    data_id,
        "start_date": start,
        "end_date":   end,
    }
    if _TOKEN:
        params["token"] = _TOKEN
    import time as _t
    t0 = _t.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(FINMIND_URL, params=params)
            r.raise_for_status()
            payload = r.json()
    except httpx.HTTPStatusError as e:
        _log.warning(f"{dataset} {data_id} HTTP {e.response.status_code}")
        return []
    except Exception as e:
        _log.warning(f"{dataset} {data_id} error: {e}")
        return []
    dt = _t.perf_counter() - t0
    if payload.get("status") != 200:
        _log.info(f"{dataset} {data_id} api_status={payload.get('status')} {dt:.2f}s")
        return []
    rows = payload.get("data") or []
    _log.info(f"{dataset} {data_id} rows={len(rows)} {dt:.2f}s")
    return rows


def _date_range(days: int) -> tuple[str, str]:
    end   = datetime.today().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


async def institutional_investors(symbol: str, days: int = 10) -> list[dict]:
    """三大法人買賣超（近 N 天）."""
    start, end = _date_range(days)
    return await _fetch("TaiwanStockInstitutionalInvestorsBuySell", symbol, start, end)


async def margin_purchase_short_sale(symbol: str, days: int = 10) -> list[dict]:
    """融資融券 (近 N 天)."""
    start, end = _date_range(days)
    return await _fetch("TaiwanStockMarginPurchaseShortSale", symbol, start, end)


async def shareholding(symbol: str, days: int = 60) -> list[dict]:
    start, end = _date_range(days)
    return await _fetch("TaiwanStockShareholding", symbol, start, end)


async def total_institutional_flow(symbol: str, days: int = 5) -> dict:
    """Aggregate last N days' foreign/investment/dealer net-buy lot totals."""
    rows = await institutional_investors(symbol, days=days + 5)
    if not rows:
        return {"foreign": None, "investment": None, "dealer": None, "period_days": days}

    # FinMind rows: {date, name, buy, sell, ...}
    agg = {"Foreign_Investor": 0.0, "Investment_Trust": 0.0, "Dealer": 0.0}
    for r in rows[-(days * 4):]:
        name = r.get("name", "")
        net  = float(r.get("buy", 0) or 0) - float(r.get("sell", 0) or 0)
        if name in agg:
            agg[name] += net
        elif "Dealer" in name:
            agg["Dealer"] += net
    return {
        "foreign":     round(agg["Foreign_Investor"], 0),
        "investment":  round(agg["Investment_Trust"], 0),
        "dealer":      round(agg["Dealer"], 0),
        "period_days": days,
    }


async def margin_change(symbol: str, days: int = 5) -> dict:
    rows = await margin_purchase_short_sale(symbol, days=days + 5)
    if not rows:
        return {"margin_change": None, "short_change": None, "period_days": days}
    recent = rows[-days:]
    margin_delta = 0.0
    short_delta  = 0.0
    for r in recent:
        margin_delta += float(r.get("MarginPurchaseTodayBalance", 0) or 0) \
                       - float(r.get("MarginPurchaseYesterdayBalance", 0) or 0)
        short_delta  += float(r.get("ShortSaleTodayBalance", 0) or 0) \
                       - float(r.get("ShortSaleYesterdayBalance", 0) or 0)
    return {
        "margin_change": round(margin_delta, 0),
        "short_change":  round(short_delta, 0),
        "period_days":   days,
    }
