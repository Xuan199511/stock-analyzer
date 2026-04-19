"""yfinance data source for deep analysis.

Thin wrapper around the existing ``services.yfinance_service`` + extra calls
needed for fundamentals, analyst targets, and peer discovery.
"""
from __future__ import annotations

from typing import Any
import pandas as pd
import yfinance as yf

from ..logging_config import logger

_log = logger.bind(section="yfinance")


def _yf_symbol(symbol: str, market: str) -> str:
    if market.upper() == "TW":
        return f"{symbol}.TW"
    return symbol


def ticker(symbol: str, market: str) -> yf.Ticker:
    return yf.Ticker(_yf_symbol(symbol, market))


def fetch_info(symbol: str, market: str) -> dict[str, Any]:
    try:
        t = ticker(symbol, market)
        info = t.info or {}
        if market.upper() == "TW" and not info.get("regularMarketPrice"):
            alt = yf.Ticker(f"{symbol}.TWO")
            alt_info = alt.info or {}
            if alt_info.get("regularMarketPrice"):
                return alt_info
        return info
    except Exception as e:
        _log.warning(f"fetch_info {symbol} ({market}): {e}")
        return {}


def fetch_history(symbol: str, market: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    try:
        t = ticker(symbol, market)
        df = t.history(period=period, interval=interval, auto_adjust=True)
        if df.empty and market.upper() == "TW":
            df = yf.Ticker(f"{symbol}.TWO").history(period=period, interval=interval, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index().rename(columns={
            "Date": "date", "Datetime": "date",
            "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        df["date"] = pd.to_datetime(df["date"])
        if getattr(df["date"].dt, "tz", None) is not None:
            df["date"] = df["date"].dt.tz_localize(None)
        return df[["date", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        _log.warning(f"fetch_history {symbol} ({market}): {e}")
        return pd.DataFrame()


def fetch_quarterly_income(symbol: str, market: str) -> pd.DataFrame:
    try:
        t = ticker(symbol, market)
        df = t.quarterly_income_stmt
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        _log.warning(f"fetch_quarterly_income {symbol} ({market}): {e}")
        return pd.DataFrame()


def fetch_annual_income(symbol: str, market: str) -> pd.DataFrame:
    try:
        t = ticker(symbol, market)
        df = t.income_stmt
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        _log.warning(f"fetch_annual_income {symbol} ({market}): {e}")
        return pd.DataFrame()


def fetch_analyst_targets(symbol: str, market: str) -> dict[str, Any]:
    """Return {'mean': .., 'high': .., 'low': .., 'count': ..} or {} on failure.

    yfinance exposes this via `.analyst_price_targets` for US; TW coverage is
    sparse so caller should fall back to empty.
    """
    try:
        t = ticker(symbol, market)
        targets = getattr(t, "analyst_price_targets", None)
        if isinstance(targets, dict) and targets:
            return {
                "mean":  targets.get("mean") or targets.get("current"),
                "high":  targets.get("high"),
                "low":   targets.get("low"),
                "count": targets.get("numberOfAnalysts") or 0,
            }
    except Exception as e:
        _log.warning(f"fetch_analyst_targets {symbol} ({market}): {e}")
    return {}


def fetch_recommendations(symbol: str, market: str) -> list[dict[str, Any]]:
    """Return recent analyst recommendation rows."""
    try:
        t = ticker(symbol, market)
        df = t.recommendations
        if df is None or df.empty:
            return []
        df = df.reset_index()
        rows = df.tail(10).to_dict(orient="records")
        return rows
    except Exception as e:
        _log.warning(f"fetch_recommendations {symbol} ({market}): {e}")
        return []
