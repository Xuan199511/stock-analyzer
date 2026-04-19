import { Card, Badge } from "./shared";

const DIMS = [
  { key: "technical_barrier",     label: "技術壁壘" },
  { key: "certification_barrier", label: "認證壁壘" },
  { key: "scale_economy",         label: "規模經濟" },
  { key: "switching_cost",        label: "轉換成本" },
  { key: "network_effect",        label: "網路效應" },
];

const REPLACE_MAP = {
  near_monopoly: { tone: "positive", label: "近乎獨佔" },
  hard:          { tone: "info",     label: "難以取代" },
  partial:       { tone: "neutral",  label: "部分護城河" },
  easily:        { tone: "warn",     label: "易被取代" },
};

function ScoreBar({ score }) {
  const pct = Math.max(0, Math.min(100, (score / 5) * 100));
  const color = score >= 4 ? "#26a69a" : score >= 3 ? "#58a6ff" : score >= 2 ? "#f0b429" : "#ef5350";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-[#21262d] rounded overflow-hidden">
        <div
          className="h-full rounded transition-[width] duration-700 ease-out"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="w-6 text-right font-mono text-xs" style={{ color }}>{score}</span>
    </div>
  );
}

function RadarChart({ dims }) {
  const size = 180;
  const cx = size / 2, cy = size / 2;
  const radius = size / 2 - 18;
  const n = dims.length;
  const angle = i => (-Math.PI / 2) + (i * 2 * Math.PI / n);
  const pt = (i, v) => {
    const r = radius * (v / 5);
    return [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))];
  };
  const poly = dims.map((d, i) => pt(i, d.value).join(",")).join(" ");

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[220px]">
      {[1, 2, 3, 4, 5].map(s => (
        <polygon
          key={s}
          points={dims.map((_, i) => {
            const r = radius * (s / 5);
            return [cx + r * Math.cos(angle(i)), cy + r * Math.sin(angle(i))].join(",");
          }).join(" ")}
          fill="none" stroke="#30363d" strokeWidth="0.5"
        />
      ))}
      {dims.map((_, i) => {
        const [x, y] = pt(i, 5);
        return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#30363d" strokeWidth="0.5" />;
      })}
      <polygon className="radar-poly" points={poly} fill="#58a6ff33" stroke="#58a6ff" strokeWidth="1.5" />
      {dims.map((d, i) => {
        const [x, y] = pt(i, 5.6);
        return (
          <text key={i} x={x} y={y} textAnchor="middle" dominantBaseline="middle"
                fontSize="9" fill="#8b949e">{d.label}</text>
        );
      })}
    </svg>
  );
}

export default function MoatCard({ moat }) {
  if (!moat) return null;
  const replace = REPLACE_MAP[moat.replaceability] || REPLACE_MAP.partial;
  const dims = DIMS.map(d => ({ ...d, value: moat[d.key] ?? 1 }));

  return (
    <Card
      title="七、獨佔性與護城河"
      icon="🏰"
      right={
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#8b949e]">綜合 {moat.overall_score?.toFixed(1)}</span>
          <Badge tone={replace.tone}>{replace.label}</Badge>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
        <div className="flex justify-center"><RadarChart dims={dims} /></div>
        <div className="flex flex-col gap-3">
          {dims.map(d => (
            <div key={d.key}>
              <div className="text-xs text-[#8b949e] mb-1">{d.label}</div>
              <ScoreBar score={d.value} />
            </div>
          ))}
        </div>
      </div>
      {moat.narrative && (
        <p className="mt-4 text-xs text-[#8b949e] leading-relaxed">{moat.narrative}</p>
      )}
    </Card>
  );
}
