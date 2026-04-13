import { useState } from "react";
import axios from "axios";
import CandleChart from "./components/CandleChart";
import FundamentalPanel from "./components/FundamentalPanel";
import SentimentPanel from "./components/SentimentPanel";
import BacktestPanel from "./components/BacktestPanel";
import ScanPanel from "./components/ScanPanel";

const DEFAULT_SYMBOLS = { tw: "2330", us: "AAPL" };
const LIMIT_OPTIONS = [
  { label: "1 個月",  value: 22  },
  { label: "3 個月",  value: 66  },
  { label: "6 個月",  value: 120 },
  { label: "1 年",    value: 250 },
  { label: "2 年",    value: 500 },
];

export default function App() {
  const [tab,    setTab]    = useState("analyze");   // "analyze" | "backtest"

  const [market, setMarket] = useState("tw");
  const [symbol, setSymbol] = useState("2330");
  const [limit,  setLimit]  = useState(120);

  const [stockData,       setStockData]       = useState(null);
  const [fundamentalData, setFundamentalData] = useState(null);
  const [sentimentData,   setSentimentData]   = useState(null);

  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleMarketChange = (m) => {
    setMarket(m);
    setSymbol(DEFAULT_SYMBOLS[m]);
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;

    setLoading(true);
    setError(null);
    setStockData(null);
    setFundamentalData(null);
    setSentimentData(null);

    try {
      // ── 同時發出五個請求 ──────────────────────────────────────────────────
      const [klineRes, indRes, fundRes, sentRes, srRes] = await Promise.allSettled([
        axios.get(`/api/stock/${sym}/kline`,      { params: { market, period: "daily", limit } }),
        axios.get(`/api/stock/${sym}/indicators`,  { params: { market } }),
        axios.get(`/api/stock/${sym}/fundamental`,  { params: { market } }),
        axios.get(`/api/stock/${sym}/sentiment`,    { params: { market } }),
        axios.get(`/api/stock/${sym}/sr`,           { params: { market } }),
      ]);

      // K 線是必要資料，失敗就顯示錯誤
      if (klineRes.status === "fulfilled") {
        setStockData({
          symbol,
          market,
          candles:    klineRes.value.data,
          indicators: indRes.status === "fulfilled" ? indRes.value.data : {},
          sr:         srRes.status  === "fulfilled" ? srRes.value.data  : null,
        });
      } else {
        setError(
          klineRes.reason?.response?.data?.detail || klineRes.reason?.message
        );
      }

      if (fundRes.status === "fulfilled") setFundamentalData(fundRes.value.data);
      if (sentRes.status === "fulfilled") setSentimentData(sentRes.value.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      {/* Header */}
      <header className="bg-[#161b22] border-b border-[#30363d] px-6 py-4 flex items-center gap-3">
        <span className="text-2xl">📈</span>
        <div>
          <h1 className="text-xl font-bold text-white">Stock Analyzer</h1>
          <p className="text-xs text-[#8b949e]">台股 FinMind ｜ 美股 yfinance</p>
        </div>

        {/* Tab switcher */}
        <div className="ml-8 flex rounded-lg overflow-hidden border border-[#30363d]">
          {[
            { key: "analyze",  label: "📊 股票分析" },
            { key: "backtest", label: "🔬 策略回測" },
            { key: "scan",     label: "📡 訊號掃描" },
          ].map(({ key, label }) => (
            <button key={key} type="button" onClick={() => setTab(key)}
              className={`px-4 py-1.5 text-sm font-medium transition-colors ${
                tab === key
                  ? "bg-[#1f6feb] text-white"
                  : "bg-[#21262d] text-[#8b949e] hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {/* Search Bar — only shown on analyze tab */}
      <div className={`bg-[#161b22] border-b border-[#30363d] px-6 py-4 ${tab === "analyze" ? "" : "hidden"}`}>
        <form onSubmit={handleSearch} className="flex flex-wrap gap-3 items-end">
          {/* Market toggle */}
          <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
            {["tw", "us"].map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => handleMarketChange(m)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  market === m
                    ? "bg-[#1f6feb] text-white"
                    : "bg-[#21262d] text-[#8b949e] hover:text-white"
                }`}
              >
                {m === "tw" ? "🇹🇼 台股" : "🇺🇸 美股"}
              </button>
            ))}
          </div>

          {/* Symbol */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#8b949e]">股票代號</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder={market === "tw" ? "e.g. 2330" : "e.g. AAPL"}
              className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm w-32 focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
            />
          </div>

          {/* Period / limit selector */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#8b949e]">K 線筆數</label>
            <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
              {LIMIT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setLimit(opt.value)}
                  className={`px-3 py-2 text-xs font-medium transition-colors ${
                    limit === opt.value
                      ? "bg-[#1f6feb] text-white"
                      : "bg-[#21262d] text-[#8b949e] hover:text-white"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "載入中..." : "查詢"}
          </button>
        </form>
      </div>

      {/* Main Content */}
      <main className="p-6 space-y-6">
        {/* ── Backtest tab ── */}
        {tab === "backtest" && <BacktestPanel />}

        {/* ── Scan tab ── */}
        {tab === "scan" && <ScanPanel />}

        {/* ── Analyze tab ── */}
        {tab === "analyze" && (
          <>
            {/* Error */}
            {error && (
              <div className="bg-[#3d1f1f] border border-[#f85149] rounded-lg p-4 text-[#f85149] text-sm">
                ⚠ {error}
              </div>
            )}

            {/* Loading */}
            {loading && (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <div className="spinner" />
                <p className="text-[#8b949e] text-sm">正在載入 {symbol} 的資料...</p>
              </div>
            )}

            {/* Charts */}
            {!loading && stockData && <CandleChart data={stockData} />}

            {/* Bottom panels */}
            {!loading && (fundamentalData || sentimentData) && (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {fundamentalData && <FundamentalPanel data={fundamentalData} />}
                {sentimentData && <SentimentPanel data={sentimentData} />}
              </div>
            )}

            {/* Empty state */}
            {!loading && !stockData && !error && (
              <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
                <span className="text-5xl mb-4">📊</span>
                <p className="text-lg">輸入股票代號開始分析</p>
                <p className="text-sm mt-2">台股範例：2330（台積電）｜美股範例：AAPL</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
