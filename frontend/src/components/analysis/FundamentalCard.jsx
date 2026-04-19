import { Card, MetricCard, Row, fmt, Badge } from "./shared";

function BarChart({ data, unit = "" }) {
  if (!data || data.length === 0) {
    return <p className="text-xs text-[#484f58] text-center py-6">無資料</p>;
  }
  const W = 420, H = 150;
  const PAD = { top: 28, right: 8, bottom: 32, left: 4 };
  const iW = W - PAD.left - PAD.right;
  const iH = H - PAD.top - PAD.bottom;
  const values = data.map(d => d.value);
  const maxVal = Math.max(0, ...values);
  const minVal = Math.min(0, ...values);
  const range = maxVal - minVal || 1;
  const yFor = v => PAD.top + iH * (maxVal - v) / range;
  const zeroY = yFor(0);
  const colW = iW / data.length;
  const barW = Math.max(colW * 0.55, 6);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
      <line x1={PAD.left} y1={zeroY} x2={W - PAD.right} y2={zeroY} stroke="#30363d" />
      {data.map((d, i) => {
        const cx   = PAD.left + colW * (i + 0.5);
        const barH = Math.max(Math.abs(yFor(d.value) - zeroY), 2);
        const barY = d.value >= 0 ? zeroY - barH : zeroY;
        const color = d.value >= 0 ? "#26a69a" : "#ef5350";
        const lblY = d.value >= 0 ? barY - 5 : barY + barH + 12;
        const scale = Math.abs(d.value) >= 1e9 ? 1e9 : Math.abs(d.value) >= 1e6 ? 1e6 : 1;
        const scaleSuffix = scale === 1e9 ? "B" : scale === 1e6 ? "M" : "";
        const display = scale === 1 ? d.value.toFixed(2) : (d.value / scale).toFixed(1) + scaleSuffix;
        return (
          <g key={i}>
            <rect x={cx - barW / 2} y={barY} width={barW} height={barH} fill={color} opacity="0.85" rx="2" />
            <text x={cx} y={lblY} textAnchor="middle" fontSize="9" fill={color}>{display}</text>
            <text x={cx} y={H - 4} textAnchor="middle" fontSize="9" fill="#6e7681">{d.period}</text>
          </g>
        );
      })}
      {unit && <text x={W - 6} y={12} textAnchor="end" fontSize="9" fill="#6e7681">{unit}</text>}
    </svg>
  );
}

function VerdictBadge({ verdict }) {
  const map = {
    undervalued: { tone: "positive", label: "評價偏低" },
    fair:        { tone: "neutral",  label: "合理估值" },
    overvalued:  { tone: "negative", label: "評價偏高" },
  };
  const cfg = map[verdict] || map.fair;
  return <Badge tone={cfg.tone}>{cfg.label}</Badge>;
}

export default function FundamentalCard({ fundamental }) {
  if (!fundamental) return null;
  const f = fundamental;

  return (
    <Card
      title="二、基本面分析"
      icon="💰"
      right={<VerdictBadge verdict={f.valuation_verdict} />}
    >
      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        <MetricCard label="本益比 (P/E)"     value={fmt(f.pe_ratio)} accent />
        <MetricCard label="股價淨值比 (P/B)" value={fmt(f.pb_ratio)} accent />
        <MetricCard label="殖利率"           value={fmt(f.dividend_yield, { pct: true })} accent />
        <MetricCard label="ROE"              value={fmt(f.roe, { pct: true })} accent />
      </div>

      {/* EPS */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className="text-xs text-[#8b949e] uppercase tracking-wider">近 5 年 EPS</span>
          {f.eps_history?.length > 1 && (
            <span className="text-xs text-[#8b949e]">
              最新 {fmt(f.eps_history[f.eps_history.length - 1].value)}
            </span>
          )}
        </div>
        <div className="bg-[#21262d] rounded-xl p-3">
          <BarChart data={f.eps_history} />
        </div>
      </div>

      {/* Revenue */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className="text-xs text-[#8b949e] uppercase tracking-wider">近 5 年營收</span>
          {f.revenue_history?.length > 1 && (
            <span className="text-xs text-[#8b949e]">
              最新 {fmt(f.revenue_history[f.revenue_history.length - 1].value, { bn: true })}
            </span>
          )}
        </div>
        <div className="bg-[#21262d] rounded-xl p-3">
          <BarChart data={f.revenue_history} />
        </div>
      </div>

      {/* Other metrics */}
      <div className="bg-[#21262d] rounded-xl px-4">
        <Row label="毛利率"         value={fmt(f.gross_margin,     { pct: true })} />
        <Row label="營業利益率"     value={fmt(f.operating_margin, { pct: true })} />
        <Row label="淨利率"         value={fmt(f.net_margin,       { pct: true })} />
        <Row label="負債權益比"     value={fmt(f.debt_ratio)} />
        <Row label="自由現金流"     value={fmt(f.free_cash_flow,   { bn: true })} />
        <Row label="同業 P/E 均值" value={fmt(f.peer_pe_comparison?.avg)} />
      </div>
    </Card>
  );
}
