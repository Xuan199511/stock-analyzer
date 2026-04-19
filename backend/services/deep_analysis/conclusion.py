"""Section 9: 綜合結論與操作建議 (+ SWOT).

給 Claude 一份上游全部資料的精簡 JSON，輸出投資亮點/風險/SWOT/
短中長期看法/進場區/停損 — 不可用時退化成規則式建議。
"""
from __future__ import annotations

from typing import Any

from .llm import available as llm_available, call_json
from .logging_config import logger
from .schemas import (
    AIConclusion,
    CompanyBasic,
    Competitor,
    ConsensusTarget,
    EntryRange,
    Fundamental,
    Moat,
    Sentiment,
    SWOT,
    Technical,
)

_log = logger.bind(section="conclusion")


def _pack_context(
    company: CompanyBasic,
    fundamental: Fundamental,
    technical: Technical,
    competitors: list[Competitor],
    moat: Moat,
    sentiment: Sentiment,
    consensus: ConsensusTarget,
) -> dict[str, Any]:
    return {
        "company": {
            "symbol": company.symbol, "name": company.name,
            "industry": company.industry, "sub_industry": company.sub_industry,
            "description": (company.description or "")[:300],
        },
        "fundamental": {
            "pe": fundamental.pe_ratio, "pb": fundamental.pb_ratio,
            "dividend_yield": fundamental.dividend_yield, "roe": fundamental.roe,
            "gross_margin": fundamental.gross_margin, "operating_margin": fundamental.operating_margin,
            "net_margin": fundamental.net_margin,
            "eps_history": [p.model_dump() for p in fundamental.eps_history],
            "revenue_history": [p.model_dump() for p in fundamental.revenue_history],
            "peer_pe_avg": fundamental.peer_pe_comparison.avg,
            "valuation_verdict": fundamental.valuation_verdict,
        },
        "technical": {
            "current_price": technical.current_price,
            "price_change_pct": technical.price_change_pct,
            "ma5": technical.ma5, "ma20": technical.ma20, "ma60": technical.ma60, "ma240": technical.ma240,
            "ma_alignment": technical.ma_alignment,
            "rsi": technical.rsi, "kd_k": technical.kd_k, "kd_d": technical.kd_d,
            "macd_hist": technical.macd.hist,
            "volume_status": technical.volume_status,
            "week_52_high": technical.week_52_high, "week_52_low": technical.week_52_low,
            "support_levels": technical.support_levels,
            "resistance_levels": technical.resistance_levels,
            "institutional_flow": technical.institutional_flow.model_dump(),
        },
        "competitors": [
            {"symbol": c.symbol, "name": c.name, "pe": c.pe_ratio, "gross_margin": c.gross_margin}
            for c in competitors[:5]
        ],
        "moat": moat.model_dump(),
        "sentiment": {
            "media_tone": sentiment.media_tone,
            "tone_score": sentiment.tone_score,
            "hot_topics": sentiment.hot_topics,
            "key_catalysts": sentiment.key_catalysts,
            "key_risks": sentiment.key_risks,
            "margin_change": sentiment.margin_trading_change.model_dump(),
        },
        "consensus_target": consensus.model_dump(),
    }


def _rule_fallback(
    fundamental: Fundamental,
    technical: Technical,
    moat: Moat,
) -> AIConclusion:
    """Deterministic fallback when Claude is unavailable."""
    highlights: list[str] = []
    risks: list[str] = []

    if fundamental.roe and fundamental.roe >= 0.2:
        highlights.append(f"ROE {fundamental.roe * 100:.1f}% 表現優異，顯示獲利能力強。")
    if fundamental.gross_margin and fundamental.gross_margin >= 0.4:
        highlights.append(f"毛利率 {fundamental.gross_margin * 100:.1f}%，產品競爭力佳。")
    if fundamental.valuation_verdict == "undervalued":
        highlights.append("目前評價相對同業偏低，有補漲空間。")
    if moat.overall_score >= 4:
        highlights.append(f"護城河綜合評分 {moat.overall_score}/5，競爭優勢明顯。")

    if technical.rsi and technical.rsi >= 75:
        risks.append(f"RSI {technical.rsi:.0f} 已進入超買區，短線需留意回檔。")
    if fundamental.valuation_verdict == "overvalued":
        risks.append("目前評價相對同業偏高，估值壓力存在。")
    if fundamental.debt_ratio and fundamental.debt_ratio >= 100:
        risks.append(f"負債比 {fundamental.debt_ratio:.0f}%，財務槓桿偏高。")
    if technical.ma_alignment == "bearish":
        risks.append("均線呈空頭排列，趨勢轉弱。")

    # Entry / stop — based on nearest support + ATR-like 5% rule
    entry = EntryRange()
    stop = None
    if technical.support_levels and technical.current_price:
        s = technical.support_levels[0]
        entry = EntryRange(low=round(s * 0.98, 2), high=round(s * 1.02, 2))
        stop = round(s * 0.95, 2)

    short_view = "均線偏多，短線可觀察壓力突破。" if technical.ma_alignment == "bullish" \
                 else "技術面偏弱，短線以防守為主。"
    mid_view = "基本面穩健，中期持續觀察營收動能。" if fundamental.roe and fundamental.roe >= 0.15 \
               else "中期需關注獲利改善幅度。"
    long_view = "長期具備產業地位與護城河優勢。" if moat.overall_score >= 3.5 \
                else "長期競爭優勢有限，需審慎布局。"

    return AIConclusion(
        highlights=highlights[:3],
        risks=risks[:3],
        swot=SWOT(),
        short_term_view=short_view,
        mid_term_view=mid_view,
        long_term_view=long_view,
        entry_range=entry,
        stop_loss=stop,
        investor_profile="moderate",
    )


async def analyze_conclusion(
    company: CompanyBasic,
    fundamental: Fundamental,
    technical: Technical,
    competitors: list[Competitor],
    moat: Moat,
    sentiment: Sentiment,
    consensus: ConsensusTarget,
) -> AIConclusion:
    if not llm_available():
        return _rule_fallback(fundamental, technical, moat)

    ctx = _pack_context(company, fundamental, technical, competitors, moat, sentiment, consensus)

    import json
    prompt = f"""你是資深股票分析師，請以繁體中文針對以下股票產出綜合結論。

資料：
```json
{json.dumps(ctx, ensure_ascii=False, indent=2)}
```

請回傳 JSON，所有字串用繁體中文：
{{
  "highlights":       ["亮點1", "亮點2", "亮點3"],       // 正好 3 個，每個 ≤ 40 字
  "risks":            ["風險1", "風險2", "風險3"],       // 正好 3 個，每個 ≤ 40 字
  "swot": {{
    "strengths":     ["優勢1", "優勢2", ...],            // 2-4 個
    "weaknesses":    ["劣勢1", "劣勢2", ...],            // 2-4 個
    "opportunities": ["機會1", "機會2", ...],            // 2-4 個
    "threats":       ["威脅1", "威脅2", ...]             // 2-4 個
  }},
  "short_term_view":  "短線（1-3 個月）看法，≤ 80 字",
  "mid_term_view":    "中期（3-12 個月）看法，≤ 80 字",
  "long_term_view":   "長期（1-3 年）看法，≤ 80 字",
  "entry_range":      {{"low": <建議進場區下緣>, "high": <建議進場區上緣>}},
  "stop_loss":        <停損價>,
  "investor_profile": "conservative" | "moderate" | "aggressive"
}}

注意：
- entry_range 與 stop_loss 須合理參考目前價 {technical.current_price} 與支撐區 {technical.support_levels}。
- 若資料嚴重不足（例如沒有基本面），將 highlights/risks 限制為實際可驗證的結論，不要編造數字。"""

    try:
        result = await call_json(prompt, max_tokens=2500)
    except Exception as e:
        _log.warning(f"Claude conclusion failed for {company.symbol}: {e}")
        return _rule_fallback(fundamental, technical, moat)

    def _str_list(key: str, lo: int, hi: int) -> list[str]:
        arr = result.get(key) or []
        return [str(x) for x in arr if x][:hi]

    swot_raw = result.get("swot") or {}
    swot = SWOT(
        strengths=[str(x) for x in (swot_raw.get("strengths") or [])][:4],
        weaknesses=[str(x) for x in (swot_raw.get("weaknesses") or [])][:4],
        opportunities=[str(x) for x in (swot_raw.get("opportunities") or [])][:4],
        threats=[str(x) for x in (swot_raw.get("threats") or [])][:4],
    )

    er = result.get("entry_range") or {}
    entry = EntryRange(
        low=_num(er.get("low")),
        high=_num(er.get("high")),
    )

    profile = result.get("investor_profile", "moderate")
    if profile not in ("conservative", "moderate", "aggressive"):
        profile = "moderate"

    return AIConclusion(
        highlights=_str_list("highlights", 3, 3),
        risks=_str_list("risks", 3, 3),
        swot=swot,
        short_term_view=str(result.get("short_term_view", ""))[:200],
        mid_term_view=str(result.get("mid_term_view", ""))[:200],
        long_term_view=str(result.get("long_term_view", ""))[:200],
        entry_range=entry,
        stop_loss=_num(result.get("stop_loss")),
        investor_profile=profile,
    )


def _num(v) -> float | None:
    try:
        if v is None:
            return None
        f = float(v)
        if f != f:
            return None
        return f
    except (ValueError, TypeError):
        return None
