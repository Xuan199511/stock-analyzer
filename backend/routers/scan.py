"""Signal scanner endpoint — GET /api/scan."""
from fastapi import APIRouter, Query

from services import scanner

router = APIRouter()


@router.get("")
async def scan(
    market: str = Query("ALL", description="TW | US | ALL"),
):
    """
    Scan the watchlist for active trading signals.

    Returns a flat list of scan results sorted by signal strength
    (BUY/SELL first, then NONE).

    Result item schema:
        symbol, name, market, price, change_pct,
        signal ("BUY"|"SELL"|"NONE"), strength ("strong"|"moderate"|"weak"|""),
        strategies (list[str])
    """
    mkt = market.strip().upper()

    if mkt == "TW":
        results = await scanner.scan_market("TW")
    elif mkt == "US":
        results = await scanner.scan_market("US")
    else:
        combined = await scanner.scan_all()
        results  = combined["TW"] + combined["US"]

    # Sort: BUY first, then SELL, then NONE; within each group strong → weak
    order = {"BUY": 0, "SELL": 1, "NONE": 2}
    strength_order = {"strong": 0, "moderate": 1, "weak": 2, "": 3}

    results.sort(
        key=lambda r: (order[r["signal"]], strength_order[r["strength"]])
    )
    return results
