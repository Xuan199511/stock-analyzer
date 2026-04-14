import { useEffect, useRef, useState } from "react";
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts";

// Keys match /api/stock/{symbol}/indicators response
const MA_COLORS = {
  ma20: "#a78bfa",
  ma60: "#fb923c",
};

// BB bands: backend returns bb.upper / bb.mid / bb.lower
const BB_BANDS = ["upper", "mid", "lower"];

export default function CandleChart({ data, quote = null, interval = "1d", intradayLoading = false }) {
  const containerRef = useRef(null);
  const chartRef     = useRef(null);
  const seriesRef    = useRef({});

  const [activeIndicators, setActiveIndicators] = useState({
    ma20: true, ma60: true, bb: false, volume: true, sr: false,
  });
  const [showRSI,  setShowRSI]  = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [tooltipInfo, setTooltipInfo] = useState(null);

  const srLinesRef = useRef([]);

  const { candles = [], indicators = {}, sr = null, symbol, market } = data;

  // Daily bars use date strings "YYYY-MM-DD"; intraday bars use Unix timestamps (int seconds)
  const toTime = (d) => (typeof d === "number" ? d : d.slice(0, 10));
  const isIntraday = interval !== "1d";

  // ── Build / rebuild chart whenever data changes ───────────────────────────
  useEffect(() => {
    if (!containerRef.current || candles.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = {};
    }

    const el    = containerRef.current;
    const chart = createChart(el, {
      width:  el.clientWidth,
      height: 420,
      layout: { background: { color: "#161b22" }, textColor: "#8b949e" },
      grid:   { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      crosshair:       { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale:       { borderColor: "#30363d", timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;

    // ── Candlestick ──────────────────────────────────────────────────────────
    const candleSeries = chart.addCandlestickSeries({
      upColor:    "#26a69a",
      downColor:  "#ef5350",
      borderVisible: false,
      wickUpColor:   "#26a69a",
      wickDownColor: "#ef5350",
    });
    candleSeries.setData(
      candles.map((c) => ({ time: toTime(c.date), open: c.open, high: c.high, low: c.low, close: c.close }))
    );
    seriesRef.current.candle = candleSeries;

    // ── Volume histogram ─────────────────────────────────────────────────────
    const volumeSeries = chart.addHistogramSeries({
      color: "#30363d",
      priceFormat:  { type: "volume" },
      priceScaleId: "volume",
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
    volumeSeries.setData(
      candles.map((c) => ({
        time:  toTime(c.date),
        value: c.volume,
        color: c.close >= c.open ? "#26a69a55" : "#ef535055",
      }))
    );
    seriesRef.current.volume = volumeSeries;

    // ── MA lines (MA20, MA60) ────────────────────────────────────────────────
    Object.entries(MA_COLORS).forEach(([key, color]) => {
      const s = chart.addLineSeries({
        color,
        lineWidth:        1,
        priceLineVisible: false,
        lastValueVisible: false,
        visible:          activeIndicators[key],
      });
      s.setData((indicators[key] || []).map((p) => ({ time: toTime(p.date), value: p.value })));
      seriesRef.current[key] = s;
    });

    // ── Bollinger Bands (upper / mid / lower) ────────────────────────────────
    BB_BANDS.forEach((band) => {
      const s = chart.addLineSeries({
        color:            band === "mid" ? "#6e7681" : "#58a6ff",
        lineWidth:        1,
        lineStyle:        band === "mid" ? LineStyle.Dashed : LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        visible:          activeIndicators.bb,
      });
      s.setData((indicators.bb?.[band] || []).map((p) => ({ time: toTime(p.date), value: p.value })));
      seriesRef.current[`bb_${band}`] = s;
    });

    // ── Crosshair tooltip ────────────────────────────────────────────────────
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData) { setTooltipInfo(null); return; }
      const bar = param.seriesData.get(candleSeries);
      if (bar) setTooltipInfo({ time: param.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close });
    });

    // ── Responsive resize ────────────────────────────────────────────────────
    const handleResize = () => {
      chartRef.current?.applyOptions({ width: containerRef.current?.clientWidth });
    };
    window.addEventListener("resize", handleResize);
    chart.timeScale().fitContent();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // ── Toggle visibility without recreating the chart ────────────────────────
  useEffect(() => {
    Object.keys(MA_COLORS).forEach((key) => {
      seriesRef.current[key]?.applyOptions({ visible: activeIndicators[key] });
    });
    BB_BANDS.forEach((band) => {
      seriesRef.current[`bb_${band}`]?.applyOptions({ visible: activeIndicators.bb });
    });
    seriesRef.current.volume?.applyOptions({ visible: activeIndicators.volume });
  }, [activeIndicators]);

  // ── Support / Resistance price lines ─────────────────────────────────────
  useEffect(() => {
    const candleSeries = seriesRef.current.candle;
    if (!candleSeries) return;

    // Remove any existing SR lines first
    srLinesRef.current.forEach((line) => {
      try { candleSeries.removePriceLine(line); } catch (_) {}
    });
    srLinesRef.current = [];

    if (!activeIndicators.sr) return;

    (sr.resistance || []).forEach(({ price, strength }) => {
      const line = candleSeries.createPriceLine({
        price,
        color:            "#ef5350",
        lineWidth:        1,
        lineStyle:        LineStyle.Dashed,
        axisLabelVisible: true,
        title:            `壓力 ×${strength}`,
      });
      srLinesRef.current.push(line);
    });

    (sr.support || []).forEach(({ price, strength }) => {
      const line = candleSeries.createPriceLine({
        price,
        color:            "#26a69a",
        lineWidth:        1,
        lineStyle:        LineStyle.Dashed,
        axisLabelVisible: true,
        title:            `支撐 ×${strength}`,
      });
      srLinesRef.current.push(line);
    });
  // candles 加入 deps：每次 chart 重建後重新畫 SR 線
  }, [activeIndicators.sr, sr, candles]);

  // ── Live last-candle update (daily mode only) ─────────────────────────────
  // When quote arrives with today's OHLC, patch the last bar in-place so it
  // reflects the current session without rebuilding the entire chart.
  useEffect(() => {
    const cs = seriesRef.current.candle;
    if (!cs || !quote?.price || !candles.length || isIntraday) return;

    const last = candles[candles.length - 1];
    const lastDate = typeof last.date === "number"
      ? new Date(last.date * 1000).toISOString().slice(0, 10)
      : last.date.slice(0, 10);
    const today = new Date().toISOString().slice(0, 10);
    if (lastDate !== today) return;   // market hasn't opened today yet

    cs.update({
      time:  toTime(last.date),
      open:  quote.day_open  ?? last.open,
      high:  quote.day_high != null ? Math.max(last.high, quote.day_high) : last.high,
      low:   quote.day_low  != null ? Math.min(last.low,  quote.day_low)  : last.low,
      close: quote.price,
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quote]);

  const toggle = (key) => setActiveIndicators((prev) => ({ ...prev, [key]: !prev[key] }));

  const lastCandle = candles[candles.length - 1];
  const prevClose  = candles.length > 1 ? candles[candles.length - 2].close : lastCandle?.open;

  // Prefer live quote; fall back to last candle
  const displayPrice  = quote?.price      ?? lastCandle?.close;
  const displayChange = quote?.change     ?? (lastCandle ? lastCandle.close - prevClose : 0);
  const displayPct    = quote?.change_pct ?? (prevClose  ? (displayChange / prevClose) * 100 : 0);
  const isLive        = !!quote?.price;

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="px-5 py-4 border-b border-[#30363d] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div>
            <span className="text-lg font-bold text-white">{symbol}</span>
            <span className="ml-2 text-xs text-[#8b949e] uppercase">{market}</span>
          </div>
          {displayPrice != null && (
            <div className="flex items-center gap-3">
              <span className={`text-xl font-mono font-bold ${displayChange >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}`}>
                {displayPrice.toFixed(2)}
              </span>
              <span className={`text-sm font-mono px-2 py-0.5 rounded ${displayChange >= 0 ? "bg-[#26a69a22] text-[#26a69a]" : "bg-[#ef535022] text-[#ef5350]"}`}>
                {displayChange >= 0 ? "▲" : "▼"} {Math.abs(displayChange).toFixed(2)} ({Math.abs(displayPct).toFixed(2)}%)
              </span>
              {isIntraday && (
                <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded bg-[#1f6feb22] border border-[#1f6feb] text-[#58a6ff]">
                  {intradayLoading
                    ? <span className="w-1.5 h-1.5 rounded-full bg-[#58a6ff] animate-pulse inline-block" />
                    : <span className="w-1.5 h-1.5 rounded-full bg-[#26a69a] inline-block" />
                  }
                  {interval}
                  {["1m","5m","15m","60m"].includes(interval) && " · 每分鐘更新"}
                </span>
              )}
              {!isIntraday && isLive && (
                <span className="flex items-center gap-1 text-xs text-[#8b949e]">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#26a69a] animate-pulse inline-block" />
                  即時 {quote.updated_at}
                </span>
              )}
            </div>
          )}
        </div>
        {tooltipInfo && (
          <div className="flex gap-3 text-xs font-mono text-[#8b949e]">
            <span>O <span className="text-white">{tooltipInfo.open?.toFixed(2)}</span></span>
            <span>H <span className="text-[#26a69a]">{tooltipInfo.high?.toFixed(2)}</span></span>
            <span>L <span className="text-[#ef5350]">{tooltipInfo.low?.toFixed(2)}</span></span>
            <span>C <span className="text-white">{tooltipInfo.close?.toFixed(2)}</span></span>
          </div>
        )}
      </div>

      {/* ── Indicator toggles ──────────────────────────────────────────────── */}
      <div className="px-5 py-2 flex flex-wrap gap-2 border-b border-[#21262d]">
        {/* MA / BB / RSI / MACD only meaningful on daily data */}
        {!isIntraday && Object.entries(MA_COLORS).map(([key, color]) => (
          <button
            key={key}
            onClick={() => toggle(key)}
            className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
              activeIndicators[key] ? "border-transparent" : "text-[#8b949e] border-[#30363d]"
            }`}
            style={activeIndicators[key] ? { backgroundColor: color + "33", borderColor: color, color } : {}}
          >
            {key.toUpperCase()}
          </button>
        ))}
        {!isIntraday && (
          <button
            onClick={() => toggle("bb")}
            className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
              activeIndicators.bb ? "bg-[#58a6ff22] border-[#58a6ff] text-[#58a6ff]" : "text-[#8b949e] border-[#30363d]"
            }`}
          >
            Bollinger
          </button>
        )}
        <button
          onClick={() => toggle("volume")}
          className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
            activeIndicators.volume ? "bg-[#30363d] border-[#484f58] text-white" : "text-[#8b949e] border-[#30363d]"
          }`}
        >
          Volume
        </button>
        {!isIntraday && (
          <button
            onClick={() => setShowRSI((v) => !v)}
            className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
              showRSI ? "bg-[#a78bfa22] border-[#a78bfa] text-[#a78bfa]" : "text-[#8b949e] border-[#30363d]"
            }`}
          >
            RSI
          </button>
        )}
        {!isIntraday && (
          <button
            onClick={() => setShowMACD((v) => !v)}
            className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
              showMACD ? "bg-[#fb923c22] border-[#fb923c] text-[#fb923c]" : "text-[#8b949e] border-[#30363d]"
            }`}
          >
            MACD
          </button>
        )}
        <button
          onClick={() => toggle("sr")}
          className={`px-3 py-1 rounded text-xs font-medium transition-all border ${
            activeIndicators.sr
              ? "bg-[#f0b42922] border-[#f0b429] text-[#f0b429]"
              : "text-[#8b949e] border-[#30363d]"
          }`}
          title={`支撐 ${sr?.support?.length ?? 0} 條 ／ 壓力 ${sr?.resistance?.length ?? 0} 條`}
        >
          S/R
        </button>
      </div>

      {/* ── Main K-line chart ───────────────────────────────────────────────── */}
      <div ref={containerRef} className="w-full" />

      {/* ── RSI sub-chart ──────────────────────────────────────────────────── */}
      {showRSI && indicators.rsi?.length > 0 && <RSIPanel data={indicators.rsi} />}

      {/* ── MACD sub-chart (key: macd.line / macd.hist) ─────────────────────── */}
      {showMACD && indicators.macd?.line?.length > 0 && <MACDPanel data={indicators.macd} />}
    </div>
  );
}

/* ── RSI sub-chart ─────────────────────────────────────────────────────────── */
function RSIPanel({ data }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      width:  ref.current.clientWidth,
      height: 120,
      layout: { background: { color: "#161b22" }, textColor: "#8b949e" },
      grid:   { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      rightPriceScale: { borderColor: "#30363d", scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale:       { borderColor: "#30363d", timeVisible: true },
    });

    const rsiSeries = chart.addLineSeries({ color: "#a78bfa", lineWidth: 1.5, priceLineVisible: false });
    rsiSeries.setData(data.map((p) => ({ time: p.date, value: p.value })));

    const times = data.map((p) => p.date);
    const ob = chart.addLineSeries({ color: "#ef535066", lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
    const os = chart.addLineSeries({ color: "#26a69a66", lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
    ob.setData(times.map((t) => ({ time: t, value: 70 })));
    os.setData(times.map((t) => ({ time: t, value: 30 })));

    chart.timeScale().fitContent();
    const resize = () => chart.applyOptions({ width: ref.current?.clientWidth || 600 });
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.remove(); };
  }, [data]);

  return (
    <div className="border-t border-[#21262d]">
      <div className="px-5 py-1 text-xs text-[#a78bfa] font-medium">RSI (14)</div>
      <div ref={ref} className="w-full" />
    </div>
  );
}

/* ── MACD sub-chart ────────────────────────────────────────────────────────── */
function MACDPanel({ data }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      width:  ref.current.clientWidth,
      height: 120,
      layout: { background: { color: "#161b22" }, textColor: "#8b949e" },
      grid:   { vertLines: { color: "#21262d" }, horzLines: { color: "#21262d" } },
      rightPriceScale: { borderColor: "#30363d" },
      timeScale:       { borderColor: "#30363d", timeVisible: true },
    });

    // data shape: { line, signal, hist }  ← from /api/stock/{symbol}/indicators
    const lineSeries   = chart.addLineSeries({ color: "#38bdf8", lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
    const signalSeries = chart.addLineSeries({ color: "#f0b429", lineWidth: 1.5, priceLineVisible: false, lastValueVisible: false });
    const histSeries   = chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false });

    lineSeries.setData(data.line.map((p) => ({ time: p.date, value: p.value })));
    signalSeries.setData(data.signal.map((p) => ({ time: p.date, value: p.value })));
    histSeries.setData(
      data.hist.map((p) => ({ time: p.date, value: p.value, color: p.value >= 0 ? "#26a69a88" : "#ef535088" }))
    );

    chart.timeScale().fitContent();
    const resize = () => chart.applyOptions({ width: ref.current?.clientWidth || 600 });
    window.addEventListener("resize", resize);
    return () => { window.removeEventListener("resize", resize); chart.remove(); };
  }, [data]);

  return (
    <div className="border-t border-[#21262d]">
      <div className="px-5 py-1 text-xs text-[#fb923c] font-medium">MACD (12, 26, 9)</div>
      <div ref={ref} className="w-full" />
    </div>
  );
}
