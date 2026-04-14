"""yfinance integration for US stock data."""
import yfinance as yf
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import pytz


def get_stock_price(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch OHLCV data for a US stock via yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        df = df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                                 "Low": "low", "Close": "close", "Volume": "volume"})
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df.sort_values("date").reset_index(drop=True)
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"[yfinance] get_stock_price error: {e}")
        return pd.DataFrame()


def get_fundamental(symbol: str) -> dict:
    """
    Fetch comprehensive fundamental data including:
    - Key metrics (P/E, EPS, ROE, gross margin, etc.)
    - Quarterly EPS for the last 8 quarters
    - Quarterly revenue for the last 8 quarters
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}

        def safe(key, default=None):
            v = info.get(key, default)
            return v if v is not None else default

        # ── Quarterly income statement ────────────────────────────────────────
        eps_quarterly     = []
        revenue_quarterly = []
        try:
            q_stmt = ticker.quarterly_income_stmt  # cols=dates, rows=items
            if q_stmt is not None and not q_stmt.empty:
                # Sort columns chronologically (oldest first)
                sorted_cols = sorted(q_stmt.columns)

                # EPS
                for eps_key in ("Diluted EPS", "Basic EPS"):
                    if eps_key in q_stmt.index:
                        for dt in sorted_cols:
                            val = q_stmt.loc[eps_key, dt]
                            if pd.notna(val):
                                q = (dt.month - 1) // 3 + 1
                                eps_quarterly.append({
                                    "date":   f"{dt.year}-{q * 3:02d}",
                                    "period": f"{dt.year}Q{q}",
                                    "value":  round(float(val), 4),
                                })
                        eps_quarterly = eps_quarterly[-8:]
                        break

                # Revenue
                for rev_key in ("Total Revenue", "Operating Revenue"):
                    if rev_key in q_stmt.index:
                        for dt in sorted_cols:
                            val = q_stmt.loc[rev_key, dt]
                            if pd.notna(val):
                                q = (dt.month - 1) // 3 + 1
                                revenue_quarterly.append({
                                    "date":   f"{dt.year}-{q * 3:02d}",
                                    "period": f"{dt.year}Q{q}",
                                    "value":  round(float(val), 0),
                                })
                        revenue_quarterly = revenue_quarterly[-8:]
                        break
        except Exception as e:
            print(f"[yfinance] quarterly_income_stmt error: {e}")

        return {
            # Identity
            "symbol":      symbol,
            "name":        safe("longName", symbol),
            "sector":      safe("sector", "N/A"),
            "industry":    safe("industry", "N/A"),
            "description": safe("longBusinessSummary", ""),
            # Valuation
            "pe_ratio":      safe("trailingPE"),
            "forward_pe":    safe("forwardPE"),
            "eps":           safe("trailingEps"),
            "dividend_yield":safe("dividendYield"),
            # Size
            "market_cap":  safe("marketCap"),
            "avg_volume":  safe("averageVolume"),
            "52w_high":    safe("fiftyTwoWeekHigh"),
            "52w_low":     safe("fiftyTwoWeekLow"),
            # Profitability
            "revenue":       safe("totalRevenue"),
            "net_income":    safe("netIncomeToCommon"),
            "gross_margin":  safe("grossMargins"),
            "profit_margin": safe("profitMargins"),
            "roe":           safe("returnOnEquity"),
            "roa":           safe("returnOnAssets"),
            "debt_to_equity":safe("debtToEquity"),
            # Charts
            "eps_quarterly":     eps_quarterly,
            "revenue_quarterly": revenue_quarterly,
        }
    except Exception as e:
        print(f"[yfinance] get_fundamental error: {e}")
        return {"symbol": symbol, "error": str(e)}


def get_quote(symbol: str, market: str) -> dict:
    """Fetch the latest real-time / delayed quote via yfinance fast_info.

    TW stocks use the '.TW' suffix (TSE). If that returns no price, falls back
    to '.TWO' (OTC).  US stocks use the plain symbol.

    Returns:
        {
          "price":      float,
          "prev_close": float,
          "change":     float,
          "change_pct": float,   # percent, e.g. 1.23 = +1.23%
          "volume":     int | None,
          "day_open":   float | None,
          "day_high":   float | None,
          "day_low":    float | None,
          "updated_at": str,     # HH:MM:SS in Asia/Taipei
        }
    """
    tz_taipei = pytz.timezone("Asia/Taipei")

    def _safe(v):
        try:
            return round(float(v), 2) if v is not None else None
        except Exception:
            return None

    def _fetch(yf_symbol: str) -> dict | None:
        try:
            ticker = yf.Ticker(yf_symbol)
            fi     = ticker.fast_info

            price      = fi.last_price
            prev_close = fi.previous_close

            # Fallback: fast_info sometimes returns None outside market hours —
            # use the last two daily bars instead.
            if price is None or prev_close is None:
                hist = ticker.history(period="5d", interval="1d", auto_adjust=True)
                if hist.empty:
                    return None
                price      = float(hist["Close"].iloc[-1])
                prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price

            price      = float(price)
            prev_close = float(prev_close)
            change     = round(price - prev_close, 4)
            change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close else 0.0
            return {
                "price":      round(price, 2),
                "prev_close": round(prev_close, 2),
                "change":     change,
                "change_pct": change_pct,
                "volume":     int(fi.last_volume) if getattr(fi, "last_volume", None) else None,
                "day_open":   _safe(getattr(fi, "open",     None)),
                "day_high":   _safe(getattr(fi, "day_high", None)),
                "day_low":    _safe(getattr(fi, "day_low",  None)),
                "updated_at": datetime.now(tz=tz_taipei).strftime("%H:%M:%S"),
            }
        except Exception as e:
            print(f"[yfinance] get_quote error for {yf_symbol}: {e}")
            return None

    if market == "tw":
        result = _fetch(f"{symbol}.TW") or _fetch(f"{symbol}.TWO")
    else:
        result = _fetch(symbol)

    return result or {"error": f"無法取得 {symbol} 的即時報價"}


def get_intraday(symbol: str, market: str, interval: str = "5m") -> pd.DataFrame:
    """Fetch intraday OHLCV bars via yfinance.

    Supported intervals: 1m, 5m, 15m, 60m
    Returns a DataFrame with columns: date (Unix timestamp int), open, high, low, close, volume
    The `date` column is seconds-since-epoch so lightweight-charts can render intraday bars.
    """
    valid = {"1m", "5m", "15m", "60m", "1wk", "1mo"}
    if interval not in valid:
        interval = "5m"

    # yfinance max-period limits per interval
    period_map = {"1m": "2d", "5m": "5d", "15m": "5d", "60m": "5d", "1wk": "5y", "1mo": "5y"}
    period = period_map.get(interval, "5d")

    def _fetch(yf_sym: str) -> pd.DataFrame:
        try:
            df = yf.Ticker(yf_sym).history(period=period, interval=interval, auto_adjust=True)
            return df
        except Exception as e:
            print(f"[yfinance] get_intraday error for {yf_sym}: {e}")
            return pd.DataFrame()

    if market == "tw":
        df = _fetch(f"{symbol}.TW")
        if df.empty:
            df = _fetch(f"{symbol}.TWO")
    else:
        df = _fetch(symbol)

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    date_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={
        date_col: "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    })

    # Strip timezone, convert to UTC Unix timestamp (seconds) for lightweight-charts
    df["date"] = pd.to_datetime(df["date"])
    if df["date"].dt.tz is not None:
        df["date"] = df["date"].dt.tz_convert("UTC").dt.tz_localize(None)
    df["date"] = (df["date"].astype("int64") // 10 ** 9).astype(int)

    df = df.sort_values("date").reset_index(drop=True)
    df = df.dropna(subset=["open", "close"])
    return df[["date", "open", "high", "low", "close", "volume"]]


def get_news_with_sentiment(symbol: str, limit: int = 15) -> list[dict]:
    """Fetch recent news and score sentiment via TextBlob."""
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news or []
        results = []
        for item in raw_news[:limit]:
            title = item.get("title", "")
            sentiment = TextBlob(title).sentiment
            polarity = sentiment.polarity          # -1.0 ~ 1.0
            if polarity > 0.05:
                label = "positive"
            elif polarity < -0.05:
                label = "negative"
            else:
                label = "neutral"
            results.append({
                "title":     title,
                "publisher": item.get("publisher", ""),
                "link":      item.get("link", ""),
                "published": item.get("providerPublishTime", 0),
                "sentiment": label,
                "polarity":  round(polarity, 3),
            })
        return results
    except Exception as e:
        print(f"[yfinance] get_news_with_sentiment error: {e}")
        return []
