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
    ma5  = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
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
        "ma5":  _to_list(dates, ma5),
        "ma10": _to_list(dates, ma10),
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


def calculate_sr(
    df: pd.DataFrame,
    window: int = 10,
    n_levels: int = 5,
    cluster_pct: float = 0.015,
) -> dict:
    """Find support and resistance levels via pivot-point clustering.

    Algorithm:
      1. Detect local high/low pivots: a bar is a pivot high if its high is the
         maximum over [i-window, i+window]; similarly for pivot lows.
      2. Cluster pivots within `cluster_pct` of each other (by price).
      3. Rank clusters by how many pivots they contain (= "strength").
      4. Return top `n_levels` resistance (above current price) and
         top `n_levels` support (below current price).

    Output:
      {
        "support":       [{"price": float, "strength": int}, ...],
        "resistance":    [{"price": float, "strength": int}, ...],
        "current_price": float,
      }
    """
    # Drop rows where OHLC has NaN to avoid corrupting pivot detection
    df = df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
    if len(df) < window * 2 + 1:
        return {"support": [], "resistance": [], "current_price": 0}

    high  = df["high"].values.astype(float)
    low   = df["low"].values.astype(float)
    close = df["close"].values.astype(float)
    n     = len(df)

    resistance_pivots: list[float] = []
    support_pivots:    list[float] = []

    for i in range(window, n - window):
        window_high = high[i - window : i + window + 1]
        window_low  = low[i  - window : i + window + 1]
        if high[i] >= window_high.max():
            resistance_pivots.append(high[i])
        if low[i] <= window_low.min():
            support_pivots.append(low[i])

    def _cluster(pivots: list[float]) -> list[dict]:
        if not pivots:
            return []
        pivots_sorted = sorted(pivots)
        groups: list[list[float]] = []
        group  = [pivots_sorted[0]]
        for p in pivots_sorted[1:]:
            if (p - group[0]) / group[0] <= cluster_pct:
                group.append(p)
            else:
                groups.append(group)
                group = [p]
        groups.append(group)
        return [
            {"price": round(float(np.mean(g)), 2), "strength": len(g)}
            for g in groups
        ]

    current_price = float(close[-1])
    threshold     = cluster_pct  # ±threshold around current price is "neutral zone"

    resistance = sorted(
        [r for r in _cluster(resistance_pivots) if r["price"] >= current_price * (1 - threshold)],
        key=lambda x: -x["strength"],
    )[:n_levels]

    support = sorted(
        [s for s in _cluster(support_pivots) if s["price"] <= current_price * (1 + threshold)],
        key=lambda x: -x["strength"],
    )[:n_levels]

    return {
        "support":       support,
        "resistance":    resistance,
        "current_price": round(current_price, 2),
    }
