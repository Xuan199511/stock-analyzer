import { Card, MetricCard, Row, Badge, fmt } from "./shared";

function AlignmentBadge({ alignment }) {
  const map = {
    bullish: { tone: "positive", label: "多頭排列" },
    bearish: { tone: "negative", label: "空頭排列" },
    mixed:   { tone: "neutral",  label: "盤整" },
  };
  const cfg = map[alignment] || map.mixed;
  return <Badge tone={cfg.tone}>{cfg.label}</Badge>;
}

function VolumeBadge({ status }) {
  const map = {
    heavy:  { tone: "info",    label: "爆量" },
    normal: { tone: "neutral", label: "均量" },
    light:  { tone: "warn",    label: "量縮" },
  };
  const cfg = map[status] || map.normal;
  return <Badge tone={cfg.tone}>{cfg.label}</Badge>;
}

function RSIStatus({ rsi }) {
  if (rsi === null || rsi === undefined) return null;
  if (rsi >= 70) return <Badge tone="negative">超買</Badge>;
  if (rsi <= 30) return <Badge tone="positive">超賣</Badge>;
  return <Badge tone="neutral">中性</Badge>;
}

function MACDStatus({ macd }) {
  const h = macd?.hist;
  if (h === null || h === undefined) return null;
  if (h > 0) return <Badge tone="positive">柱狀體為正（偏多）</Badge>;
  if (h < 0) return <Badge tone="negative">柱狀體為負（偏空）</Badge>;
  return <Badge tone="neutral">中性</Badge>;
}

function SRList({ title, levels, tone }) {
  return (
    <div>
      <div className="text-xs text-[#8b949e] mb-1">{title}</div>
      {levels?.length ? (
        <div className="flex flex-wrap gap-1">
          {levels.map((v, i) => (
            <Badge key={i} tone={tone}>{fmt(v)}</Badge>
          ))}
        </div>
      ) : (
        <span className="text-xs text-[#484f58]">—</span>
      )}
    </div>
  );
}

export default function TechnicalCard({ technical }) {
  if (!technical) return null;
  const t = technical;
  const flow = t.institutional_flow || {};

  return (
    <Card
      title="三、技術面分析"
      icon="📈"
      right={<AlignmentBadge alignment={t.ma_alignment} />}
    >
      {/* Price & change */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        <MetricCard
          label="現價"
          value={fmt(t.current_price)}
          sub={
            t.price_change_pct !== null && t.price_change_pct !== undefined
              ? <span className={t.price_change_pct >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
                  {t.price_change_pct >= 0 ? "▲" : "▼"} {Math.abs(t.price_change_pct).toFixed(2)}%
                </span>
              : null
          }
          accent
        />
        <MetricCard label="52 週高"  value={fmt(t.week_52_high)} />
        <MetricCard label="52 週低"  value={fmt(t.week_52_low)} />
        <MetricCard label="RSI(14)"  value={fmt(t.rsi)} sub={<RSIStatus rsi={t.rsi} />} />
      </div>

      {/* Moving averages */}
      <div className="mb-4">
        <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-1">均線</div>
        <div className="bg-[#21262d] rounded-xl px-4">
          <Row label="MA5"   value={fmt(t.ma5)} />
          <Row label="MA20"  value={fmt(t.ma20)} />
          <Row label="MA60"  value={fmt(t.ma60)} />
          <Row label="MA240" value={fmt(t.ma240)} />
        </div>
      </div>

      {/* Oscillators */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-[#21262d] rounded-xl p-3">
          <div className="text-xs text-[#8b949e] mb-2 uppercase tracking-wider">KD</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-lg font-mono text-white">K {fmt(t.kd_k)}</span>
            <span className="text-lg font-mono text-[#8b949e]">D {fmt(t.kd_d)}</span>
          </div>
          {t.kd_k !== null && t.kd_k !== undefined && (
            <span className="text-xs text-[#8b949e]">
              {t.kd_k > 80 ? "高檔鈍化" : t.kd_k < 20 ? "低檔鈍化" : t.kd_k > t.kd_d ? "黃金交叉傾向" : "死亡交叉傾向"}
            </span>
          )}
        </div>
        <div className="bg-[#21262d] rounded-xl p-3">
          <div className="text-xs text-[#8b949e] mb-2 uppercase tracking-wider">MACD</div>
          <div className="flex items-baseline gap-2 mb-1">
            <span className="text-lg font-mono text-white">{fmt(t.macd?.macd)}</span>
            <span className="text-xs text-[#8b949e]">柱 {fmt(t.macd?.hist)}</span>
          </div>
          <MACDStatus macd={t.macd} />
        </div>
      </div>

      {/* S/R */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <SRList title="支撐區" levels={t.support_levels} tone="positive" />
        <SRList title="壓力區" levels={t.resistance_levels} tone="negative" />
      </div>

      {/* Volume + Institutional */}
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className="text-xs text-[#8b949e]">量能：</span>
        <VolumeBadge status={t.volume_status} />
      </div>

      {(flow.foreign !== null && flow.foreign !== undefined) && (
        <div className="bg-[#21262d] rounded-xl px-4 mt-2">
          <div className="text-xs text-[#8b949e] py-2 border-b border-[#30363d]">
            近 {flow.period_days} 日三大法人（張）
          </div>
          <Row label="外資"     value={fmt(flow.foreign,    { dp: 0 })} />
          <Row label="投信"     value={fmt(flow.investment, { dp: 0 })} />
          <Row label="自營商"   value={fmt(flow.dealer,     { dp: 0 })} />
        </div>
      )}
    </Card>
  );
}
