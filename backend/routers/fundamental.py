"""Basic fundamental data endpoints (EPS, P/E, financial statements)."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta

from services import finmind, yfinance_service

router = APIRouter()


@router.get("/{symbol}")
async def get_fundamental(
    symbol: str,
    market: str = Query("tw", enum=["tw", "us"]),
):
    """Return fundamental data for the given symbol."""
    if market == "us":
        data = yfinance_service.get_fundamental(symbol)
        if "error" in data and len(data) == 2:
            raise HTTPException(status_code=404, detail=data["error"])
        return {"symbol": symbol, "market": "us", "data": data}

    # Taiwan stock — aggregate from FinMind
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")

    per_data, fs_data, rev_data = await _gather_tw(symbol, start_date, end_date)

    # Latest PER entry
    per_latest = per_data[-1] if per_data else {}

    # EPS from financial statements (type == "EPS")
    eps_records = [r for r in fs_data if r.get("type") == "EPS"]
    eps_latest = eps_records[-1] if eps_records else {}

    # Revenue trend (last 12 months)
    rev_trend = rev_data[-12:] if rev_data else []

    return {
        "symbol": symbol,
        "market": "tw",
        "data": {
            "symbol": symbol,
            "pe_ratio": per_latest.get("PER"),
            "pb_ratio": per_latest.get("PBR"),
            "dividend_yield": per_latest.get("DividendYield"),
            "eps": eps_latest.get("value"),
            "eps_date": eps_latest.get("date"),
            "financial_statements": fs_data[-40:],   # last ~10 quarters
            "revenue_trend": rev_trend,
            "per_history": per_data[-60:],
        },
    }


async def _gather_tw(symbol: str, start_date: str, end_date: str):
    import asyncio
    per_task = finmind.get_per(symbol, start_date, end_date)
    fs_task = finmind.get_financial_statements(symbol, start_date, end_date)
    rev_task = finmind.get_monthly_revenue(symbol, start_date, end_date)
    return await asyncio.gather(per_task, fs_task, rev_task)
