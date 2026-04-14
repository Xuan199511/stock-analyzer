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


# ── NEW: GET /api/stock/{symbol}/fundamental ─────────────────────────────────

@router.get("/{symbol}/fundamental")
async def get_stock_fundamental(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
):
    """回傳基本面分析：關鍵指標 + 近 8 季 EPS + 近 12 月/季營收。

    回傳格式：
    {
      "symbol": str,
      "market": str,
      "metrics": {pe_ratio, pb_ratio, eps, roe, gross_margin, ...},
      "eps_quarterly":  [{date, period, value}, ...],   # 最近 8 季
      "revenue_trend":  [{date, period, value}, ...],   # TW 月/US 季
    }
    """
    mkt = _resolve_market(market)
    sym = symbol.upper()

    if mkt == "us":
        raw = yfinance_service.get_fundamental(sym)
        if "error" in raw and len(raw) <= 2:
            raise HTTPException(status_code=404, detail=raw.get("error", "Not found"))
        return {
            "symbol": sym,
            "market": "US",
            "metrics": {
                "pe_ratio":      raw.get("pe_ratio"),
                "forward_pe":    raw.get("forward_pe"),
                "eps":           raw.get("eps"),
                "roe":           raw.get("roe"),
                "gross_margin":  raw.get("gross_margin"),
                "profit_margin": raw.get("profit_margin"),
                "dividend_yield":raw.get("dividend_yield"),
                "market_cap":    raw.get("market_cap"),
                "52w_high":      raw.get("52w_high"),
                "52w_low":       raw.get("52w_low"),
                "revenue":       raw.get("revenue"),
                "name":          raw.get("name"),
                "sector":        raw.get("sector"),
                "description":   raw.get("description"),
            },
            "eps_quarterly": raw.get("eps_quarterly", []),
            "revenue_trend": raw.get("revenue_quarterly", []),
        }

    # ── Taiwan stock (FinMind) ────────────────────────────────────────────────
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")

    import asyncio
    per_data, fs_data, rev_data = await asyncio.gather(
        finmind.get_per(sym, start_date, end_date),
        finmind.get_financial_statements(sym, start_date, end_date),
        finmind.get_monthly_revenue(sym, start_date, end_date),
    )

    # Latest PER / PBR / DividendYield
    per_latest = per_data[-1] if per_data else {}

    # EPS quarterly — filter type=="EPS", convert date to quarter label
    eps_records = sorted(
        [r for r in fs_data if r.get("type") == "EPS"],
        key=lambda r: r.get("date", ""),
    )
    eps_quarterly = []
    for r in eps_records:
        d = str(r.get("date", ""))
        if len(d) >= 7:
            year, month = d[:4], int(d[5:7])
            q = (month - 1) // 3 + 1
            eps_quarterly.append({
                "date":   f"{year}-{month:02d}",
                "period": f"{year}Q{q}",
                "value":  float(r.get("value", 0)),
            })
    eps_quarterly = eps_quarterly[-8:]

    # Monthly revenue — last 12 months
    revenue_trend = [
        {
            "date":   str(r.get("date", ""))[:7],
            "period": str(r.get("date", ""))[:7],
            "value":  float(r.get("revenue", 0)),
        }
        for r in rev_data[-12:]
    ]

    latest_eps = eps_quarterly[-1]["value"] if eps_quarterly else None

    return {
        "symbol": sym,
        "market": "TW",
        "metrics": {
            "pe_ratio":      per_latest.get("PER"),
            "pb_ratio":      per_latest.get("PBR"),
            "eps":           latest_eps,
            "roe":           None,
            "gross_margin":  None,
            "profit_margin": None,
            "dividend_yield":per_latest.get("DividendYield"),
            "market_cap":    None,
            "52w_high":      None,
            "52w_low":       None,
            "revenue":       None,
        },
        "eps_quarterly": eps_quarterly,
        "revenue_trend": revenue_trend,
    }


# ── NEW: GET /api/stock/{symbol}/sentiment ───────────────────────────────────

@router.get("/{symbol}/sentiment")
async def get_stock_sentiment(
    symbol: str,
    market: str = Query("TW", description="TW 或 US"),
):
    """NewsAPI 取新聞 + Claude 批次情緒分析。

    回傳格式：
    {
      "symbol": str, "market": str, "source": "claude"|"keyword"|"none",
      "overall": "positive"|"neutral"|"negative",
      "score":   0-100,
      "summary": "一句話中文摘要",
      "news":    [{title, url, source, date, sentiment, reason}],
      "trend":   [{date, score, count}]   # 近 7 天
    }

    前置條件（.env）：
      NEWS_API_KEY      — NewsAPI 免費帳號 key
      ANTHROPIC_API_KEY — Anthropic API key
    """
    from services.news_sentiment import fetch_news, analyze_with_claude

    sym = symbol.upper()
    mkt = _resolve_market(market)

    # Build search query: TW stocks use company code + "Taiwan stock"
    query = f"{sym} Taiwan stock" if mkt == "tw" else sym

    articles = await fetch_news(query, days=7, limit=10)
    result   = await analyze_with_claude(sym, articles)

    return {"symbol": sym, "market": market.upper(), **result}


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
