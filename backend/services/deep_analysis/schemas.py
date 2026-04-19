"""Pydantic schemas for the 9-section deep stock analysis report."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── 一、公司基本資料 ──────────────────────────────────────────────────────────

class BusinessSegment(BaseModel):
    name: str
    revenue_pct: Optional[float] = None


class CompanyBasic(BaseModel):
    symbol: str
    name: str
    market: str                                  # TW / US
    industry: str
    sub_industry: Optional[str] = None
    business_segments: list[BusinessSegment] = Field(default_factory=list)
    top_customers: Optional[list[str]] = None
    supply_chain_position: str = "N/A"          # upstream/midstream/downstream
    description: str = ""


# ── 二、基本面分析 ────────────────────────────────────────────────────────────

class HistoryPoint(BaseModel):
    period: str                                  # "2024Q3" or "2024"
    value: float


class PeerPE(BaseModel):
    avg: Optional[float] = None
    percentile: Optional[float] = None           # 0-100


class Fundamental(BaseModel):
    eps_history:     list[HistoryPoint] = Field(default_factory=list)
    revenue_history: list[HistoryPoint] = Field(default_factory=list)
    gross_margin:    Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin:      Optional[float] = None
    roe:             Optional[float] = None
    pe_ratio:        Optional[float] = None
    pe_ttm:          Optional[float] = None
    pb_ratio:        Optional[float] = None
    dividend_yield:  Optional[float] = None
    debt_ratio:      Optional[float] = None
    free_cash_flow:  Optional[float] = None
    peer_pe_comparison: PeerPE = Field(default_factory=PeerPE)
    valuation_verdict: str = "fair"             # undervalued/fair/overvalued


# ── 三、技術面分析 ────────────────────────────────────────────────────────────

class MACDData(BaseModel):
    macd:    Optional[float] = None
    signal:  Optional[float] = None
    hist:    Optional[float] = None


class InstitutionalFlow(BaseModel):
    foreign:       Optional[float] = None        # net buy (shares or lots)
    investment:    Optional[float] = None        # 投信
    dealer:        Optional[float] = None
    period_days:   int = 5


class Technical(BaseModel):
    current_price:  Optional[float] = None
    price_change_pct: Optional[float] = None
    week_52_high:   Optional[float] = None
    week_52_low:    Optional[float] = None
    ma5:            Optional[float] = None
    ma20:           Optional[float] = None
    ma60:           Optional[float] = None
    ma240:          Optional[float] = None
    ma_alignment:   str = "mixed"               # bullish/bearish/mixed
    kd_k:           Optional[float] = None
    kd_d:           Optional[float] = None
    macd:           MACDData = Field(default_factory=MACDData)
    rsi:            Optional[float] = None
    volume_status:  str = "normal"              # heavy/normal/light
    support_levels:    list[float] = Field(default_factory=list)
    resistance_levels: list[float] = Field(default_factory=list)
    institutional_flow: InstitutionalFlow = Field(default_factory=InstitutionalFlow)


# ── 四、市場情緒分析 ──────────────────────────────────────────────────────────

class NewsItem(BaseModel):
    title: str
    url: str = ""
    source: str = ""
    date: str = ""
    sentiment: str = "neutral"


class MarginTradingChange(BaseModel):
    margin_change:       Optional[float] = None   # 融資餘額變化
    short_change:        Optional[float] = None   # 融券餘額變化
    period_days:         int = 5


class Sentiment(BaseModel):
    news_items:  list[NewsItem] = Field(default_factory=list)
    media_tone:  str = "neutral"                # positive/neutral/negative
    tone_score:  float = 0.0                    # -1 ~ 1
    social_heat: Optional[int] = None
    margin_trading_change: MarginTradingChange = Field(default_factory=MarginTradingChange)
    hot_topics:     list[str] = Field(default_factory=list)
    key_catalysts:  list[str] = Field(default_factory=list)
    key_risks:      list[str] = Field(default_factory=list)


# ── 五、競爭對手比較 ──────────────────────────────────────────────────────────

class Competitor(BaseModel):
    symbol: str
    name: str
    market_cap:   Optional[float] = None
    revenue:      Optional[float] = None
    gross_margin: Optional[float] = None
    eps:          Optional[float] = None
    pe_ratio:     Optional[float] = None
    market_share: Optional[float] = None


# ── 六、SWOT (嵌在 AIConclusion 之前的輕量結構) ──────────────────────────────
# 放進 AIConclusion 中一併由 LLM 產生，避免額外呼叫


# ── 七、護城河 ────────────────────────────────────────────────────────────────

class Moat(BaseModel):
    technical_barrier:    int = 1                # 1-5
    certification_barrier: int = 1
    scale_economy:        int = 1
    switching_cost:       int = 1
    network_effect:       int = 1
    overall_score:        float = 1.0
    replaceability:       str = "partial"        # easily/partial/hard/near_monopoly
    narrative:            str = ""


# ── 八、外資與法人目標價 ──────────────────────────────────────────────────────

class InstitutionalTarget(BaseModel):
    broker:           str
    rating:           str = "hold"                # buy/hold/sell
    target_price:     Optional[float] = None
    report_date:      Optional[str] = None        # ISO date
    key_assumptions:  Optional[str] = None


class ConsensusTarget(BaseModel):
    avg:   Optional[float] = None
    high:  Optional[float] = None
    low:   Optional[float] = None
    count: int = 0


# ── 九、AI 綜合結論 ───────────────────────────────────────────────────────────

class EntryRange(BaseModel):
    low:  Optional[float] = None
    high: Optional[float] = None


class SWOT(BaseModel):
    strengths:     list[str] = Field(default_factory=list)
    weaknesses:    list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    threats:       list[str] = Field(default_factory=list)


class AIConclusion(BaseModel):
    highlights:       list[str] = Field(default_factory=list)   # 3
    risks:            list[str] = Field(default_factory=list)   # 3
    swot:             SWOT = Field(default_factory=SWOT)
    short_term_view:  str = ""
    mid_term_view:    str = ""
    long_term_view:   str = ""
    entry_range:      EntryRange = Field(default_factory=EntryRange)
    stop_loss:        Optional[float] = None
    investor_profile: str = "moderate"            # conservative/moderate/aggressive
    disclaimer:       str = "本分析僅供參考，不構成投資建議，投資人應自行判斷風險。"


# ── 全報告 ────────────────────────────────────────────────────────────────────

class PartialError(BaseModel):
    section: str
    error:   str
    status_code: Optional[int] = None               # HTTP status when applicable
    occurred_at: Optional[datetime] = None


class StockAnalysisReport(BaseModel):
    company:      CompanyBasic
    fundamental:  Fundamental
    technical:    Technical
    sentiment:    Sentiment
    competitors:  list[Competitor] = Field(default_factory=list)
    moat:         Moat
    institutional_targets: list[InstitutionalTarget] = Field(default_factory=list)
    consensus_target:      ConsensusTarget = Field(default_factory=ConsensusTarget)
    ai_conclusion: AIConclusion
    generated_at:  datetime
    data_sources:  list[str] = Field(default_factory=list)
    errors:        list[PartialError] = Field(default_factory=list)
    cached:        bool = False
