"""SQLite-backed cache for StockAnalysisReport (TTL via expires_at)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, select

from db import db_session
from models.analysis_report import AnalysisReport
from services.deep_analysis.schemas import StockAnalysisReport

from .logging_config import logger

_TTL_HOURS = int(os.getenv("ANALYSIS_CACHE_TTL_HOURS", "4"))
_log = logger.bind(section="cache")


def get(symbol: str, market: str) -> Optional[StockAnalysisReport]:
    now = datetime.utcnow()
    with db_session() as s:
        stmt = (
            select(AnalysisReport)
            .where(AnalysisReport.symbol == symbol, AnalysisReport.market == market.upper())
            .order_by(AnalysisReport.created_at.desc())
            .limit(1)
        )
        row = s.execute(stmt).scalar_one_or_none()
        if row is None:
            _log.debug(f"MISS {symbol} ({market})")
            return None
        if row.expires_at < now:
            s.execute(delete(AnalysisReport).where(AnalysisReport.id == row.id))
            _log.info(f"EXPIRED {symbol} ({market}) — evicted")
            return None
        try:
            data = json.loads(row.report_json)
            report = StockAnalysisReport.model_validate(data)
            report.cached = True
            age_min = (now - row.created_at).total_seconds() / 60
            _log.info(f"HIT {symbol} ({market}) age={age_min:.1f}m")
            return report
        except Exception as e:
            _log.error(f"deserialize failed for {symbol}: {e}")
            return None


def put(report: StockAnalysisReport) -> None:
    expires = datetime.utcnow() + timedelta(hours=_TTL_HOURS)
    payload = report.model_dump(mode="json")
    payload["cached"] = False
    with db_session() as s:
        s.execute(
            delete(AnalysisReport).where(
                AnalysisReport.symbol == report.company.symbol,
                AnalysisReport.market == report.company.market.upper(),
            )
        )
        s.add(AnalysisReport(
            symbol=report.company.symbol,
            market=report.company.market.upper(),
            report_json=json.dumps(payload, ensure_ascii=False),
            created_at=datetime.utcnow(),
            expires_at=expires,
        ))
    _log.info(f"PUT {report.company.symbol} ({report.company.market}) expires={expires:%Y-%m-%d %H:%M}")


def cleanup_expired() -> int:
    """Delete all expired rows.  Returns number of rows removed."""
    now = datetime.utcnow()
    with db_session() as s:
        result = s.execute(delete(AnalysisReport).where(AnalysisReport.expires_at < now))
        removed = result.rowcount or 0
    if removed:
        _log.info(f"cleanup removed {removed} expired rows")
    return removed


def purge(symbol: Optional[str] = None, market: Optional[str] = None) -> int:
    """Purge cache entries.  With no args, drops the entire cache."""
    with db_session() as s:
        stmt = delete(AnalysisReport)
        if symbol:
            stmt = stmt.where(AnalysisReport.symbol == symbol.upper())
        if market:
            stmt = stmt.where(AnalysisReport.market == market.upper())
        result = s.execute(stmt)
        removed = result.rowcount or 0
    _log.warning(f"purge({symbol}, {market}) removed {removed} rows")
    return removed


def stats() -> dict:
    """Return counts for dashboards / admin endpoints."""
    now = datetime.utcnow()
    with db_session() as s:
        total   = s.execute(select(func.count(AnalysisReport.id))).scalar() or 0
        active  = s.execute(
            select(func.count(AnalysisReport.id)).where(AnalysisReport.expires_at >= now)
        ).scalar() or 0
        expired = total - active
        latest_row = s.execute(
            select(AnalysisReport.symbol, AnalysisReport.market, AnalysisReport.created_at)
            .order_by(AnalysisReport.created_at.desc())
            .limit(10)
        ).all()
    return {
        "total": total,
        "active": active,
        "expired": expired,
        "ttl_hours": _TTL_HOURS,
        "recent": [
            {"symbol": r.symbol, "market": r.market, "created_at": r.created_at.isoformat()}
            for r in latest_row
        ],
    }
