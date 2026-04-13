"""yfinance integration for US stock data."""
import yfinance as yf
import pandas as pd
from textblob import TextBlob


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
