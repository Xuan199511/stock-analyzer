"""Section 5: 競爭對手比較.

Resolves a peer list for the given symbol from a curated JSON map, falls back
to yfinance `info['recommendationSymbols']`/industry heuristics, then fetches
each peer's key metrics via yfinance.  Returns up to 4 peers (excluding self).
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .schemas import Competitor, PeerPE
from .sources import yf as yf_src


_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "competitors.json")
_MAX_PEERS = 4


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


def _load_peer_map() -> dict[str, dict[str, list[str]]]:
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[competitors] failed to load peer map: {e}")
        return {"TW": {}, "US": {}}


def _peers_from_yf(symbol: str, market: str) -> list[str]:
    """Fallback: yfinance `recommendationSymbols` or similar."""
    info = yf_src.fetch_info(symbol, market)
    for key in ("recommendationSymbols", "peerSymbols"):
        syms = info.get(key) or []
        if syms:
            cleaned: list[str] = []
            for s in syms:
                s = str(s).split(".")[0].upper()
                if s and s != symbol.upper():
                    cleaned.append(s)
            if cleaned:
                return cleaned[:_MAX_PEERS]
    return []


def resolve_peers(symbol: str, market: str) -> list[str]:
    m = _load_peer_map()
    mkt_map = m.get(market.upper(), {})
    peers = mkt_map.get(symbol.upper(), [])
    if peers:
        return [p for p in peers if p.upper() != symbol.upper()][:_MAX_PEERS]
    return _peers_from_yf(symbol, market)


def _peer_metrics(symbol: str, market: str) -> Optional[Competitor]:
    info = yf_src.fetch_info(symbol, market)
    if not info:
        return None
    return Competitor(
        symbol=symbol,
        name=info.get("shortName") or info.get("longName") or symbol,
        market_cap=_safe_num(info.get("marketCap")),
        revenue=_safe_num(info.get("totalRevenue")),
        gross_margin=_safe_num(info.get("grossMargins")),
        eps=_safe_num(info.get("trailingEps")),
        pe_ratio=_safe_num(info.get("trailingPE")),
        market_share=None,
    )


def analyze_competitors(symbol: str, market: str) -> list[Competitor]:
    peers = resolve_peers(symbol, market)
    out: list[Competitor] = []
    for p in peers[:_MAX_PEERS]:
        try:
            row = _peer_metrics(p, market)
            if row:
                out.append(row)
        except Exception as e:
            print(f"[competitors] skip {p}: {e}")
            continue
    return out


def peer_pe(competitors: list[Competitor], own_pe: Optional[float]) -> PeerPE:
    pes = [c.pe_ratio for c in competitors if c.pe_ratio is not None and c.pe_ratio > 0]
    if not pes:
        return PeerPE()
    avg = sum(pes) / len(pes)
    percentile: Optional[float] = None
    if own_pe is not None and own_pe > 0:
        below = sum(1 for p in pes if p < own_pe)
        percentile = round(below / len(pes) * 100, 1)
    return PeerPE(avg=round(avg, 2), percentile=percentile)
