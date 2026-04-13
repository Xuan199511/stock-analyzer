"""Backtest endpoint — POST /api/backtest."""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from services import finmind, yfinance_service
from services.backtest_engine import BacktestRequest, run as run_backtest

router = APIRouter()


@router.post("")
async def backtest(req: BacktestRequest):
    """
    Run a vectorized backtest on historical OHLCV data.

    Strategies: ma_cross | rsi | macd | bb
    Returns: total_return, win_rate, max_drawdown, sharpe_ratio,
             trade_count, equity_curve, trades
    """
    mkt = req.market.strip().lower()
    sym = req.symbol.upper()

    end_date   = req.end_date or datetime.today().strftime("%Y-%m-%d")
    start_date = req.start_date

    try:
        if mkt == "tw":
            df = await finmind.get_stock_price(sym, start_date, end_date)
        else:
            df = yfinance_service.get_stock_price(sym, start_date, end_date)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"資料獲取失敗: {e}")

    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"找不到 {sym}（{req.market}）的資料")

    try:
        result = run_backtest(df, req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回測執行失敗: {e}")

    return result
