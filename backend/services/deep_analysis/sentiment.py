"""Section 4: 市場情緒分析.

- 拉 NewsAPI（英文新聞）
- TW 另外拉融資融券變化（FinMind）
- Claude 整合成 `Sentiment`（media_tone / tone_score / 熱度 / 題材 / 風險）

Claude 不可用時退化成關鍵字情緒（仍會拿融資融券資料）。
"""
from __future__ import annotations

from typing import Any

from ..news_sentiment import fetch_news, analyze_with_claude as keyword_fallback
from .llm import call_json, available as llm_available
from .logging_config import logger
from .schemas import MarginTradingChange, NewsItem, Sentiment
from .sources import finmind_ext

_log = logger.bind(section="sentiment")


def _news_query(symbol: str, market: str, name: str | None = None) -> str:
    if market == "TW":
        # TW code alone returns too many false hits on NewsAPI → add name if available
        return f"{symbol} {name}".strip() if name else f"TWSE {symbol}"
    return name or symbol


async def _claude_summarize(symbol: str, news: list[dict]) -> dict[str, Any]:
    if not news or not llm_available():
        return {}

    lines = "\n".join(
        f"{i + 1}. [{n.get('publishedAt', '')}] {n.get('title', '')}"
        for i, n in enumerate(news[:15])
    )
    prompt = f"""分析以下與股票 {symbol} 相關的最近新聞，輸出市場情緒摘要。

新聞清單：
{lines}

請以繁體中文回傳 JSON：
{{
  "media_tone":   "positive" | "neutral" | "negative",
  "tone_score":   <浮點 -1 ~ 1，-1=極負面，0=中性，1=極正面>,
  "social_heat":  <整數 1-100，熱度分數（依新聞量 + 題材強度判斷）>,
  "hot_topics":   ["題材1", "題材2", ...]  (最多 5 個),
  "key_catalysts":["催化事件1", ...]        (最多 3 個),
  "key_risks":    ["風險1", ...]             (最多 3 個),
  "per_news":     [{{"index": 1, "sentiment": "positive|neutral|negative"}}, ...]
}}"""

    return await call_json(prompt, max_tokens=1500)


async def analyze_sentiment(symbol: str, market: str, name: str | None = None) -> Sentiment:
    # ── News ───────────────────────────────────────────────────────────────
    query = _news_query(symbol, market, name)
    raw_news = await fetch_news(query, days=7, limit=15)

    claude_out: dict[str, Any] = {}
    try:
        claude_out = await _claude_summarize(symbol, raw_news)
    except Exception as e:
        _log.warning(f"Claude summarize failed for {symbol}: {e}")
        claude_out = {}

    # fallback — keyword sentiment on titles when LLM unavailable / failed
    if not claude_out and raw_news:
        kw = await keyword_fallback(symbol, raw_news)
        per_index = {a["title"]: a.get("sentiment", "neutral") for a in kw.get("news", [])}
        news_items = [
            NewsItem(
                title=a["title"], url=a.get("url", ""), source=a.get("source", ""),
                date=a.get("publishedAt", ""), sentiment=per_index.get(a["title"], "neutral"),
            )
            for a in raw_news
        ]
        tone_score = (kw.get("score", 50) - 50) / 50
        overall = kw.get("overall", "neutral")
        hot = []
        catalysts = []
        risks = []
    else:
        per_sent = {
            p.get("index"): p.get("sentiment", "neutral")
            for p in claude_out.get("per_news", [])
        }
        news_items = [
            NewsItem(
                title=n.get("title", ""), url=n.get("url", ""), source=n.get("source", ""),
                date=n.get("publishedAt", ""), sentiment=per_sent.get(i + 1, "neutral"),
            )
            for i, n in enumerate(raw_news)
        ]
        tone_score = float(claude_out.get("tone_score") or 0.0)
        overall = claude_out.get("media_tone", "neutral")
        hot = list(claude_out.get("hot_topics") or [])[:5]
        catalysts = list(claude_out.get("key_catalysts") or [])[:3]
        risks = list(claude_out.get("key_risks") or [])[:3]

    # ── Margin change (TW only) ────────────────────────────────────────────
    margin = MarginTradingChange()
    if market == "TW":
        try:
            m = await finmind_ext.margin_change(symbol, days=5)
            margin = MarginTradingChange(
                margin_change=m.get("margin_change"),
                short_change=m.get("short_change"),
                period_days=m.get("period_days", 5),
            )
        except Exception as e:
            _log.warning(f"FinMind margin_change failed for {symbol}: {e}")

    social_heat = None
    if claude_out.get("social_heat") is not None:
        try:
            social_heat = int(claude_out["social_heat"])
        except (TypeError, ValueError):
            pass
    if social_heat is None and raw_news:
        social_heat = min(len(raw_news) * 7, 100)

    return Sentiment(
        news_items=news_items,
        media_tone=overall if overall in ("positive", "neutral", "negative") else "neutral",
        tone_score=max(-1.0, min(1.0, tone_score)),
        social_heat=social_heat,
        margin_trading_change=margin,
        hot_topics=hot,
        key_catalysts=catalysts,
        key_risks=risks,
    )
