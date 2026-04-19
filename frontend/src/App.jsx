import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import axios from "axios";
import CandleChart from "./components/CandleChart";
import BacktestPanel from "./components/BacktestPanel";
import ScanPanel from "./components/ScanPanel";
import DeepAnalysisPanel from "./components/analysis/DeepAnalysisPanel";
import { fetchDeepAnalysis } from "./api/analysisApi";

const DEFAULT_SYMBOLS = { tw: "2330", us: "AAPL" };

// ── Client-side MA computation (fallback if backend omits ma5/ma10) ──────────
function computeMA(candles, period) {
  const result = [];
  for (let i = period - 1; i < candles.length; i++) {
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += candles[j].close;
    result.push({ date: candles[i].date, value: Math.round(sum / period * 10000) / 10000 });
  }
  return result;
}

// ── Client-side Support / Resistance calculation ──────────────────────────────
// Runs entirely in the browser from existing daily candle data.
// No backend call needed → always works.
function calculateSR(candles, pivotWindow = 10, nLevels = 5, clusterPct = 0.015) {
  const n = candles.length;
  if (n < pivotWindow * 2 + 1) return { support: [], resistance: [], current_price: 0 };

  const resPivots = [], supPivots = [];
  for (let i = pivotWindow; i < n - pivotWindow; i++) {
    let maxH = -Infinity, minL = Infinity;
    for (let j = i - pivotWindow; j <= i + pivotWindow; j++) {
      if (candles[j].high  > maxH) maxH = candles[j].high;
      if (candles[j].low   < minL) minL = candles[j].low;
    }
    if (candles[i].high >= maxH) resPivots.push(candles[i].high);
    if (candles[i].low  <= minL) supPivots.push(candles[i].low);
  }

  function cluster(pivots) {
    if (!pivots.length) return [];
    const sorted = [...pivots].sort((a, b) => a - b);
    const groups = [];
    let grp = [sorted[0]];
    for (let i = 1; i < sorted.length; i++) {
      if ((sorted[i] - grp[0]) / grp[0] <= clusterPct) { grp.push(sorted[i]); }
      else { groups.push(grp); grp = [sorted[i]]; }
    }
    groups.push(grp);
    return groups.map(g => ({
      price:    Math.round(g.reduce((a, b) => a + b, 0) / g.length * 100) / 100,
      strength: g.length,
    }));
  }

  const cur = candles[n - 1].close;
  return {
    support:       cluster(supPivots) .filter(s => s.price <= cur * (1 + clusterPct)).sort((a,b) => b.strength - a.strength).slice(0, nLevels),
    resistance:    cluster(resPivots) .filter(r => r.price >= cur * (1 - clusterPct)).sort((a,b) => b.strength - a.strength).slice(0, nLevels),
    current_price: cur,
  };
}
// ── Client-side weekly / monthly aggregation from daily candles ───────────────
function aggregateCandles(candles, interval) {
  if (interval === "1d") return candles;
  const groups = {};
  candles.forEach((c) => {
    const d = new Date(c.date + "T00:00:00");
    let key;
    if (interval === "1wk") {
      // Key = Monday of that week — use LOCAL date parts (not toISOString which gives UTC)
      const day  = d.getDay() || 7;                        // 1=Mon … 7=Sun
      const mon  = new Date(d);
      mon.setDate(d.getDate() - (day - 1));
      const y  = mon.getFullYear();
      const m  = String(mon.getMonth() + 1).padStart(2, "0");
      const dd = String(mon.getDate()).padStart(2, "0");
      key = `${y}-${m}-${dd}`;
    } else {
      key = c.date.slice(0, 7) + "-01";                   // YYYY-MM-01
    }
    if (!groups[key]) {
      groups[key] = { date: key, open: c.open, high: c.high, low: c.low, close: c.close, volume: c.volume };
    } else {
      groups[key].high   = Math.max(groups[key].high, c.high);
      groups[key].low    = Math.min(groups[key].low,  c.low);
      groups[key].close  = c.close;
      groups[key].volume += c.volume;
    }
  });
  return Object.values(groups).sort((a, b) => a.date.localeCompare(b.date));
}

const DAILY_LIMIT = 500; // 2 years
const INTERVAL_OPTIONS = [
  { label: "月K",  value: "1mo" },
  { label: "周K",  value: "1wk" },
  { label: "日K",  value: "1d"  },
  { label: "60m",  value: "60m" },
  { label: "15m",  value: "15m" },
  { label: "5m",   value: "5m"  },
  { label: "1m",   value: "1m"  },
];
// Intervals that poll every 60 s; weekly/monthly don't need auto-refresh
const SHORT_INTRADAY = new Set(["60m", "15m", "5m", "1m"]);

export default function App() {
  const [tab,    setTab]    = useState("analyze");

  const [market,   setMarket]   = useState("tw");
  const [symbol,   setSymbol]   = useState("2330");
  const [interval, setChartInterval] = useState("1d");

  // Daily data (set once per search)
  const [stockData,       setStockData]       = useState(null);
  const [deepAnalysis,    setDeepAnalysis]    = useState(null);
  const [deepLoading,     setDeepLoading]     = useState(false);
  const [deepError,       setDeepError]       = useState(null);
  // Intraday candles (replaced on each refresh)
  const [intradayCandles, setIntradayCandles] = useState([]);
  // Live quote (refreshed every 30 s)
  const [quoteData, setQuoteData] = useState(null);

  const [loading,         setLoading]         = useState(false);
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [intradayError,   setIntradayError]   = useState(null);
  const [error,           setError]           = useState(null);

  // Refs so interval callbacks always see current values without stale closures
  const liveRef      = useRef({ sym: null, mkt: null, interval: "1d" });
  const quoteTimer   = useRef(null);
  const intradayTimer = useRef(null);

  // ── Quote polling ─────────────────────────────────────────────────────────
  const fetchQuote = useCallback(async (sym, mkt) => {
    try {
      const res = await axios.get(`/api/stock/${sym}/quote`, { params: { market: mkt } });
      setQuoteData(res.data);
    } catch { /* silent */ }
  }, []);

  const startQuotePolling = useCallback((sym, mkt) => {
    liveRef.current.sym = sym;
    liveRef.current.mkt = mkt;
    if (quoteTimer.current) clearInterval(quoteTimer.current);
    fetchQuote(sym, mkt);
    quoteTimer.current = setInterval(
      () => fetchQuote(liveRef.current.sym, liveRef.current.mkt),
      30_000,
    );
  }, [fetchQuote]);

  // ── Intraday fetch + polling ──────────────────────────────────────────────
  const fetchIntraday = useCallback(async (sym, mkt, ivl) => {
    try {
      setIntradayLoading(true);
      setIntradayError(null);
      const res = await axios.get(`/api/stock/${sym}/intraday`, {
        params: { market: mkt, interval: ivl },
      });
      setIntradayCandles(res.data);
    } catch (e) {
      console.error("intraday fetch error", e);
      const msg = e?.response?.data?.detail || e?.message || "無法取得分K資料";
      setIntradayError(msg);
    } finally {
      setIntradayLoading(false);
    }
  }, []);

  const startIntradayPolling = useCallback((sym, mkt, ivl) => {
    liveRef.current.interval = ivl;
    if (intradayTimer.current) { clearInterval(intradayTimer.current); intradayTimer.current = null; }
    // Clear stale candles immediately so the chart doesn't briefly show old data
    setIntradayCandles([]);
    setIntradayError(null);
    fetchIntraday(sym, mkt, ivl);
    // Only auto-refresh short intraday intervals; weekly/monthly don't need it
    if (SHORT_INTRADAY.has(ivl)) {
      intradayTimer.current = setInterval(
        () => fetchIntraday(liveRef.current.sym, liveRef.current.mkt, liveRef.current.interval),
        60_000,
      );
    }
  }, [fetchIntraday]);

  const stopIntradayPolling = useCallback(() => {
    if (intradayTimer.current) { clearInterval(intradayTimer.current); intradayTimer.current = null; }
    setIntradayCandles([]);
  }, []);

  // Clean up all timers on unmount
  useEffect(() => () => {
    if (quoteTimer.current)    clearInterval(quoteTimer.current);
    if (intradayTimer.current) clearInterval(intradayTimer.current);
  }, []);

  // ── React to interval change (only when a stock is already loaded) ────────
  // 1d / 1wk / 1mo → 用本地日K聚合，不呼叫 intraday endpoint
  const DAILY_LIKE = new Set(["1d", "1wk", "1mo"]);

  useEffect(() => {
    if (!stockData) return;
    const { sym, mkt } = liveRef.current;
    if (!sym) return;
    if (DAILY_LIKE.has(interval)) {
      stopIntradayPolling();
    } else {
      startIntradayPolling(sym, mkt, interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleMarketChange = (m) => { setMarket(m); setSymbol(DEFAULT_SYMBOLS[m]); };

  const runDeepAnalysis = useCallback(async (forceRefresh = false) => {
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;
    setDeepLoading(true);
    setDeepError(null);
    try {
      const data = await fetchDeepAnalysis(sym, market.toUpperCase(), forceRefresh);
      setDeepAnalysis(data);
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || "深度分析載入失敗";
      setDeepError(msg);
    } finally {
      setDeepLoading(false);
    }
  }, [symbol, market]);

  const handleSearch = async (e) => {
    e.preventDefault();
    const sym = symbol.trim().toUpperCase();
    if (!sym) return;

    setLoading(true);
    setError(null);
    setStockData(null);
    setQuoteData(null);
    setDeepAnalysis(null);
    setDeepError(null);
    stopIntradayPolling();
    setChartInterval("1d");  // reset to daily on new search

    try {
      const [klineRes, indRes] = await Promise.allSettled([
        axios.get(`/api/stock/${sym}/kline`,       { params: { market, period: "daily", limit: DAILY_LIMIT } }),
        axios.get(`/api/stock/${sym}/indicators`,   { params: { market } }),
      ]);

      if (klineRes.status === "fulfilled") {
        const dailyCandles = klineRes.value.data;
        const ind = indRes.status === "fulfilled" ? indRes.value.data : {};
        if (!ind.ma5?.length)  ind.ma5  = computeMA(dailyCandles, 5);
        if (!ind.ma10?.length) ind.ma10 = computeMA(dailyCandles, 10);
        setStockData({
          symbol,
          market,
          candles:    dailyCandles,
          indicators: ind,
          sr:         calculateSR(dailyCandles, 10, 5),           // 中長期：window=10，全部資料
          shortSr:    calculateSR(dailyCandles.slice(-60), 5, 3), // 短期：window=5，近 60 根
        });
        startQuotePolling(sym, market);
      } else {
        setError(klineRes.reason?.response?.data?.detail || klineRes.reason?.message);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Candles passed to CandleChart:
  //   1d        → 原始日K
  //   1wk / 1mo → 前端聚合自日K，不走 intraday
  //   分鐘線    → intraday endpoint 回傳
  // Memoized so chartData only changes when actual data changes, not on every quote poll.
  const chartCandles = useMemo(() => {
    if (!stockData) return [];
    if (interval === "1wk" || interval === "1mo")
      return aggregateCandles(stockData.candles, interval);
    if (interval !== "1d" && intradayCandles.length > 0)
      return intradayCandles;
    return stockData.candles;
  }, [stockData, interval, intradayCandles]);

  const chartData = useMemo(() => {
    if (!stockData) return null;
    return {
      ...stockData,
      candles:    chartCandles,
      // 指標只在日K顯示（週/月K用日K聚合，MA 點數會不對齊）
      indicators: interval === "1d" ? stockData.indicators : {},
      shortSr:    interval === "1d" ? stockData.shortSr : null,
    };
  }, [stockData, chartCandles, interval]);

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
                tab === key ? "bg-[#1f6feb] text-white" : "bg-[#21262d] text-[#8b949e] hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {/* Search Bar */}
      <div className={`bg-[#161b22] border-b border-[#30363d] px-6 py-4 ${tab === "analyze" ? "" : "hidden"}`}>
        <form onSubmit={handleSearch} className="flex flex-wrap gap-3 items-end">
          {/* Market toggle */}
          <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
            {["tw", "us"].map((m) => (
              <button key={m} type="button" onClick={() => handleMarketChange(m)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  market === m ? "bg-[#1f6feb] text-white" : "bg-[#21262d] text-[#8b949e] hover:text-white"
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
              type="text" value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              placeholder={market === "tw" ? "e.g. 2330" : "e.g. AAPL"}
              className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm w-32 focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
            />
          </div>

          {/* Interval selector */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-[#8b949e]">週期</label>
            <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
              {INTERVAL_OPTIONS.map((opt) => (
                <button key={opt.value} type="button"
                  onClick={() => setChartInterval(opt.value)}
                  disabled={!stockData && opt.value !== "1d"}
                  className={`px-3 py-2 text-xs font-medium transition-colors disabled:opacity-40 ${
                    interval === opt.value
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
          <button type="submit" disabled={loading}
            className="px-5 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "載入中..." : "查詢"}
          </button>

          {/* Deep analysis trigger (on-demand) */}
          <button type="button" disabled={deepLoading || !stockData}
            onClick={() => runDeepAnalysis(false)}
            className="px-5 py-2 bg-[#6f42c1] hover:bg-[#8957e5] disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            title={stockData ? "以快取為主產生深度分析" : "請先查詢股票"}
          >
            {deepLoading ? "分析中..." : "🧠 深度分析"}
          </button>
        </form>
      </div>

      {/* Main Content */}
      <main className="p-6 space-y-6">
        {tab === "backtest" && <BacktestPanel />}
        {tab === "scan"     && <ScanPanel />}

        {tab === "analyze" && (
          <>
            {error && (
              <div className="bg-[#3d1f1f] border border-[#f85149] rounded-lg p-4 text-[#f85149] text-sm">
                ⚠ {error}
              </div>
            )}
            {intradayError && !error && (
              <div className="bg-[#2d2208] border border-[#f0b429] rounded-lg p-3 text-[#f0b429] text-xs">
                ⚠ 分K資料無法載入（{intradayError}）。yfinance 分鐘資料限制：1m 僅最近 2 天，5m/15m/60m 最近 5 天，且台股盤後可能暫時無資料。
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center py-20 gap-4">
                <div className="spinner" />
                <p className="text-[#8b949e] text-sm">正在載入 {symbol} 的資料...</p>
              </div>
            )}

            {!loading && chartData && (
              <CandleChart
                data={chartData}
                quote={quoteData}
                interval={interval}
                intradayLoading={intradayLoading}
              />
            )}

            {(deepAnalysis || deepLoading || deepError) && (
              <DeepAnalysisPanel
                report={deepAnalysis}
                loading={deepLoading}
                error={deepError}
                onRefresh={() => runDeepAnalysis(true)}
              />
            )}

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
