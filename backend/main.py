"""Stock Analyzer — FastAPI entry point.

Run:
    uvicorn main:app --reload

Required environment variables (copy .env.example → .env and fill in):
    NEWS_API_KEY       — NewsAPI free tier key
    ANTHROPIC_API_KEY  — Anthropic Claude API key
    LINE_NOTIFY_TOKEN  — LINE Notify personal access token
    FINMIND_API_KEY    — (optional) FinMind API key for higher rate limits
    API_SECRET_KEY     — 自訂金鑰，保護 API 不被外人呼叫
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()   # must run before any service imports that read os.getenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from routers import stock, fundamental, sentiment, backtest, scan, notify

# ── Scheduled jobs ────────────────────────────────────────────────────────────

_tz = pytz.timezone("Asia/Taipei")


async def _scheduled_scan_and_notify(market_label: str, market: str) -> None:
    """Scan the given market and send LINE Notify if any signals found."""
    from services import scanner as sc, notifier as nt

    print(f"[Scheduler] 開始掃描 {market_label}...")
    try:
        results = await sc.scan_market(market)
        has_signal = any(r["signal"] != "NONE" for r in results)

        if has_signal:
            tw = results if market == "TW" else []
            us = results if market == "US" else []
            msg = nt.build_scan_message(tw, us)
            ok, detail = await nt.send(msg)
            print(f"[Scheduler] {market_label} LINE Notify: {'sent' if ok else detail}")
        else:
            print(f"[Scheduler] {market_label} 無訊號，跳過通知")
    except Exception as e:
        print(f"[Scheduler] {market_label} 錯誤: {e}")


async def _job_tw():
    await _scheduled_scan_and_notify("台股 22:30", "TW")


async def _job_us():
    await _scheduled_scan_and_notify("美股 15:00", "US")


# ── App lifespan (scheduler start / stop) ────────────────────────────────────

scheduler = AsyncIOScheduler(timezone=_tz)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(_job_tw, CronTrigger(hour=22, minute=30, timezone=_tz))
    scheduler.add_job(_job_us, CronTrigger(hour=15, minute=0,  timezone=_tz))
    scheduler.start()
    print("[Scheduler] APScheduler started (TW=22:30, US=15:00 Asia/Taipei)")
    yield
    scheduler.shutdown()
    print("[Scheduler] APScheduler stopped")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Stock Analyzer API",
    version="1.0.0",
    description="Taiwan (FinMind) & US (yfinance) stock data with signals & backtest.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API 金鑰保護 middleware ────────────────────────────────────────────────────

_API_KEY = os.getenv("API_SECRET_KEY", "")

# 不需要驗證的路徑（健康檢查、API 文件）
_PUBLIC_PATHS = {"/", "/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def verify_api_key(request: Request, call_next):
    # 本機開發時不設定 API_SECRET_KEY 就跳過驗證
    if not _API_KEY:
        return await call_next(request)

    # 公開路徑免驗
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    # 檢查 header
    key = request.headers.get("X-API-Key", "")
    if key != _API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(stock.router,       prefix="/api/stock",       tags=["Stock / K-Line"])
app.include_router(fundamental.router, prefix="/api/fundamental",  tags=["Fundamental"])
app.include_router(sentiment.router,   prefix="/api/sentiment",    tags=["Sentiment"])
app.include_router(backtest.router,    prefix="/api/backtest",     tags=["Backtest"])
app.include_router(scan.router,        prefix="/api/scan",         tags=["Signal Scanner"])
app.include_router(notify.router,      prefix="/api/notify",       tags=["Notify"])


@app.get("/", tags=["Health"])
def root():
    return {"message": "Stock Analyzer API", "status": "running", "docs": "/docs"}
