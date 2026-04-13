"""
Vectorized backtesting engine — pandas / numpy.

Implements four long-only strategies:
  ma_cross  — Moving Average crossover (fast MA crosses slow MA)
  rsi       — RSI level-based (enter oversold zone, exit overbought zone)
  macd      — MACD / signal-line crossover
  bb        — Bollinger Band channel breakout (mean reversion)

All strategies are vectorized: signals are computed over the entire price
series in one pass, then a single O(n) loop simulates the portfolio.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from typing import Literal


# ── Request / Response models ─────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    symbol:          str
    market:          str                                             = "TW"
    strategy:        Literal["ma_cross", "rsi", "macd", "bb"]      = "ma_cross"
    params:          dict                                            = {}
    start_date:      str                                             = "2022-01-01"
    end_date:        str                                             = ""
    initial_capital: float = Field(default=100_000, gt=0)


# ── Default parameters per strategy ──────────────────────────────────────────

STRATEGY_DEFAULTS: dict[str, dict] = {
    "ma_cross": {"fast": 20,   "slow": 60},
    "rsi":      {"period": 14, "oversold": 30,  "overbought": 70},
    "macd":     {"fast": 12,   "slow": 26,       "signal": 9},
    "bb":       {"period": 20, "std_dev": 2.0},
}


# ── Signal generators ─────────────────────────────────────────────────────────

def _ma_cross(close: pd.Series, p: dict):
    """Golden/Death cross: fast MA vs slow MA crossover."""
    fast = int(p.get("fast", 20))
    slow = int(p.get("slow", 60))
    ma_f = close.rolling(fast).mean()
    ma_s = close.rolling(slow).mean()
    entries = (ma_f > ma_s) & (ma_f.shift(1) <= ma_s.shift(1))
    exits   = (ma_f < ma_s) & (ma_f.shift(1) >= ma_s.shift(1))
    return entries, exits


def _rsi(close: pd.Series, p: dict):
    """Enter when RSI dips into oversold; exit when RSI enters overbought."""
    period     = int(p.get("period",     14))
    oversold   = float(p.get("oversold",   30))
    overbought = float(p.get("overbought", 70))

    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))

    # Level-based (not crossover): enter on oversold, exit on overbought
    entries = rsi <= oversold
    exits   = rsi >= overbought
    return entries, exits


def _macd(close: pd.Series, p: dict):
    """MACD line crosses above / below signal line."""
    fast_p   = int(p.get("fast",   12))
    slow_p   = int(p.get("slow",   26))
    signal_p = int(p.get("signal",  9))

    ema_f  = close.ewm(span=fast_p,   adjust=False).mean()
    ema_s  = close.ewm(span=slow_p,   adjust=False).mean()
    macd   = ema_f - ema_s
    signal = macd.ewm(span=signal_p, adjust=False).mean()

    entries = (macd > signal) & (macd.shift(1) <= signal.shift(1))
    exits   = (macd < signal) & (macd.shift(1) >= signal.shift(1))
    return entries, exits


def _bb(close: pd.Series, p: dict):
    """Enter when price touches lower band; exit when price touches upper band."""
    period  = int(p.get("period",  20))
    std_dev = float(p.get("std_dev", 2.0))

    mid   = close.rolling(period).mean()
    std   = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std

    entries = close <= lower   # price at or below lower band
    exits   = close >= upper   # price at or above upper band
    return entries, exits


_STRATEGIES = {
    "ma_cross": _ma_cross,
    "rsi":      _rsi,
    "macd":     _macd,
    "bb":       _bb,
}


# ── Portfolio simulator ───────────────────────────────────────────────────────

def _simulate(
    close:           np.ndarray,
    dates:           list[str],
    entries:         pd.Series,
    exits:           pd.Series,
    initial_capital: float,
    commission:      float = 0.001425,   # ~0.1425 % per side (TW default)
) -> dict:
    """
    Long-only, full-capital-per-trade portfolio simulation.

    Rules:
    - Only one position at a time (no pyramiding).
    - 100 % of available cash is deployed on entry.
    - Commission is deducted from both entry (reduces shares acquired)
      and exit (reduces cash received).
    - If still in position at period end, force-close at last price.
    """
    n      = len(close)
    equity = np.empty(n, dtype=float)
    cash   = float(initial_capital)
    shares = 0.0

    in_pos       = False
    entry_price  = 0.0
    entry_date   = ""
    entry_cash   = 0.0   # portfolio value when we entered

    trades_list: list[dict] = []

    for i in range(n):
        price = float(close[i])
        date  = dates[i]

        if i > 0:    # no trades on first bar (insufficient history)
            if not in_pos and bool(entries.iloc[i]):
                # ── BUY ──────────────────────────────────────────────────────
                entry_cash  = cash
                shares      = cash * (1.0 - commission) / price
                cash        = 0.0
                in_pos      = True
                entry_price = price
                entry_date  = date

            elif in_pos and bool(exits.iloc[i]):
                # ── SELL ─────────────────────────────────────────────────────
                exit_cash = shares * price * (1.0 - commission)
                pnl       = exit_cash - entry_cash
                ret_pct   = (exit_cash / entry_cash - 1.0) * 100.0 if entry_cash else 0.0

                trades_list.append({
                    "entry_date":  entry_date,
                    "exit_date":   date,
                    "entry_price": round(entry_price, 4),
                    "exit_price":  round(price, 4),
                    "pnl":         round(pnl, 2),
                    "return_pct":  round(ret_pct, 2),
                })

                cash   = exit_cash
                shares = 0.0
                in_pos = False

        equity[i] = cash + shares * price

    # ── Force-close open position at period end ───────────────────────────────
    if in_pos:
        last_price = float(close[-1])
        exit_cash  = shares * last_price * (1.0 - commission)
        pnl        = exit_cash - entry_cash
        ret_pct    = (exit_cash / entry_cash - 1.0) * 100.0 if entry_cash else 0.0

        trades_list.append({
            "entry_date":  entry_date,
            "exit_date":   dates[-1],
            "entry_price": round(entry_price, 4),
            "exit_price":  round(last_price, 4),
            "pnl":         round(pnl, 2),
            "return_pct":  round(ret_pct, 2),
        })
        equity[-1] = exit_cash

    # ── Performance metrics ───────────────────────────────────────────────────
    total_return  = (equity[-1] / initial_capital - 1.0) * 100.0

    daily_ret     = np.diff(equity) / np.where(equity[:-1] != 0, equity[:-1], 1.0)
    std_dr        = float(np.std(daily_ret))
    sharpe        = float(np.mean(daily_ret) / std_dr * np.sqrt(252)) if std_dr > 1e-10 else 0.0

    running_max   = np.maximum.accumulate(equity)
    drawdowns     = (equity - running_max) / np.where(running_max > 0, running_max, 1.0)
    max_drawdown  = float(np.min(drawdowns) * 100.0)

    wins      = [t for t in trades_list if t["pnl"] > 0]
    win_rate  = (len(wins) / len(trades_list) * 100.0) if trades_list else 0.0

    equity_curve = [
        {"date": d, "value": round(float(v), 2)}
        for d, v in zip(dates, equity)
    ]

    return {
        "total_return":  round(total_return,  2),
        "win_rate":      round(win_rate,       2),
        "max_drawdown":  round(max_drawdown,   2),
        "sharpe_ratio":  round(sharpe,         3),
        "trade_count":   len(trades_list),
        "equity_curve":  equity_curve,
        "trades":        trades_list,
    }


# ── Public entry point ────────────────────────────────────────────────────────

def run(df: pd.DataFrame, req: BacktestRequest) -> dict:
    """
    Run a backtest on an OHLCV DataFrame.

    Args:
        df:  DataFrame with columns [date (datetime), open, high, low, close, volume].
        req: BacktestRequest with strategy, params, and capital.

    Returns:
        dict matching the /api/backtest response schema.
    """
    strategy_fn = _STRATEGIES.get(req.strategy)
    if strategy_fn is None:
        raise ValueError(f"Unknown strategy: {req.strategy!r}")

    # Merge user params over defaults so omitted fields keep sensible values
    merged_params = {**STRATEGY_DEFAULTS.get(req.strategy, {}), **req.params}

    close = df["close"]
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()

    entries, exits = strategy_fn(close, merged_params)

    return _simulate(
        close.values,
        dates,
        entries.fillna(False),
        exits.fillna(False),
        req.initial_capital,
    )
