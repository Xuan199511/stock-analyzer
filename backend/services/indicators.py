"""Technical indicator calculations via pandas-ta.

Output contract (used by both /kline+/indicators and legacy /candles):
  {
    "ma20":  [{date, value}, ...],
    "ma60":  [{date, value}, ...],
    "rsi":   [{date, value}, ...],
    "macd":  {"line": [...], "signal": [...], "hist": [...]},
    "bb":    {"upper": [...], "mid": [...], "lower": [...]},
  }
"""
import pandas as pd
import pandas_ta as ta


def _to_list(dates: pd.Series, values: pd.Series) -> list[dict]:
    """Zip dates + values into [{date, value}], dropping NaN rows."""
    return [
        {"date": str(d)[:10], "value": round(float(v), 4)}
        for d, v in zip(dates, values)
        if pd.notna(v)
    ]


def calculate_indicators(df: pd.DataFrame) -> dict:
    """
    Calculate MA20, MA60, RSI(14), MACD(12,26,9), BB(20,2) from a DataFrame
    with columns: date, open, high, low, close, volume.
    """
    close = df["close"]
    dates = df["date"]

    # ── Moving Averages ──────────────────────────────────────────────────────
    ma20 = ta.sma(close, length=20)
    ma60 = ta.sma(close, length=60)

    # ── RSI ──────────────────────────────────────────────────────────────────
    rsi = ta.rsi(close, length=14)

    # ── MACD ─────────────────────────────────────────────────────────────────
    # pandas-ta returns: MACD_12_26_9 | MACDh_12_26_9 | MACDs_12_26_9
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    macd_line   = macd_df.iloc[:, 0]   # MACD_12_26_9
    macd_hist   = macd_df.iloc[:, 1]   # MACDh_12_26_9
    macd_signal = macd_df.iloc[:, 2]   # MACDs_12_26_9

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    # pandas-ta returns: BBL_20_2.0 | BBM_20_2.0 | BBU_20_2.0 | BBB | BBP
    bb_df  = ta.bbands(close, length=20, std=2)
    bb_lower  = bb_df.iloc[:, 0]   # BBL
    bb_mid    = bb_df.iloc[:, 1]   # BBM
    bb_upper  = bb_df.iloc[:, 2]   # BBU

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


# Alias kept so the legacy /candles endpoint still works without changes.
calculate_all = calculate_indicators
