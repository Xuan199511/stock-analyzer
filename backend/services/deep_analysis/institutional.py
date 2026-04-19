"""Section 8: 外資與法人目標價.

yfinance analyst_price_targets + recommendations.  Taiwan coverage is
sparse — TW symbols typically return empty, in which case we return an empty
list and a ConsensusTarget with count=0.  A future scraper can plug into
``analyze_institutional_targets`` without changing callers.
"""
from __future__ import annotations

from typing import Optional

from .schemas import ConsensusTarget, InstitutionalTarget
from .sources import yf as yf_src


def _safe_num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:
            return None
        return f
    except (ValueError, TypeError):
        return None


def _normalize_rating(raw: str) -> str:
    r = (raw or "").lower()
    if any(k in r for k in ("buy", "outperform", "overweight", "strong")):
        return "buy"
    if any(k in r for k in ("sell", "underperform", "underweight")):
        return "sell"
    return "hold"


def analyze_consensus(symbol: str, market: str) -> ConsensusTarget:
    targets = yf_src.fetch_analyst_targets(symbol, market)
    if not targets:
        return ConsensusTarget()
    return ConsensusTarget(
        avg=_safe_num(targets.get("mean")),
        high=_safe_num(targets.get("high")),
        low=_safe_num(targets.get("low")),
        count=int(targets.get("count") or 0),
    )


def analyze_institutional_targets(symbol: str, market: str) -> list[InstitutionalTarget]:
    recs = yf_src.fetch_recommendations(symbol, market)
    if not recs:
        return []

    out: list[InstitutionalTarget] = []
    for r in recs[-6:]:                          # last 6 rows ≈ 3-6 months
        firm = r.get("Firm") or r.get("firm") or ""
        to_grade = r.get("To Grade") or r.get("toGrade") or r.get("Rating") or ""
        raw_date = r.get("Date") or r.get("date") or r.get("period")
        date_str: Optional[str] = None
        if raw_date is not None:
            try:
                date_str = str(raw_date)[:10]
            except Exception:
                date_str = None

        if not firm:
            continue

        out.append(InstitutionalTarget(
            broker=str(firm)[:40],
            rating=_normalize_rating(str(to_grade)),
            target_price=None,                    # yfinance doesn't expose per-row price
            report_date=date_str,
            key_assumptions=None,
        ))
    return out
