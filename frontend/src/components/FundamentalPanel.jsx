/**
 * FundamentalPanel — 基本面分析面板
 *
 * Props:
 *   data: {
 *     symbol, market,
 *     metrics: { pe_ratio, pb_ratio, forward_pe, eps, roe, gross_margin,
 *                profit_margin, dividend_yield, market_cap, 52w_high,
 *                52w_low, revenue, name, sector, description },
 *     eps_quarterly:  [{date, period, value}, ...],  // 最近 8 季
 *     revenue_trend:  [{date, period, value}, ...],  // TW=月, US=季
 *   }
 */

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(value, { pct = false, bn = false, dp = 2 } = {}) {
  if (value === null || value === undefined || isNaN(value)) return "—";
  const n = Number(value);
  if (pct)  return `${(n * 100).toFixed(dp)}%`;
  if (bn) {
    if (Math.abs(n) >= 1e12) return `${(n / 1e12).toFixed(2)} T`;
    if (Math.abs(n) >= 1e9)  return `${(n / 1e9).toFixed(2)} B`;
    if (Math.abs(n) >= 1e6)  return `${(n / 1e6).toFixed(2)} M`;
  }
  return n.toFixed(dp);
}

// ── Metric Card ───────────────────────────────────────────────────────────────

function MetricCard({ label, value, sub = null, accent = false }) {
  const isEmpty = value === null || value === undefined || value === "—";
  return (
    <div className="bg-[#21262d] rounded-xl p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-[#8b949e] truncate">{label}</span>
      <span className={`text-xl font-mono font-bold truncate ${accent ? "text-[#58a6ff]" : isEmpty ? "text-[#484f58]" : "text-white"}`}>
        {isEmpty ? "—" : value}
      </span>
      {sub && <span className="text-xs text-[#8b949e] truncate">{sub}</span>}
    </div>
  );
}

// ── Metric Row (table style) ──────────────────────────────────────────────────

function MetricRow({ label, value }) {
  if (value === null || value === undefined || value === "—") return null;
  return (
    <div className="flex justify-between items-center py-2 border-b border-[#21262d] last:border-0">
      <span className="text-sm text-[#8b949e]">{label}</span>
      <span className="text-sm font-mono text-white">{value}</span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-5">
      <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">{title}</h3>
      {children}
    </div>
  );
}

// ── EPS Bar Chart (SVG, pure — no extra dependencies) ────────────────────────

function EpsBarChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-[#484f58] text-center py-6">無季度 EPS 資料</p>;
  }

  const W = 420, H = 160;
  const PAD = { top: 28, right: 8, bottom: 34, left: 4 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const values   = data.map((d) => d.value);
  const maxVal   = Math.max(0, ...values);
  const minVal   = Math.min(0, ...values);
  const range    = maxVal - minVal || 1;

  // y = PAD.top at maxVal, y = PAD.top + innerH at minVal
  const yFor   = (v) => PAD.top + innerH * (maxVal - v) / range;
  const zeroY  = yFor(0);

  const colW   = innerW / data.length;
  const barW   = Math.max(colW * 0.55, 6);

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      preserveAspectRatio="xMidYMid meet"
      aria-label="近8季 EPS"
    >
      {/* Zero baseline */}
      <line x1={PAD.left} y1={zeroY} x2={W - PAD.right} y2={zeroY}
            stroke="#30363d" strokeWidth="1" />

      {data.map((d, i) => {
        const cx    = PAD.left + colW * (i + 0.5);
        const barH  = Math.max(Math.abs(yFor(d.value) - zeroY), 2);
        const barY  = d.value >= 0 ? zeroY - barH : zeroY;
        const color = d.value >= 0 ? "#26a69a" : "#ef5350";
        const lblY  = d.value >= 0 ? barY - 5 : barY + barH + 13;

        return (
          <g key={i}>
            <rect x={cx - barW / 2} y={barY} width={barW} height={barH}
                  fill={color} opacity="0.85" rx="2" />
            {/* Value label */}
            <text x={cx} y={lblY} textAnchor="middle" fontSize="9" fill={color}>
              {d.value.toFixed(1)}
            </text>
            {/* Period label */}
            <text x={cx} y={H - 4} textAnchor="middle" fontSize="8.5" fill="#6e7681">
              {d.period}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Revenue Line Chart (SVG) ──────────────────────────────────────────────────

function RevenueLineChart({ data }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-[#484f58] text-center py-6">無營收資料</p>;
  }

  const W = 420, H = 130;
  const PAD = { top: 16, right: 8, bottom: 28, left: 4 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const values  = data.map((d) => d.value);
  const maxVal  = Math.max(...values);
  const minVal  = Math.min(...values);
  const range   = maxVal - minVal || 1;

  const xFor = (i) => PAD.left + (data.length > 1 ? (i / (data.length - 1)) * innerW : innerW / 2);
  const yFor = (v) => PAD.top + innerH * (maxVal - v) / range;

  const pts  = data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.value).toFixed(1)}`).join(" ");
  const area = [
    `${xFor(0).toFixed(1)},${(PAD.top + innerH).toFixed(1)}`,
    ...data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.value).toFixed(1)}`),
    `${xFor(data.length - 1).toFixed(1)},${(PAD.top + innerH).toFixed(1)}`,
  ].join(" ");

  // Show at most 6 labels to avoid crowding
  const step = Math.max(1, Math.ceil(data.length / 6));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      preserveAspectRatio="xMidYMid meet"
      aria-label="營收趨勢"
    >
      <defs>
        <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#1f6feb" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#1f6feb" stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Area */}
      <polygon points={area} fill="url(#revGrad)" />
      {/* Line */}
      <polyline points={pts} fill="none" stroke="#58a6ff" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      {/* Dots */}
      {data.map((d, i) => (
        <circle key={i} cx={xFor(i)} cy={yFor(d.value)} r="2.5" fill="#58a6ff" />
      ))}
      {/* X-axis labels */}
      {data.map((d, i) =>
        i % step === 0 ? (
          <text key={i} x={xFor(i)} y={H - 4} textAnchor="middle" fontSize="8.5" fill="#6e7681">
            {(d.period || d.date || "").slice(-5)}
          </text>
        ) : null
      )}
    </svg>
  );
}

// ── YoY change badge ─────────────────────────────────────────────────────────

function YoYBadge({ current, prev }) {
  if (!current || !prev || prev === 0) return null;
  const pct = ((current - prev) / Math.abs(prev)) * 100;
  const up  = pct >= 0;
  return (
    <span className={`text-xs font-mono px-1.5 py-0.5 rounded ${up ? "bg-[#26a69a22] text-[#26a69a]" : "bg-[#ef535022] text-[#ef5350]"}`}>
      {up ? "▲" : "▼"} {Math.abs(pct).toFixed(1)}%
    </span>
  );
}

// ── US Fundamentals ───────────────────────────────────────────────────────────

function USFundamental({ metrics, eps_quarterly, revenue_trend }) {
  const m = metrics;
  const latestEps  = eps_quarterly?.[eps_quarterly.length - 1]?.value;
  const prevEps    = eps_quarterly?.[eps_quarterly.length - 5]?.value; // YoY (4 quarters ago)
  const latestRev  = revenue_trend?.[revenue_trend.length - 1]?.value;
  const prevRev    = revenue_trend?.[revenue_trend.length - 5]?.value;

  return (
    <div>
      {/* Description */}
      {m.description && (
        <p className="text-xs text-[#8b949e] mb-5 leading-relaxed line-clamp-2">{m.description}</p>
      )}

      {/* ── Key Metric Cards (2×2) ── */}
      <Section title="關鍵指標">
        <div className="grid grid-cols-2 gap-2 mb-1">
          <MetricCard label="本益比 (P/E)" value={fmt(m.pe_ratio)} sub={`預期 ${fmt(m.forward_pe)}`} accent />
          <MetricCard label="每股盈餘 (EPS)" value={`$${fmt(m.eps)}`}
            sub={<YoYBadge current={latestEps} prev={prevEps} />} accent />
          <MetricCard label="股東權益報酬率 (ROE)" value={fmt(m.roe, { pct: true })} accent />
          <MetricCard label="毛利率" value={fmt(m.gross_margin, { pct: true })} accent />
        </div>
      </Section>

      {/* ── EPS Bar Chart ── */}
      <Section title={`近 ${eps_quarterly.length} 季 EPS`}>
        <div className="bg-[#21262d] rounded-xl p-3">
          <EpsBarChart data={eps_quarterly} />
        </div>
      </Section>

      {/* ── Revenue Trend ── */}
      <Section title={`近 ${revenue_trend.length} 季營收`}>
        <div className="bg-[#21262d] rounded-xl p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[#8b949e]">最新: {fmt(latestRev, { bn: true })}</span>
            <YoYBadge current={latestRev} prev={prevRev} />
          </div>
          <RevenueLineChart data={revenue_trend} />
        </div>
      </Section>

      {/* ── Other Metrics ── */}
      <Section title="其他指標">
        <div className="bg-[#21262d] rounded-xl px-4">
          <MetricRow label="市值"       value={fmt(m.market_cap,    { bn: true })} />
          <MetricRow label="52週最高"   value={`$${fmt(m["52w_high"])}`} />
          <MetricRow label="52週最低"   value={`$${fmt(m["52w_low"])}`} />
          <MetricRow label="淨利率"     value={fmt(m.profit_margin,  { pct: true })} />
          <MetricRow label="ROA"        value={fmt(m.roa,            { pct: true })} />
          <MetricRow label="殖利率"     value={fmt(m.dividend_yield, { pct: true })} />
          <MetricRow label="年營收"     value={fmt(m.revenue,        { bn: true })} />
          <MetricRow label="產業"       value={m.sector} />
        </div>
      </Section>
    </div>
  );
}

// ── TW Fundamentals ───────────────────────────────────────────────────────────

function TWFundamental({ metrics, eps_quarterly, revenue_trend }) {
  const m = metrics;
  const latestEps = eps_quarterly?.[eps_quarterly.length - 1]?.value;
  const prevEps   = eps_quarterly?.[eps_quarterly.length - 5]?.value;
  const latestRev = revenue_trend?.[revenue_trend.length - 1]?.value;
  const prevRev   = revenue_trend?.[revenue_trend.length - 13]?.value; // YoY for monthly

  return (
    <div>
      {/* ── Key Metric Cards (2×2) ── */}
      <Section title="關鍵指標">
        <div className="grid grid-cols-2 gap-2 mb-1">
          <MetricCard label="本益比 (PER)" value={fmt(m.pe_ratio)} accent />
          <MetricCard label="每股盈餘 (EPS)" value={latestEps !== undefined ? `${fmt(latestEps)} 元` : "—"}
            sub={<YoYBadge current={latestEps} prev={prevEps} />} accent />
          <MetricCard label="股價淨值比 (PBR)" value={fmt(m.pb_ratio)} accent />
          <MetricCard label="殖利率" value={fmt(m.dividend_yield, { dp: 2 })} sub="%" accent />
        </div>
      </Section>

      {/* ── EPS Bar Chart ── */}
      <Section title={`近 ${eps_quarterly.length} 季 EPS（元）`}>
        <div className="bg-[#21262d] rounded-xl p-3">
          <EpsBarChart data={eps_quarterly} />
        </div>
      </Section>

      {/* ── Monthly Revenue Line Chart ── */}
      <Section title="近 12 月營收趨勢">
        <div className="bg-[#21262d] rounded-xl p-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[#8b949e]">最新: {fmt(latestRev, { bn: true })}</span>
            <YoYBadge current={latestRev} prev={prevRev} />
          </div>
          <RevenueLineChart data={revenue_trend} />
        </div>
      </Section>
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export default function FundamentalPanel({ data }) {
  const { symbol, market, metrics = {}, eps_quarterly = [], revenue_trend = [] } = data;

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2">
        <span className="text-base">📋</span>
        <h2 className="font-semibold text-white">基本面分析</h2>
        {metrics.name && (
          <span className="text-xs text-[#8b949e] hidden sm:inline truncate max-w-[140px]">{metrics.name}</span>
        )}
        <span className="ml-auto text-xs text-[#8b949e] uppercase shrink-0">{symbol} · {market}</span>
      </div>

      {/* Body */}
      <div className="p-5 overflow-y-auto max-h-[680px]">
        {market === "US" || market === "us" ? (
          <USFundamental metrics={metrics} eps_quarterly={eps_quarterly} revenue_trend={revenue_trend} />
        ) : (
          <TWFundamental metrics={metrics} eps_quarterly={eps_quarterly} revenue_trend={revenue_trend} />
        )}
      </div>
    </div>
  );
}
