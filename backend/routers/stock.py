"""K-line (OHLCV) and technical indicator endpoints."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import pandas as pd

from services import finmind, yfinance_service, indicators

router = APIRouter()

# ── helpers ──────────────────────────────────────────────────────────────────

def _df_to_candles(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "date":   str(row["date"])[:10],
            "open":   round(float(row["open"]),  4),
            "high":   round(float(row["high"]),  4),
            "low":    round(float(row["low"]),   4),
            "close":  round(float(row["close"]), 4),
            "volume": int(row["volume"]),
        }
        for _, row in df.iterrows()
    ]


def _resolve_market(market: str) -> str:
    """Normalise market param to lowercase 'tw' / 'us'."""
    return market.strip().lower()


async def _fetch_df(symbol: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    if market == "tw":
        return await finmind.get_stock_price(symbol, start_date, end_date)
    return yfinance_service.get_stock_price(symbol, start_date, end_date)


def _date_range(limit: int) -> tuple[str, str]:
    """Return (start, end) covering enough calendar days for `limit` trading bars."""
    # Assume ~5 trading days / week → multiply by 1.5 for safety + weekends/holidays
    calendar_days = max(int(limit * 1.5) + 30, 180)
    end   = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - timedelta(days=calendar_days)).strftime("%Y-%m-%d")
    return start, end


# ── NEW: GET /api/stock/{symbol}/kline ───────────────────────────────────────

@router.get("/{symbol}/kline")
async def get_kline(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
    period: str = Query("daily", description="目前僅支援 daily"),
    limit:  int = Query(120, ge=10, le=2000, description="回傳筆數上限"),
):
    """回傳 OHLCV K 線資料，最多 limit 筆（最新的 limit 根）。

    回傳格式：[{date, open, high, low, close, volume}, ...]
    """
    mkt = _resolve_market(market)
    start_date, end_date = _date_range(limit)

    df = await _fetch_df(symbol.upper(), mkt, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"找不到 {symbol}（{market}）的資料")

    # Take the tail so we always return the *most recent* `limit` bars
    df = df.tail(limit).reset_index(drop=True)
    return _df_to_candles(df)


# ── NEW: GET /api/stock/{symbol}/indicators ──────────────────────────────────

@router.get("/{symbol}/indicators")
async def get_indicators(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
):
    """計算並回傳 MA20、MA60、RSI(14)、MACD(12,26,9)、布林帶(20,2)。

    回傳格式：
    {
      "ma20":  [{date, value}],
      "ma60":  [{date, value}],
      "rsi":   [{date, value}],
      "macd":  {"line": [...], "signal": [...], "hist": [...]},
      "bb":    {"upper": [...], "mid": [...], "lower": [...]}
    }
    """
    mkt = _resolve_market(market)
    # 需要至少 60 根才能算出 MA60；多抓些以讓指標穩定
    start_date, end_date = _date_range(limit=300)

    df = await _fetch_df(symbol.upper(), mkt, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"找不到 {symbol}（{market}）的資料")

    return indicators.calculate_indicators(df)


# ── NEW: GET /api/stock/{symbol}/intraday ───────────────────────────────────

@router.get("/{symbol}/intraday")
async def get_intraday(
    symbol:   str,
    market:   str = Query("TW",  description="TW 或 US"),
    interval: str = Query("5m",  description="1m | 5m | 15m | 60m"),
):
    """分鐘 / 小時 K 線，透過 yfinance 取得（約 15 分鐘延遲）。

    - 1m  → 最近 2 個交易日
    - 5m / 15m / 60m → 最近 5 個交易日

    回傳格式：[{date (Unix 秒), open, high, low, close, volume}, ...]
    date 為 Unix timestamp（整數秒），供 lightweight-charts 直接使用。
    """
    import asyncio
    mkt = _resolve_market(market)
    df  = await asyncio.to_thread(yfinance_service.get_intraday, symbol.upper(), mkt, interval)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"找不到 {symbol}（{market}）的分鐘資料")
    return [
        {
            "date":   int(row["date"]),
            "open":   round(float(row["open"]),  4),
            "high":   round(float(row["high"]),  4),
            "low":    round(float(row["low"]),   4),
            "close":  round(float(row["close"]), 4),
            "volume": int(row["volume"]),
        }
        for _, row in df.iterrows()
    ]


# ── NEW: GET /api/stock/{symbol}/quote ──────────────────────────────────────

@router.get("/{symbol}/quote")
async def get_quote(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
):
    """即時（或延遲 15 分鐘）報價，透過 yfinance fast_info 取得。

    TW 股票先嘗試 TSE（.TW），失敗再嘗試 OTC（.TWO）。

    回傳格式：
    {
      "price":      float,
      "prev_close": float,
      "change":     float,
      "change_pct": float,   # 漲跌幅 %
      "volume":     int | null,
      "updated_at": "HH:MM:SS",  # 台北時間
    }
    """
    import asyncio
    mkt    = _resolve_market(market)
    result = await asyncio.to_thread(yfinance_service.get_quote, symbol.upper(), mkt)
    if "error" in result:
        raise HTTPException(status_code=503, detail=result["error"])
    return result


# ── NEW: GET /api/stock/{symbol}/sr ─────────────────────────────────────────

@router.get("/{symbol}/sr")
async def get_support_resistance(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
    window: int  = Query(10, ge=3,  le=30,  description="樞紐點左右視窗（根數）"),
    levels: int  = Query(5,  ge=1,  le=10,  description="最多回傳幾條支撐/壓力線"),
):
    """計算支撐位與壓力位（Pivot-Point 聚類法）。

    回傳格式：
    {
      "support":       [{"price": float, "strength": int}, ...],
      "resistance":    [{"price": float, "strength": int}, ...],
      "current_price": float,
    }
    strength = 有幾個樞紐點落在同一價格區間（越大代表該位置被測試越多次）。
    """
    import asyncio, traceback
    mkt = _resolve_market(market)
    sym = symbol.upper()

    _empty = {"support": [], "resistance": [], "current_price": 0}

    try:
        start_date, end_date = _date_range(limit=300)

        # Always run data fetch in a thread so sync yfinance calls don't block the loop
        if mkt == "tw":
            df = await _fetch_df(sym, mkt, start_date, end_date)
        else:
            df = await asyncio.to_thread(
                yfinance_service.get_stock_price, sym, start_date, end_date
            )

        if df.empty:
            return _empty

        result = indicators.calculate_sr(df, window=window, n_levels=levels)
        return result
    except Exception:
        print(f"[/sr] {sym} ({mkt}) error:\n{traceback.format_exc()}")
        return _empty


# ── LEGACY: GET /api/stock/candles/{symbol} ──────────────────────────────────

@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    market: str = Query("tw", enum=["tw", "us"]),
    start:  str = Query(None, description="YYYY-MM-DD"),
    end:    str = Query(None, description="YYYY-MM-DD"),
):
    """舊版端點：同時回傳 K 線 + 技術指標（仍可使用）。"""
    end_date   = end   or datetime.today().strftime("%Y-%m-%d")
    start_date = start or (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")

    df = await _fetch_df(symbol, market, start_date, end_date)

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol} ({market})")

    return {
        "symbol":     symbol,
        "market":     market,
        "start":      start_date,
        "end":        end_date,
        "candles":    _df_to_candles(df),
        "indicators": indicators.calculate_all(df),
    }
