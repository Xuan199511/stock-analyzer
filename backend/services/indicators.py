"""Technical indicator calculations — pure pandas / numpy, no extra deps.

Output contract (used by both /kline+/indicators and legacy /candles):
  {
    "ma20":  [{date, value}, ...],
    "ma60":  [{date, value}, ...],
    "rsi":   [{date, value}, ...],
    "macd":  {"line": [...], "signal": [...], "hist": [...]},
    "bb":    {"upper": [...], "mid": [...], "lower": [...]},
  }
"""
import numpy as np
import pandas as pd


def _to_list(dates: pd.Series, values: pd.Series) -> list[dict]:
    return [
        {"date": str(d)[:10], "value": round(float(v), 4)}
        for d, v in zip(dates, values)
        if pd.notna(v)
    ]


def calculate_indicators(df: pd.DataFrame) -> dict:
    close = df["close"]
    dates = df["date"]

    # ── Moving Averages ──────────────────────────────────────────────────────
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    # ── RSI(14) ──────────────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    # ── MACD(12, 26, 9) ──────────────────────────────────────────────────────
    ema12       = close.ewm(span=12, adjust=False).mean()
    ema26       = close.ewm(span=26, adjust=False).mean()
    macd_line   = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist   = macd_line - macd_signal

    # ── Bollinger Bands(20, 2) ───────────────────────────────────────────────
    bb_mid   = close.rolling(20).mean()
    bb_std   = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    return {
        "ma20": _to_list(dates, ma20),
        "ma60": _to_list(dates, ma60),
        "rsi":  _to_list(dates, rsi),
        "macd": {
            "line":   _to_list(dates, macd_line),
            "signal": _to_list(dates, macd_signal),
            "hist":   _to_list(dates, macd_hist),
        },
        "bb": {
            "upper": _to_list(dates, bb_upper),
            "mid":   _to_list(dates, bb_mid),
            "lower": _to_list(dates, bb_lower),
        },
    }


# Alias kept so the legacy /candles endpoint still works.
calculate_all = calculate_indicators
