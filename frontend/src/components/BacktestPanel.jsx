/**
 * BacktestPanel — 策略回測面板
 *
 * 包含：
 *   - 策略參數設定表單
 *   - 績效統計卡片
 *   - 淨值曲線（SVG AreaChart）
 *   - 交易紀錄表格
 */
import { useState } from "react";
import axios from "axios";

// ── Constants ─────────────────────────────────────────────────────────────────

const STRATEGIES = [
  { value: "ma_cross", label: "均線交叉 (MA Cross)" },
  { value: "rsi",      label: "RSI 超買超賣" },
  { value: "macd",     label: "MACD 交叉" },
  { value: "bb",       label: "布林帶 (Bollinger Bands)" },
];

const PARAM_DEFS = {
  ma_cross: [
    { key: "fast", label: "快線週期", default: 20, min: 2,  max: 200 },
    { key: "slow", label: "慢線週期", default: 60, min: 5,  max: 500 },
  ],
  rsi: [
    { key: "period",     label: "RSI 週期",   default: 14, min: 2,  max: 100 },
    { key: "oversold",   label: "超賣門檻",   default: 30, min: 5,  max: 49  },
    { key: "overbought", label: "超買門檻",   default: 70, min: 51, max: 95  },
  ],
  macd: [
    { key: "fast",   label: "快線 EMA", default: 12, min: 2,  max: 100 },
    { key: "slow",   label: "慢線 EMA", default: 26, min: 5,  max: 200 },
    { key: "signal", label: "訊號線",   default: 9,  min: 2,  max: 50  },
  ],
  bb: [
    { key: "period",  label: "均線週期", default: 20,  min: 5,   max: 200 },
    { key: "std_dev", label: "標準差倍數", default: 2.0, min: 0.5, max: 5.0, step: 0.1 },
  ],
};

const DEFAULT_FORM = {
  symbol:          "2330",
  market:          "TW",
  strategy:        "ma_cross",
  start_date:      "2022-01-01",
  end_date:        "2024-12-31",
  initial_capital: 100000,
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtNum(v, dp = 2) {
  if (v === null || v === undefined) return "—";
  return Number(v).toFixed(dp);
}

function colorByValue(v) {
  if (v > 0) return "text-[#26a69a]";
  if (v < 0) return "text-[#ef5350]";
  return "text-white";
}

// ── Stat Card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, unit = "", colorClass = "text-white" }) {
  return (
    <div className="bg-[#21262d] rounded-xl p-4 flex flex-col gap-1">
      <span className="text-xs text-[#8b949e]">{label}</span>
      <span className={`text-2xl font-mono font-bold ${colorClass}`}>
        {value}<span className="text-sm font-normal text-[#8b949e] ml-1">{unit}</span>
      </span>
    </div>
  );
}

// ── Equity Curve (SVG Area Chart) ─────────────────────────────────────────────

function EquityCurve({ data, initialCapital }) {
  if (!data || data.length < 2) return null;

  const W = 700, H = 200;
  const PAD = { top: 16, right: 16, bottom: 28, left: 16 };
  const iW  = W - PAD.left - PAD.right;
  const iH  = H - PAD.top  - PAD.bottom;

  const values  = data.map((d) => d.value);
  const maxVal  = Math.max(...values);
  const minVal  = Math.min(...values);
  const range   = maxVal - minVal || 1;

  const xFor = (i) => PAD.left + (i / (data.length - 1)) * iW;
  const yFor = (v) => PAD.top + iH * (maxVal - v) / range;

  const pts  = data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.value).toFixed(1)}`).join(" ");
  const area = [
    `${PAD.left},${(PAD.top + iH).toFixed(1)}`,
    ...data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.value).toFixed(1)}`),
    `${(W - PAD.right).toFixed(1)},${(PAD.top + iH).toFixed(1)}`,
  ].join(" ");

  // Baseline (initial capital)
  const baseY   = yFor(initialCapital).toFixed(1);
  const showBase = initialCapital >= minVal && initialCapital <= maxVal;

  // X-axis date labels (first / quarters / last)
  const labelStep = Math.max(1, Math.floor(data.length / 6));
  const labelIdxs = new Set([0, data.length - 1]);
  for (let i = labelStep; i < data.length - 1; i += labelStep) labelIdxs.add(i);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="淨值曲線">
      <defs>
        <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#1f6feb" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#1f6feb" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Baseline */}
      {showBase && (
        <line x1={PAD.left} y1={baseY} x2={W - PAD.right} y2={baseY}
              stroke="#484f58" strokeWidth="1" strokeDasharray="4 4" />
      )}

      {/* Area fill */}
      <polygon points={area} fill="url(#eqGrad)" />

      {/* Line */}
      <polyline points={pts} fill="none" stroke="#58a6ff"
                strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />

      {/* X-axis labels */}
      {[...labelIdxs].sort((a, b) => a - b).map((i) => (
        <text key={i} x={xFor(i)} y={H - 4} textAnchor="middle" fontSize="9" fill="#6e7681">
          {data[i]?.date?.slice(0, 7)}
        </text>
      ))}
    </svg>
  );
}

// ── Trades Table ──────────────────────────────────────────────────────────────

function TradesTable({ trades }) {
  if (!trades || trades.length === 0) {
    return <p className="text-xs text-[#484f58] text-center py-6">無交易紀錄</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-[#30363d]">
            {["進場日", "出場日", "進場價", "出場價", "損益", "報酬率"].map((h) => (
              <th key={h} className="pb-2 pr-4 text-[#8b949e] font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {trades.map((t, i) => {
            const up = t.pnl >= 0;
            const color = up ? "text-[#26a69a]" : "text-[#ef5350]";
            return (
              <tr key={i} className="border-b border-[#21262d] last:border-0">
                <td className="py-2 pr-4 font-mono text-[#e6edf3]">{t.entry_date}</td>
                <td className="py-2 pr-4 font-mono text-[#e6edf3]">{t.exit_date}</td>
                <td className="py-2 pr-4 font-mono text-[#e6edf3]">{fmtNum(t.entry_price)}</td>
                <td className="py-2 pr-4 font-mono text-[#e6edf3]">{fmtNum(t.exit_price)}</td>
                <td className={`py-2 pr-4 font-mono font-semibold ${color}`}>
                  {up ? "+" : ""}{fmtNum(t.pnl)}
                </td>
                <td className={`py-2 pr-4 font-mono font-semibold ${color}`}>
                  {up ? "+" : ""}{fmtNum(t.return_pct)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Strategy Param Form ───────────────────────────────────────────────────────

function ParamFields({ strategy, params, onChange }) {
  const defs = PARAM_DEFS[strategy] || [];
  return (
    <div className="flex flex-wrap gap-3">
      {defs.map((d) => (
        <div key={d.key} className="flex flex-col gap-1">
          <label className="text-xs text-[#8b949e]">{d.label}</label>
          <input
            type="number"
            min={d.min}
            max={d.max}
            step={d.step || 1}
            value={params[d.key] ?? d.default}
            onChange={(e) => onChange(d.key, d.step ? parseFloat(e.target.value) : parseInt(e.target.value, 10))}
            className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm w-24
                       focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
          />
        </div>
      ))}
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export default function BacktestPanel() {
  const [form,    setForm]    = useState(DEFAULT_FORM);
  const [params,  setParams]  = useState({});
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  const handleField = (key, val) => setForm((f) => ({ ...f, [key]: val }));
  const handleParam = (key, val) => setParams((p) => ({ ...p, [key]: val }));

  const handleStrategyChange = (s) => {
    setForm((f) => ({ ...f, strategy: s }));
    setParams({});   // reset params to defaults when strategy changes
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await axios.post("/api/backtest", {
        ...form,
        params,
        initial_capital: Number(form.initial_capital),
      });
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const r = result;
  const totalRetColor = r ? colorByValue(r.total_return) : "text-white";
  const ddColor       = r ? colorByValue(-Math.abs(r.max_drawdown)) : "text-white";

  return (
    <div className="space-y-6">
      {/* ── Form Panel ──────────────────────────────────────────────────────── */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2">
          <span className="text-base">⚙️</span>
          <h2 className="font-semibold text-white">策略回測設定</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Row 1: market + symbol + dates + capital */}
          <div className="flex flex-wrap gap-3 items-end">
            {/* Market */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e]">市場</label>
              <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
                {["TW", "US"].map((m) => (
                  <button key={m} type="button"
                    onClick={() => handleField("market", m)}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      form.market === m
                        ? "bg-[#1f6feb] text-white"
                        : "bg-[#21262d] text-[#8b949e] hover:text-white"
                    }`}
                  >
                    {m === "TW" ? "🇹🇼 台股" : "🇺🇸 美股"}
                  </button>
                ))}
              </div>
            </div>

            {/* Symbol */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e]">股票代號</label>
              <input
                type="text"
                value={form.symbol}
                onChange={(e) => handleField("symbol", e.target.value.toUpperCase())}
                placeholder={form.market === "TW" ? "e.g. 2330" : "e.g. AAPL"}
                className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm w-28
                           focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
              />
            </div>

            {/* Start date */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e]">開始日期</label>
              <input type="date" value={form.start_date}
                onChange={(e) => handleField("start_date", e.target.value)}
                className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm
                           focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
              />
            </div>

            {/* End date */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e]">結束日期</label>
              <input type="date" value={form.end_date}
                onChange={(e) => handleField("end_date", e.target.value)}
                className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm
                           focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
              />
            </div>

            {/* Initial capital */}
            <div className="flex flex-col gap-1">
              <label className="text-xs text-[#8b949e]">初始資金</label>
              <input type="number" min={1000} step={1000} value={form.initial_capital}
                onChange={(e) => handleField("initial_capital", e.target.value)}
                className="bg-[#21262d] border border-[#30363d] rounded-lg px-3 py-2 text-sm w-32
                           focus:outline-none focus:border-[#1f6feb] focus:ring-1 focus:ring-[#1f6feb]"
              />
            </div>
          </div>

          {/* Row 2: strategy selector */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-[#8b949e]">策略</label>
            <div className="flex flex-wrap gap-2">
              {STRATEGIES.map((s) => (
                <button key={s.value} type="button"
                  onClick={() => handleStrategyChange(s.value)}
                  className={`px-4 py-2 text-sm rounded-lg border transition-colors ${
                    form.strategy === s.value
                      ? "bg-[#1f6feb] border-[#1f6feb] text-white"
                      : "bg-[#21262d] border-[#30363d] text-[#8b949e] hover:text-white hover:border-[#484f58]"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Row 3: dynamic strategy params */}
          <div className="flex flex-col gap-2">
            <label className="text-xs text-[#8b949e]">策略參數</label>
            <ParamFields strategy={form.strategy} params={params} onChange={handleParam} />
          </div>

          {/* Submit */}
          <button type="submit" disabled={loading}
            className="px-6 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "回測中..." : "開始回測"}
          </button>
        </form>
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {error && (
        <div className="bg-[#3d1f1f] border border-[#f85149] rounded-lg p-4 text-[#f85149] text-sm">
          ⚠ {error}
        </div>
      )}

      {/* ── Loading ─────────────────────────────────────────────────────────── */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="spinner" />
          <p className="text-[#8b949e] text-sm">正在執行回測...</p>
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────────────────── */}
      {!loading && r && (
        <div className="space-y-6">
          {/* Stats cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <StatCard label="總報酬率"   value={`${r.total_return > 0 ? "+" : ""}${fmtNum(r.total_return)}`} unit="%" colorClass={totalRetColor} />
            <StatCard label="勝率"       value={fmtNum(r.win_rate)} unit="%" />
            <StatCard label="最大回撤"   value={fmtNum(r.max_drawdown)} unit="%" colorClass={ddColor} />
            <StatCard label="夏普比率"   value={fmtNum(r.sharpe_ratio, 3)} colorClass={r.sharpe_ratio >= 1 ? "text-[#26a69a]" : r.sharpe_ratio < 0 ? "text-[#ef5350]" : "text-white"} />
            <StatCard label="交易次數"   value={r.trade_count} />
          </div>

          {/* Equity curve */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2">
              <span className="text-base">📈</span>
              <h2 className="font-semibold text-white">淨值曲線</h2>
              <span className="ml-auto text-xs text-[#484f58]">虛線 = 初始資金</span>
            </div>
            <div className="p-5">
              <div className="bg-[#21262d] rounded-xl p-3">
                <EquityCurve data={r.equity_curve} initialCapital={form.initial_capital} />
              </div>
            </div>
          </div>

          {/* Trades table */}
          <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2">
              <span className="text-base">📋</span>
              <h2 className="font-semibold text-white">交易紀錄</h2>
              <span className="ml-auto text-xs text-[#8b949e]">{r.trade_count} 筆</span>
            </div>
            <div className="p-5">
              <TradesTable trades={r.trades} />
            </div>
          </div>
        </div>
      )}

      {/* ── Empty state ─────────────────────────────────────────────────────── */}
      {!loading && !r && !error && (
        <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
          <span className="text-5xl mb-4">🔬</span>
          <p className="text-lg">設定策略參數，開始回測</p>
          <p className="text-sm mt-2">支援 MA 均線交叉、RSI、MACD、布林帶四種策略</p>
        </div>
      )}
    </div>
  );
}
