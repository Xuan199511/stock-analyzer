# Stock Analyzer

台股 + 美股即時分析平台，整合技術指標、基本面、情緒分析、策略回測、訊號掃描與支撐壓力位功能。

**線上網址：** [Vercel 前端] → 代理至 [Render 後端 `https://stock-analyzer-backend-1028.onrender.com`]  
**原始碼：** `https://github.com/Xuan199511/stock-analyzer`

---

## 功能總覽

| 功能 | 說明 |
|------|------|
| **K 線圖** | 日K / 周K / 月K / 60m / 15m / 5m / 1m，自動切換 |
| **技術指標** | MA20、MA60、RSI(14)、MACD(12,26,9)、布林帶(20,2) |
| **支撐與壓力** | Pivot Point 聚類演算法，前端直接計算，顯示強度 |
| **即時報價** | yfinance fast_info，每 30 秒更新；盤中今日 K 棒即時更新 OHLC |
| **分K自動刷新** | 60m/15m/5m/1m 每 60 秒自動抓新資料 |
| **基本面** | PE/PB/EPS/ROE/毛利率、近 8 季 EPS、近 12 月營收 |
| **情緒分析** | NewsAPI 抓新聞 + Claude AI 批次分析，近 7 天趨勢 |
| **策略回測** | 4 種策略（MA 均線、RSI、MACD、布林帶），自訂參數 |
| **訊號掃描** | 固定觀察名單，自動掃描 BUY/SELL/NONE 並顯示強度 |
| **LINE Notify** | 手動 / 排程自動通知 |
| **APScheduler** | 台股 22:30、美股 15:00（Asia/Taipei）自動掃描並推播 |

---

## 技術架構

### 後端（Render）

```
backend/
├── main.py                  # FastAPI 入口、CORS、API Key 中介層、APScheduler
├── routers/
│   ├── stock.py             # K 線、指標、intraday、quote、SR、基本面、情緒
│   ├── backtest.py          # POST /api/backtest
│   ├── scan.py              # GET /api/scan
│   └── notify.py            # POST /api/notify/line
├── services/
│   ├── indicators.py        # MA / RSI / MACD / BB（純 pandas/numpy）
│   ├── finmind.py           # 台股資料（FinMind API）
│   ├── yfinance_service.py  # 美股資料、報價、intraday（yfinance）
│   ├── backtest_engine.py   # 回測邏輯
│   ├── scanner.py           # 訊號掃描
│   ├── notifier.py          # LINE Notify
│   └── news_sentiment.py    # NewsAPI + Claude 情緒分析
├── requirements.txt
├── render.yaml
└── runtime.txt              # Python 3.12.0
```

**主要依賴：** FastAPI、uvicorn、yfinance、pandas、numpy、httpx、anthropic、apscheduler、pytz

### 前端（Vercel）

```
frontend/
├── src/
│   ├── App.jsx              # 主頁面、查詢邏輯、即時報價輪詢、S/R 前端計算
│   └── components/
│       ├── CandleChart.jsx  # lightweight-charts K 線圖、技術指標、S/R 線
│       ├── BacktestPanel.jsx
│       ├── ScanPanel.jsx
│       ├── FundamentalPanel.jsx
│       └── SentimentPanel.jsx
├── vercel.json              # /api/* 代理至 Render
└── vite.config.js
```

**主要依賴：** React、Vite、Tailwind CSS、lightweight-charts、axios

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/stock/{symbol}/kline` | 日 K 線（OHLCV） |
| GET | `/api/stock/{symbol}/indicators` | MA/RSI/MACD/BB |
| GET | `/api/stock/{symbol}/intraday` | 分鐘/小時 K 線 |
| GET | `/api/stock/{symbol}/quote` | 即時報價 |
| GET | `/api/stock/{symbol}/fundamental` | 基本面 |
| GET | `/api/stock/{symbol}/sentiment` | 情緒分析 |
| POST | `/api/backtest` | 策略回測 |
| GET | `/api/scan` | 訊號掃描 |
| POST | `/api/notify/line` | LINE 推播 |

---

## 本機開發

### 環境需求

- Python 3.12+
- Node.js 18+

### 後端啟動

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 複製環境變數
cp .env.example .env          # 填入 API Keys

uvicorn main:app --reload --port 8000
```

### 前端啟動

```bash
cd frontend
npm install
npm run dev
```

前端預設 `http://localhost:5173`，`vite.config.js` 已設定 `host: "0.0.0.0"` 支援區域網路存取。

---

## 環境變數（`.env`）

| 變數 | 說明 | 必填 |
|------|------|------|
| `ANTHROPIC_API_KEY` | Claude AI（情緒分析） | 情緒功能需要 |
| `NEWS_API_KEY` | NewsAPI（新聞抓取） | 情緒功能需要 |
| `LINE_NOTIFY_TOKEN` | LINE Notify 個人存取權杖 | LINE 推播需要 |
| `FINMIND_API_KEY` | FinMind API（台股資料） | 選填，提高速率限制 |
| `API_SECRET_KEY` | 自訂 API 保護金鑰 | 選填，不設則開放存取 |

---

## 雲端部署

### 後端（Render）

1. 連接 GitHub repo
2. Root Directory：`backend`
3. Build Command：`pip install -r requirements.txt`
4. Start Command：`uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment Variables：填入上方所有需要的 Keys

### 前端（Vercel）

1. 連接 GitHub repo
2. Root Directory：`frontend`
3. 自動部署（push 到 main 即更新）
4. `vercel.json` 已設定將 `/api/*` 代理至 Render 後端

---

## 支撐與壓力演算法

採用 **Pivot Point 聚類法**，完全在前端瀏覽器執行：

1. **找樞紐點**：掃描每根 K 棒，若其最高/最低價為前後 N 根的極值，標記為壓力/支撐樞紐點
2. **聚類合併**：將價格距離在 1.5% 以內的樞紐點合併為同一區間
3. **強度排序**：區間內的樞紐點越多，強度（×N）越高，代表該位置被市場測試越多次
4. **顯示**：綠色虛線 = 支撐位、紅色虛線 = 壓力位，標籤顯示強度

---

## 觀察名單（訊號掃描）

| 市場 | 股票代號 |
|------|----------|
| 台股 | 2330、2317、2454、2308、2382、6505 |
| 美股 | AAPL、NVDA、TSLA、MSFT、META、GOOGL |

---

## 資料來源限制

| 資料類型 | 來源 | 延遲 |
|----------|------|------|
| 台股日K / 基本面 | FinMind API | 收盤後更新 |
| 美股日K / 基本面 | yfinance (Yahoo Finance) | 收盤後更新 |
| 即時報價（台股/美股） | yfinance fast_info | 約 15 分鐘延遲 |
| 分K資料 | yfinance | 約 15 分鐘延遲 |
| 新聞情緒 | NewsAPI + Claude AI | 即時 |

> 真正零延遲的即時報價需要付費資料源（台股：富果 Fugle；美股：Polygon.io）

---

## Git 提交歷史（主要功能）

| 功能 | 說明 |
|------|------|
| K 線圖 + 技術指標 | lightweight-charts 整合，MA/RSI/MACD/BB |
| 基本面 + 情緒分析 | FinMind + yfinance + NewsAPI + Claude |
| 策略回測 | BacktestPanel + backtest_engine |
| 訊號掃描 | ScanPanel + scanner service + LINE Notify |
| APScheduler | 台股/美股定時自動掃描推播 |
| 支撐壓力位 | Pivot Point 聚類，前端計算 |
| 即時報價 | yfinance fast_info + 今日 K 棒動態更新 |
| 分K圖 | /intraday 端點 + 1m/5m/15m/60m/周K/月K |
| 安全修正 | setInterval 命名衝突修復 |
