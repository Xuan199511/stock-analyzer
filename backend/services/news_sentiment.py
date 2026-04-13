"""NewsAPI + Claude sentiment analysis service.

Environment variables required:
    NEWS_API_KEY       — https://newsapi.org/ (free tier, 100 req/day)
    ANTHROPIC_API_KEY  — https://console.anthropic.com/
"""
import os
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

import httpx
import anthropic

NEWS_API_URL  = "https://newsapi.org/v2/everything"
CLAUDE_MODEL  = "claude-haiku-4-5-20251001"   # fast & cheap for batch sentiment

_news_api_key      = os.getenv("NEWS_API_KEY", "")
_anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")


# ── NewsAPI ───────────────────────────────────────────────────────────────────

async def fetch_news(query: str, days: int = 7, limit: int = 10) -> list[dict]:
    """Fetch recent news from NewsAPI.  Returns [] when key is absent."""
    if not _news_api_key:
        return []

    from_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "q":        query,
        "from":     from_date,
        "sortBy":   "publishedAt",
        "pageSize": limit,
        "language": "en",
        "apiKey":   _news_api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(NEWS_API_URL, params=params)
            r.raise_for_status()
            payload = r.json()
    except Exception as e:
        print(f"[NewsAPI] fetch error: {e}")
        return []

    articles = []
    for item in payload.get("articles", []):
        title = (item.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue
        articles.append({
            "title":       title,
            "url":         item.get("url", ""),
            "source":      (item.get("source") or {}).get("name", ""),
            "publishedAt": (item.get("publishedAt") or "")[:10],
        })
    return articles


# ── Claude sentiment ──────────────────────────────────────────────────────────

async def analyze_with_claude(symbol: str, articles: list[dict]) -> dict:
    """Batch-analyze news titles with Claude; return structured sentiment."""
    if not _anthropic_api_key:
        return _fallback(articles, reason="ANTHROPIC_API_KEY not set")
    if not articles:
        return _empty()

    # Build numbered title list for the prompt
    lines = "\n".join(
        f"{i + 1}. [{a['publishedAt']}] {a['title']}"
        for i, a in enumerate(articles)
    )
    prompt = f"""你是專業的金融新聞情緒分析師。
請分析以下與股票代號 {symbol} 相關的新聞標題，以繁體中文摘要市場情緒。

新聞清單：
{lines}

請嚴格回傳以下 JSON（不要有多餘文字或 markdown 包裝）：
{{
  "overall": "positive" | "neutral" | "negative",
  "score": <整數 0-100，0=極度負面，50=中性，100=極度正面>,
  "summary": "<一句話繁體中文整體情緒摘要>",
  "news": [
    {{"index": <新聞編號>, "sentiment": "positive" | "neutral" | "negative", "reason": "<繁體中文簡短原因>"}}
  ]
}}"""

    try:
        client = anthropic.AsyncAnthropic(api_key=_anthropic_api_key)
        msg = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
    except Exception as e:
        print(f"[Claude] API error: {e}")
        return _fallback(articles, reason=str(e))

    # Strip optional markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Claude] JSON parse error: {e}\nRaw: {raw[:300]}")
        return _fallback(articles, reason="JSON parse failed")

    # Map Claude per-article sentiment back to articles
    claude_map = {item["index"]: item for item in result.get("news", [])}
    enriched = []
    for i, a in enumerate(articles):
        c = claude_map.get(i + 1, {})
        enriched.append({
            "title":     a["title"],
            "url":       a["url"],
            "source":    a["source"],
            "date":      a["publishedAt"],
            "sentiment": c.get("sentiment", "neutral"),
            "reason":    c.get("reason", ""),
        })

    return {
        "overall": result.get("overall", "neutral"),
        "score":   int(result.get("score", 50)),
        "summary": result.get("summary", ""),
        "news":    enriched,
        "trend":   _build_trend(enriched),
        "source":  "claude",
    }


# ── Trend builder ─────────────────────────────────────────────────────────────

def _build_trend(articles: list[dict], days: int = 7) -> list[dict]:
    """Aggregate per-day sentiment score from enriched articles (last `days` days)."""
    today = datetime.today().date()

    # Initialise all days with neutral score
    buckets: dict[str, dict] = {}
    for offset in range(days - 1, -1, -1):
        d = (today - timedelta(days=offset)).isoformat()
        buckets[d] = {"date": d, "score": 50, "count": 0, "pos": 0, "neg": 0, "neu": 0}

    for a in articles:
        d = str(a.get("date", ""))[:10]
        if d not in buckets:
            continue
        buckets[d]["count"] += 1
        sent = a.get("sentiment", "neutral")
        if sent == "positive":
            buckets[d]["pos"] += 1
        elif sent == "negative":
            buckets[d]["neg"] += 1
        else:
            buckets[d]["neu"] += 1

    # Convert counts to a score (pos pushes up, neg pushes down)
    result = []
    for d, b in sorted(buckets.items()):
        n = b["count"]
        if n > 0:
            b["score"] = round(50 + (b["pos"] - b["neg"]) / n * 50)
        result.append({"date": b["date"], "score": b["score"], "count": b["count"]})
    return result


# ── Fallbacks ─────────────────────────────────────────────────────────────────

def _empty() -> dict:
    return {
        "overall": "neutral", "score": 50,
        "summary": "目前無相關新聞資料。",
        "news": [], "trend": _build_trend([]), "source": "none",
    }


def _fallback(articles: list[dict], reason: str = "") -> dict:
    """Keyword-based English sentiment when Claude is unavailable."""
    POS = {"surge", "rally", "beat", "record", "growth", "profit", "buy",
           "upgrade", "strong", "soar", "gain", "rise", "bullish"}
    NEG = {"fall", "drop", "miss", "loss", "warning", "cut", "sell",
           "downgrade", "weak", "crash", "decline", "bearish", "risk"}

    enriched = []
    for a in articles:
        words = set(a["title"].lower().split())
        p = len(words & POS)
        n = len(words & NEG)
        if p > n:
            sent = "positive"
        elif n > p:
            sent = "negative"
        else:
            sent = "neutral"
        enriched.append({**a, "date": a.get("publishedAt", ""),
                         "sentiment": sent, "reason": ""})

    pos = sum(1 for a in enriched if a["sentiment"] == "positive")
    neg = sum(1 for a in enriched if a["sentiment"] == "negative")
    total = len(enriched) or 1
    score = round(50 + (pos - neg) / total * 50)
    overall = "positive" if score > 60 else "negative" if score < 40 else "neutral"

    note = f"（Claude 未啟用：{reason}）" if reason else ""
    return {
        "overall": overall,
        "score":   score,
        "summary": f"基於關鍵字分析，整體情緒{{'positive':'偏正面','negative':'偏負面'}.get(overall,'中性')}。{note}",
        "news":    enriched,
        "trend":   _build_trend(enriched),
        "source":  "keyword",
    }
