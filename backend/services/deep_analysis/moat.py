"""Section 7: 獨佔性與護城河.

Heuristic 1-5 scoring across 5 moat dimensions derived from fundamentals +
industry keywords.  Phase 5 LLM can later rewrite the ``narrative`` field.
"""
from __future__ import annotations

from .schemas import CompanyBasic, Competitor, Fundamental, Moat


def _clip(v: int) -> int:
    return max(1, min(5, v))


def _industry_keywords(company: CompanyBasic) -> str:
    """Combined lowercase industry + sub_industry + description."""
    parts = [company.industry or "", company.sub_industry or "", company.description or ""]
    return " ".join(p.lower() for p in parts)


def _score_technical(fund: Fundamental, kw: str) -> int:
    """Gross margin + ROE + high-tech industry bonus."""
    s = 1
    if fund.gross_margin and fund.gross_margin >= 0.5:   s += 2
    elif fund.gross_margin and fund.gross_margin >= 0.35: s += 1
    if fund.roe and fund.roe >= 0.2:                      s += 1
    if any(k in kw for k in ("semiconductor", "software", "biotech", "pharma", "aerospace", "半導體", "生技")):
        s += 1
    return _clip(s)


def _score_certification(fund: Fundamental, kw: str) -> int:
    """Regulated / high-barrier industries + operating-margin signal."""
    s = 1
    if any(k in kw for k in (
        "medical", "healthcare", "pharmaceutical", "automotive", "aerospace", "defense",
        "financial", "bank", "insurance", "醫療", "製藥", "汽車", "航太", "金融"
    )):
        s += 2
    if fund.operating_margin and fund.operating_margin >= 0.25:
        s += 1
    if fund.net_margin and fund.net_margin >= 0.15:
        s += 1
    return _clip(s)


def _score_scale(fund: Fundamental, competitors: list[Competitor], own_mcap: float | None) -> int:
    """Scale economy — market-cap percentile among peers + revenue size."""
    s = 1
    peer_mcaps = [c.market_cap for c in competitors if c.market_cap]
    if own_mcap and peer_mcaps:
        bigger_than = sum(1 for m in peer_mcaps if own_mcap >= m)
        pct = bigger_than / len(peer_mcaps)
        if pct >= 0.75: s += 2
        elif pct >= 0.5: s += 1
    if fund.revenue_history:
        last_rev = fund.revenue_history[-1].value
        if last_rev >= 1e11:        s += 2      # ≥ 100B
        elif last_rev >= 1e10:      s += 1      # ≥ 10B
    return _clip(s)


def _score_switching(fund: Fundamental, kw: str) -> int:
    """Switching cost — recurring-revenue industries + high net margin."""
    s = 1
    if any(k in kw for k in (
        "software", "saas", "cloud", "platform", "enterprise", "subscription",
        "financial", "bank", "insurance", "雲端", "平台", "訂閱"
    )):
        s += 2
    if fund.net_margin and fund.net_margin >= 0.2:
        s += 1
    if fund.roe and fund.roe >= 0.25:
        s += 1
    return _clip(s)


def _score_network(kw: str) -> int:
    """Network-effect proxies — platform/marketplace/social keywords."""
    s = 1
    if any(k in kw for k in (
        "platform", "marketplace", "social", "network", "exchange", "ecosystem",
        "community", "advertising", "payment", "交易所", "支付", "社群"
    )):
        s += 2
    if any(k in kw for k in ("search", "operating system", "browser")):
        s += 1
    return _clip(s)


def _replaceability(overall: float) -> str:
    if overall >= 4.2:  return "near_monopoly"
    if overall >= 3.2:  return "hard"
    if overall >= 2.2:  return "partial"
    return "easily"


def analyze_moat(
    company: CompanyBasic,
    fundamental: Fundamental,
    competitors: list[Competitor],
    market_cap: float | None = None,
) -> Moat:
    kw = _industry_keywords(company)

    tech  = _score_technical(fundamental, kw)
    cert  = _score_certification(fundamental, kw)
    scale = _score_scale(fundamental, competitors, market_cap)
    swch  = _score_switching(fundamental, kw)
    net   = _score_network(kw)

    overall = round((tech + cert + scale + swch + net) / 5, 2)

    return Moat(
        technical_barrier=tech,
        certification_barrier=cert,
        scale_economy=scale,
        switching_cost=swch,
        network_effect=net,
        overall_score=overall,
        replaceability=_replaceability(overall),
        narrative="",
    )
