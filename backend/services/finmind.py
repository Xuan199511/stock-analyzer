"""FinMind API integration for Taiwan stock data (free, no API key required)."""
import httpx
import pandas as pd
from datetime import datetime

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


async def _fetch(dataset: str, data_id: str, start_date: str, end_date: str) -> dict:
    params = {
        "dataset": dataset,
        "data_id": data_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(FINMIND_URL, params=params)
        r.raise_for_status()
        return r.json()


async def get_stock_price(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch OHLCV data for a Taiwan stock."""
    try:
        data = await _fetch("TaiwanStockPrice", symbol, start_date, end_date)
        if data.get("status") != 200 or not data.get("data"):
            return pd.DataFrame()
        df = pd.DataFrame(data["data"])
        df = df.rename(columns={"max": "high", "min": "low", "Trading_Volume": "volume"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0).astype(int)
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        print(f"[FinMind] get_stock_price error: {e}")
        return pd.DataFrame()


async def get_per(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch P/E ratio history."""
    try:
        data = await _fetch("TaiwanStockPER", symbol, start_date, end_date)
        if data.get("status") != 200 or not data.get("data"):
            return []
        return data["data"]
    except Exception as e:
        print(f"[FinMind] get_per error: {e}")
        return []


async def get_financial_statements(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch income statement / financial data."""
    try:
        data = await _fetch("TaiwanStockFinancialStatements", symbol, start_date, end_date)
        if data.get("status") != 200 or not data.get("data"):
            return []
        return data["data"]
    except Exception as e:
        print(f"[FinMind] get_financial_statements error: {e}")
        return []


async def get_monthly_revenue(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch monthly revenue data."""
    try:
        data = await _fetch("TaiwanStockMonthRevenue", symbol, start_date, end_date)
        if data.get("status") != 200 or not data.get("data"):
            return []
        return data["data"]
    except Exception as e:
        print(f"[FinMind] get_monthly_revenue error: {e}")
        return []


async def get_news(symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Fetch news for a Taiwan stock."""
    try:
        data = await _fetch("TaiwanStockNews", symbol, start_date, end_date)
        if data.get("status") != 200 or not data.get("data"):
            return []
        return data["data"]
    except Exception as e:
        print(f"[FinMind] get_news error: {e}")
        return []
