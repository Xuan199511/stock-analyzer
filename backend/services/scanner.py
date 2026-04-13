"""
Signal scanner service.

Scans a hardcoded watchlist, detects which stocks have active entry/exit
signals across all four strategies (ma_cross, rsi, macd, bb), and returns
a structured result for each symbol.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pandas as pd

from services import finmind, yfinance_service
from services.backtest_engine import _STRATEGIES, STRATEGY_DEFAULTS

# ── Watchlist (hardcoded per spec) ────────────────────────────────────────────

WATCHLIST: dict[str, list[str]] = {
    "TW": ["2330", "2317", "2454", "2308", "2382", "6505"],
    "US": ["AAPL", "NVDA", "TSLA", "MSFT", "META", "GOOGL"],
}

TW_NAMES: dict[str, str] = {
    "2330": "台積電",
    "2317": "鴻海",
    "2454": "聯發科",
    "2308": "台達電",
    "2382": "廣達",
    "6505": "台塑化",
}

US_NAMES: dict[str, str] = {
    "AAPL":  "Apple",
    "NVDA":  "NVIDIA",
    "TSLA":  "Tesla",
    "MSFT":  "Microsoft",
    "META":  "Meta",
    "GOOGL": "Alphabet",
}

_SIGNAL_LABELS = {
    "ma_cross": "MA交叉",
    "rsi":      "RSI",
    "macd":     "MACD",
    "bb":       "布林帶",
}


# ── Per-symbol scan ───────────────────────────────────────────────────────────

async def _fetch_df(symbol: str, market: str) -> pd.DataFrame:
    """Fetch ~200 calendar days of OHLCV (enough for all indicators)."""
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=300)).strftime("%Y-%m-%d")

    if market == "TW":
        return await finmind.get_stock_price(symbol, start_date, end_date)

    # yfinance is synchronous — run in thread pool to avoid blocking
    return await asyncio.to_thread(
        yfinance_service.get_stock_price, symbol, start_date, end_date
    )


async def scan_symbol(symbol: str, market: str) -> dict | None:
    """
    Scan a single symbol for active signals.

    Returns a dict:
        symbol, name, market, price, change_pct,
        signal ("BUY"|"SELL"|"NONE"), strength ("strong"|"moderate"|"weak"|""),
        strategies (list of active strategy labels)
    or None if data is unavailable.
    """
    try:
        df = await _fetch_df(symbol, market)
    except Exception as e:
        print(f"[Scanner] fetch error {symbol}: {e}")
        return None

    if df is None or df.empty or len(df) < 35:
        return None

    close = df["close"]

    # Latest price and 1-day change
    price      = round(float(close.iloc[-1]), 2)
    prev_price = float(close.iloc[-2]) if len(close) > 1 else price
    change_pct = round((price / prev_price - 1.0) * 100.0, 2) if prev_price else 0.0

    # Run every strategy and inspect the last bar
    buy_strats:  list[str] = []
    sell_strats: list[str] = []

    for strat_name, strat_fn in _STRATEGIES.items():
        params   = STRATEGY_DEFAULTS[strat_name]
        entries, exits = strat_fn(close, params)

        if bool(entries.fillna(False).iloc[-1]):
            buy_strats.append(_SIGNAL_LABELS[strat_name])
        elif bool(exits.fillna(False).iloc[-1]):
            sell_strats.append(_SIGNAL_LABELS[strat_name])

    # Determine dominant signal
    if len(buy_strats) > len(sell_strats):
        signal   = "BUY"
        strength = _strength(len(buy_strats))
        active   = buy_strats
    elif len(sell_strats) > len(buy_strats):
        signal   = "SELL"
        strength = _strength(len(sell_strats))
        active   = sell_strats
    else:
        signal   = "NONE"
        strength = ""
        active   = buy_strats + sell_strats  # mixed / empty

    names = TW_NAMES if market == "TW" else US_NAMES

    return {
        "symbol":     symbol,
        "name":       names.get(symbol, symbol),
        "market":     market,
        "price":      price,
        "change_pct": change_pct,
        "signal":     signal,
        "strength":   strength,
        "strategies": active,
    }


def _strength(n: int) -> str:
    if n >= 3: return "strong"
    if n == 2: return "moderate"
    return "weak"


# ── Market-level scan ─────────────────────────────────────────────────────────

async def scan_market(market: str) -> list[dict]:
    """Scan all symbols in the given market's watchlist concurrently."""
    symbols = WATCHLIST.get(market.upper(), [])
    tasks   = [scan_symbol(sym, market.upper()) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return [r for r in results if r is not None]


async def scan_all() -> dict[str, list[dict]]:
    """Scan both TW and US watchlists concurrently."""
    tw_task = scan_market("TW")
    us_task = scan_market("US")
    tw, us  = await asyncio.gather(tw_task, us_task)
    return {"TW": tw, "US": us}
