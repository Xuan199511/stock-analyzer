"""Deep analysis orchestrator.

Phase 4 adds competitors, moat, institutional.
Phase 5 adds sentiment + AI conclusion (Claude).
Phase 6 adds structured logging, timing, cleaned-up error capture.
"""
from __future__ import annotations

import asyncio
import inspect
import os
import time
from datetime import datetime
from typing import Any

import httpx

from .schemas import (
    AIConclusion,
    CompanyBasic,
    Competitor,
    ConsensusTarget,
    Fundamental,
    Moat,
    PartialError,
    Sentiment,
    StockAnalysisReport,
    Technical,
)
from . import (
    cache, company, competitors, conclusion,
    fundamental, institutional, moat, sentiment as sentiment_mod, technical,
)
from . import llm
from .logging_config import logger
from .sources import finmind_ext, yf as yf_src

_log = logger.bind(section="orchestrator")


def _extract_status(e: Exception) -> int | None:
    """Best-effort HTTP status extraction from varied exception shapes."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code
    status = getattr(e, "status_code", None)
    if status is None:
        resp = getattr(e, "response", None)
        status = getattr(resp, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


async def _await_safe(section: str, awaitable: Any, errors: list[PartialError]) -> Any:
    """Await a future/coroutine; record exceptions instead of raising."""
    try:
        if inspect.isawaitable(awaitable):
            return await awaitable
        return awaitable
    except Exception as e:
        err = PartialError(
            section=section,
            error=f"{type(e).__name__}: {e}",
            status_code=_extract_status(e),
            occurred_at=datetime.utcnow(),
        )
        errors.append(err)
        _log.warning(f"section={section} failed: {err.error} status={err.status_code}")
        return None


async def analyze_stock(symbol: str, market: str = "TW", force_refresh: bool = False) -> StockAnalysisReport:
    market = market.upper()
    t_start = time.perf_counter()
    _log.info(f"BEGIN {symbol} ({market}) force_refresh={force_refresh}")

    if not force_refresh:
        cached = cache.get(symbol, market)
        if cached is not None:
            dt = time.perf_counter() - t_start
            _log.info(f"CACHED {symbol} ({market}) served in {dt*1000:.0f}ms")
            return cached

    errors: list[PartialError] = []
    data_sources: list[str] = ["yfinance"]

    loop = asyncio.get_running_loop()

    company_fut      = loop.run_in_executor(None, company.analyze_company,         symbol, market)
    fundamental_fut  = loop.run_in_executor(None, fundamental.analyze_fundamental, symbol, market)
    competitors_fut  = loop.run_in_executor(None, competitors.analyze_competitors, symbol, market)
    inst_targets_fut = loop.run_in_executor(None, institutional.analyze_institutional_targets, symbol, market)
    consensus_fut    = loop.run_in_executor(None, institutional.analyze_consensus,              symbol, market)

    inst_flow_awaitable = None
    if market == "TW":
        data_sources.append("finmind")
        inst_flow_awaitable = finmind_ext.total_institutional_flow(symbol, days=5)

    company_obj     = await _await_safe("company",            company_fut,     errors)
    fundamental_obj = await _await_safe("fundamental",        fundamental_fut, errors)
    competitors_obj = await _await_safe("competitors",        competitors_fut, errors) or []
    inst_targets    = await _await_safe("institutional_targets", inst_targets_fut, errors) or []
    consensus_obj   = await _await_safe("consensus_target",   consensus_fut,   errors) or ConsensusTarget()
    inst_flow       = await _await_safe("institutional_flow", inst_flow_awaitable, errors) \
                        if inst_flow_awaitable is not None else None

    technical_fut = loop.run_in_executor(None, technical.analyze_technical, symbol, market, inst_flow)
    technical_obj = await _await_safe("technical", technical_fut, errors)

    company_obj     = company_obj     or CompanyBasic(symbol=symbol, name=symbol, market=market, industry="N/A")
    fundamental_obj = fundamental_obj or Fundamental()
    technical_obj   = technical_obj   or Technical()

    try:
        fundamental_obj.peer_pe_comparison = competitors.peer_pe(competitors_obj, fundamental_obj.pe_ratio)
        peer_avg = fundamental_obj.peer_pe_comparison.avg
        own_pe   = fundamental_obj.pe_ratio
        if peer_avg and own_pe and peer_avg > 0:
            ratio = own_pe / peer_avg
            fundamental_obj.valuation_verdict = (
                "undervalued" if ratio < 0.8 else "overvalued" if ratio > 1.2 else "fair"
            )
    except Exception as e:
        errors.append(PartialError(
            section="peer_pe", error=f"{type(e).__name__}: {e}",
            status_code=_extract_status(e), occurred_at=datetime.utcnow(),
        ))
        _log.warning(f"peer_pe post-process failed: {e}")

    try:
        own_mcap = None
        try:
            info = yf_src.fetch_info(symbol, market) or {}
            own_mcap = float(info["marketCap"]) if info.get("marketCap") is not None else None
        except Exception:
            own_mcap = None
        moat_obj = moat.analyze_moat(company_obj, fundamental_obj, competitors_obj, own_mcap)
    except Exception as e:
        errors.append(PartialError(
            section="moat", error=f"{type(e).__name__}: {e}",
            status_code=_extract_status(e), occurred_at=datetime.utcnow(),
        ))
        _log.warning(f"moat failed: {e}")
        moat_obj = Moat()

    if os.getenv("NEWS_API_KEY"):
        data_sources.append("newsapi")
    if llm.available():
        data_sources.append("claude")

    sentiment_obj = await _await_safe(
        "sentiment",
        sentiment_mod.analyze_sentiment(symbol, market, name=company_obj.name),
        errors,
    ) or Sentiment()

    ai_conclusion = await _await_safe(
        "ai_conclusion",
        conclusion.analyze_conclusion(
            company_obj, fundamental_obj, technical_obj,
            competitors_obj, moat_obj, sentiment_obj, consensus_obj,
        ),
        errors,
    ) or AIConclusion()

    report = StockAnalysisReport(
        company=company_obj,
        fundamental=fundamental_obj,
        technical=technical_obj,
        sentiment=sentiment_obj,
        competitors=competitors_obj,
        moat=moat_obj,
        institutional_targets=inst_targets,
        consensus_target=consensus_obj,
        ai_conclusion=ai_conclusion,
        generated_at=datetime.utcnow(),
        data_sources=sorted(set(data_sources)),
        errors=errors,
        cached=False,
    )

    try:
        cache.put(report)
    except Exception as e:
        _log.error(f"cache.put failed: {e}")

    dt = time.perf_counter() - t_start
    _log.info(
        f"DONE {symbol} ({market}) {dt:.2f}s · sources={report.data_sources} · "
        f"errors={len(errors)}"
    )
    return report
