"""Market sentiment / news headline analysis endpoints."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta

from services import finmind, yfinance_service

router = APIRouter()

# Simple Chinese/English keyword sentiment dictionaries
POSITIVE_KW = {"漲", "突破", "強勢", "創高", "利多", "買超", "獲利", "成長", "亮眼", "超預期"}
NEGATIVE_KW = {"跌", "下修", "虧損", "利空", "賣超", "裁員", "警示", "崩跌", "衰退", "虧損"}


def _tw_sentiment(title: str) -> dict:
    pos = sum(1 for kw in POSITIVE_KW if kw in title)
    neg = sum(1 for kw in NEGATIVE_KW if kw in title)
    polarity = (pos - neg) / max(pos + neg, 1) if (pos + neg) > 0 else 0.0
    if polarity > 0:
        label = "positive"
    elif polarity < 0:
        label = "negative"
    else:
        label = "neutral"
    return {"sentiment": label, "polarity": round(polarity, 3)}


def _summary_stats(articles: list[dict]) -> dict:
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    polarities = []
    for a in articles:
        counts[a.get("sentiment", "neutral")] += 1
        polarities.append(a.get("polarity", 0))
    avg_polarity = sum(polarities) / len(polarities) if polarities else 0.0
    total = len(articles)
    overall = "neutral"
    if counts["positive"] > counts["negative"] and counts["positive"] / max(total, 1) > 0.4:
        overall = "bullish"
    elif counts["negative"] > counts["positive"] and counts["negative"] / max(total, 1) > 0.4:
        overall = "bearish"
    return {
        "total": total,
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral": counts["neutral"],
        "avg_polarity": round(avg_polarity, 3),
        "overall": overall,
    }


@router.get("/{symbol}")
async def get_sentiment(
    symbol: str,
    market: str = Query("tw", enum=["tw", "us"]),
):
    """Return news headlines with sentiment scores."""
    if market == "us":
        articles = yfinance_service.get_news_with_sentiment(symbol)
        if not articles:
            return {"symbol": symbol, "market": "us", "articles": [], "summary": _summary_stats([])}
        return {
            "symbol": symbol,
            "market": "us",
            "articles": articles,
            "summary": _summary_stats(articles),
        }

    # Taiwan
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")
    raw_news = await finmind.get_news(symbol, start_date, end_date)

    articles = []
    for item in raw_news[:30]:
        title = item.get("title", "")
        sent = _tw_sentiment(title)
        articles.append({
            "title": title,
            "publisher": item.get("source", ""),
            "link": item.get("link", ""),
            "published": item.get("date", ""),
            **sent,
        })

    return {
        "symbol": symbol,
        "market": "tw",
        "articles": articles,
        "summary": _summary_stats(articles),
    }
