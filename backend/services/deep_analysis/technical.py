"""Section 3: 技術面分析."""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from .schemas import MACDData, Technical, InstitutionalFlow
from .sources import yf as yf_src


# ── Pure-pandas indicator helpers (avoid pandas-ta → numba wheel build) ─────

def _sma(s: pd.Series, length: int) -> pd.Series:
    return s.rolling(length).mean()


def _rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(length).mean()
    loss  = (-delta.clip(upper=0)).rolling(length).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _stoch(high: pd.Series, low: pd.Series, close: pd.Series,
           k: int = 14, d: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    k_line = raw_k.rolling(smooth_k).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"k": k_line, "d": d_line})


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = close.ewm(span=fast,  adjust=False).mean()
    ema_slow = close.ewm(span=slow,  adjust=False).mean()
    line     = ema_fast - ema_slow
    sig      = line.ewm(span=signal, adjust=False).mean()
    hist     = line - sig
    return pd.DataFrame({"macd": line, "hist": hist, "signal": sig})


def _safe(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f or f in (float("inf"), float("-inf")):
            return None
        return round(f, 4)
    except (ValueError, TypeError):
        return None


def _ma_alignment(ma5, ma20, ma60, ma240) -> str:
    vals = [ma5, ma20, ma60, ma240]
    if any(v is None for v in vals):
        # graceful degrade when short histories lack MA240
        core = [ma5, ma20, ma60]
        if all(v is not None for v in core):
            if core[0] > core[1] > core[2]:
                return "bullish"
            if core[0] < core[1] < core[2]:
                return "bearish"
        return "mixed"
    if vals[0] > vals[1] > vals[2] > vals[3]:
        return "bullish"
    if vals[0] < vals[1] < vals[2] < vals[3]:
        return "bearish"
    return "mixed"


def _volume_status(df: pd.DataFrame) -> str:
    if len(df) < 20:
        return "normal"
    last = float(df["volume"].iloc[-1] or 0)
    avg20 = float(df["volume"].tail(20).mean() or 0)
    if avg20 <= 0:
        return "normal"
    ratio = last / avg20
    if ratio >= 1.5:
        return "heavy"
    if ratio <= 0.6:
        return "light"
    return "normal"


def _support_resistance(df: pd.DataFrame, window: int = 60, n: int = 3) -> tuple[list[float], list[float]]:
    """Pick the top-n swing lows (support) & highs (resistance) over the last `window` bars."""
    if len(df) < window:
        window = len(df)
    recent = df.tail(window).reset_index(drop=True)
    if recent.empty:
        return [], []

    # A simple swing detector: local extrema with radius 3 bars
    radius = 3
    lows, highs = [], []
    for i in range(radius, len(recent) - radius):
        window_slice = recent.iloc[i - radius:i + radius + 1]
        lo = float(recent["low"].iloc[i])
        hi = float(recent["high"].iloc[i])
        if lo == float(window_slice["low"].min()):
            lows.append(lo)
        if hi == float(window_slice["high"].max()):
            highs.append(hi)

    current = float(recent["close"].iloc[-1])
    supports    = sorted({round(x, 2) for x in lows if x < current}, reverse=True)[:n]
    resistances = sorted({round(x, 2) for x in highs if x > current})[:n]
    return supports, resistances


def analyze_technical(symbol: str, market: str, inst_flow: Optional[dict] = None) -> Technical:
    df = yf_src.fetch_history(symbol, market, period="1y", interval="1d")
    if df.empty or len(df) < 2:
        return Technical()

    close = df["close"].astype(float)
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)

    # Moving averages
    ma5   = _safe(_sma(close, 5).iloc[-1])     if len(close) >= 5   else None
    ma20  = _safe(_sma(close, 20).iloc[-1])    if len(close) >= 20  else None
    ma60  = _safe(_sma(close, 60).iloc[-1])    if len(close) >= 60  else None
    ma240 = _safe(_sma(close, 240).iloc[-1])   if len(close) >= 240 else None

    # Oscillators
    rsi = _safe(_rsi(close, 14).iloc[-1]) if len(close) >= 15 else None

    kd_k = kd_d = None
    if len(close) >= 14:
        stoch = _stoch(high, low, close)
        if not stoch.empty:
            kd_k = _safe(stoch["k"].iloc[-1])
            kd_d = _safe(stoch["d"].iloc[-1])

    macd_data = MACDData()
    if len(close) >= 35:
        md = _macd(close)
        if not md.empty:
            last = md.iloc[-1]
            macd_data = MACDData(
                macd=_safe(last["macd"]),
                signal=_safe(last["signal"]),
                hist=_safe(last["hist"]),
            )

    current = _safe(close.iloc[-1])
    prev    = _safe(close.iloc[-2]) if len(close) >= 2 else None
    pct_change = None
    if current is not None and prev:
        pct_change = round((current - prev) / prev * 100, 2)

    week52_high = _safe(high.tail(252).max())
    week52_low  = _safe(low.tail(252).min())

    supports, resistances = _support_resistance(df)

    flow = InstitutionalFlow(**inst_flow) if inst_flow else InstitutionalFlow()

    return Technical(
        current_price=current,
        price_change_pct=pct_change,
        week_52_high=week52_high,
        week_52_low=week52_low,
        ma5=ma5, ma20=ma20, ma60=ma60, ma240=ma240,
        ma_alignment=_ma_alignment(ma5, ma20, ma60, ma240),
        kd_k=kd_k, kd_d=kd_d,
        macd=macd_data,
        rsi=rsi,
        volume_status=_volume_status(df),
        support_levels=supports,
        resistance_levels=resistances,
        institutional_flow=flow,
    )
