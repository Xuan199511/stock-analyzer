"""Deep-analysis REST endpoints."""
from fastapi import APIRouter, Query

from services.deep_analysis import cache as analysis_cache
from services.deep_analysis import service as analysis_service
from services.deep_analysis.schemas import StockAnalysisReport

router = APIRouter()


@router.get("/cache/stats")
def cache_stats():
    """Return cache size, TTL, and the 10 most recently cached reports."""
    return analysis_cache.stats()


@router.post("/cache/cleanup")
def cache_cleanup():
    """Evict all expired rows."""
    removed = analysis_cache.cleanup_expired()
    return {"removed": removed}


@router.delete("/cache")
def cache_purge(
    symbol: str | None = Query(None),
    market: str | None = Query(None, pattern="^(TW|US|tw|us)$"),
):
    """Drop cache entries.  No args → wipe entire cache."""
    removed = analysis_cache.purge(symbol=symbol, market=market)
    return {"removed": removed, "symbol": symbol, "market": market}


@router.get("/{symbol}", response_model=StockAnalysisReport)
async def get_analysis(
    symbol: str,
    market: str = Query("TW", pattern="^(TW|US|tw|us)$"),
    force_refresh: bool = Query(False),
):
    return await analysis_service.analyze_stock(symbol.upper(), market.upper(), force_refresh)
