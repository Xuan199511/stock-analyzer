"""Section 2: 基本面分析."""
from __future__ import annotations

from typing import Optional

import pandas as pd

from .schemas import Fundamental, HistoryPoint, PeerPE
from .sources import yf as yf_src


def _safe_num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:      # NaN check
            return None
        return f
    except (ValueError, TypeError):
        return None


def _annual_series(stmt: pd.DataFrame, keys: tuple[str, ...]) -> list[HistoryPoint]:
    """Pick the first matching row key from annual income stmt and build year-labelled points."""
    if stmt is None or stmt.empty:
        return []
    for k in keys:
        if k in stmt.index:
            row = stmt.loc[k]
            points: list[HistoryPoint] = []
            for col in sorted(row.index):
                v = _safe_num(row[col])
                if v is None:
                    continue
                year = getattr(col, "year", None) or str(col)[:4]
                points.append(HistoryPoint(period=str(year), value=round(v, 4)))
            return points[-5:]          # last 5 years
    return []


def _valuation_verdict(pe: Optional[float], peer_avg: Optional[float]) -> str:
    if pe is None or peer_avg is None or peer_avg <= 0:
        return "fair"
    ratio = pe / peer_avg
    if ratio < 0.8:
        return "undervalued"
    if ratio > 1.2:
        return "overvalued"
    return "fair"


def analyze_fundamental(symbol: str, market: str) -> Fundamental:
    info = yf_src.fetch_info(symbol, market)
    annual = yf_src.fetch_annual_income(symbol, market)

    eps_hist     = _annual_series(annual, ("Diluted EPS", "Basic EPS"))
    revenue_hist = _annual_series(annual, ("Total Revenue", "Operating Revenue"))

    pe      = _safe_num(info.get("trailingPE"))
    pe_ttm  = _safe_num(info.get("trailingPE"))      # yfinance exposes only trailingPE; treat as TTM
    pb      = _safe_num(info.get("priceToBook"))
    dyield  = _safe_num(info.get("dividendYield"))
    # yfinance ≥0.2.38 returns dividendYield as a percentage (e.g. 1.18 = 1.18 %);
    # normalise to a ratio (0.0118) so the frontend's pct:true formatter stays uniform.
    if dyield is not None and dyield > 1:
        dyield = dyield / 100
    gmar    = _safe_num(info.get("grossMargins"))
    omar    = _safe_num(info.get("operatingMargins"))
    nmar    = _safe_num(info.get("profitMargins"))
    roe     = _safe_num(info.get("returnOnEquity"))
    debt_eq = _safe_num(info.get("debtToEquity"))
    fcf     = _safe_num(info.get("freeCashflow"))

    # Peer PE is populated by Phase 4 (competitors); leave empty for now.
    peer = PeerPE()
    verdict = _valuation_verdict(pe, peer.avg)

    return Fundamental(
        eps_history=eps_hist,
        revenue_history=revenue_hist,
        gross_margin=gmar,
        operating_margin=omar,
        net_margin=nmar,
        roe=roe,
        pe_ratio=pe,
        pe_ttm=pe_ttm,
        pb_ratio=pb,
        dividend_yield=dyield,
        debt_ratio=debt_eq,
        free_cash_flow=fcf,
        peer_pe_comparison=peer,
        valuation_verdict=verdict,
    )
