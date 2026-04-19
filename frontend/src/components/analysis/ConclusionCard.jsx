import { Card, Badge, MetricCard, fmt } from "./shared";

const PROFILE = {
  conservative: { tone: "info",     label: "保守型" },
  moderate:     { tone: "neutral",  label: "穩健型" },
  aggressive:   { tone: "warn",     label: "積極型" },
};

function BulletList({ items, icon, tone = "neutral" }) {
  if (!items || items.length === 0) {
    return <p className="text-xs text-[#484f58]">—</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((t, i) => (
        <li key={i} className="flex gap-2 items-start text-sm">
          <span className="shrink-0 mt-0.5">{icon}</span>
          <span className="text-[#c9d1d9]">{t}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ConclusionCard({ conclusion, currentPrice }) {
  if (!conclusion) return null;
  const profile = PROFILE[conclusion.investor_profile] || PROFILE.moderate;
  const entry = conclusion.entry_range || {};
  const hasEntry = entry.low || entry.high;
  const upsideLow  = entry.low && currentPrice  ? ((entry.low - currentPrice) / currentPrice) * 100 : null;
  const upsideHigh = entry.high && currentPrice ? ((entry.high - currentPrice) / currentPrice) * 100 : null;

  return (
    <Card
      title="九、綜合結論與操作建議"
      icon="🧭"
      right={<Badge tone={profile.tone}>{profile.label}</Badge>}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="bg-[#21262d] rounded-xl p-4 border-l-4 border-[#26a69a]">
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">✨ 投資亮點</div>
          <BulletList items={conclusion.highlights} icon="✅" />
        </div>
        <div className="bg-[#21262d] rounded-xl p-4 border-l-4 border-[#ef5350]">
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">⚠️ 主要風險</div>
          <BulletList items={conclusion.risks} icon="🔻" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        {[
          { label: "短線 (1-3M)", val: conclusion.short_term_view, icon: "🎯" },
          { label: "中期 (3-12M)", val: conclusion.mid_term_view,   icon: "📊" },
          { label: "長期 (1-3Y)",  val: conclusion.long_term_view,  icon: "🏗️" },
        ].map((v, i) => (
          <div key={i} className="bg-[#21262d] rounded-xl p-3">
            <div className="text-xs text-[#8b949e] mb-2">{v.icon} {v.label}</div>
            <p className="text-sm text-[#c9d1d9] leading-relaxed">{v.val || "—"}</p>
          </div>
        ))}
      </div>

      {(hasEntry || conclusion.stop_loss) && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
          <MetricCard
            label="建議進場下緣"
            value={fmt(entry.low)}
            sub={upsideLow !== null
              ? <span className={upsideLow >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
                  {upsideLow >= 0 ? "+" : ""}{upsideLow.toFixed(1)}%
                </span>
              : null}
            accent
          />
          <MetricCard
            label="建議進場上緣"
            value={fmt(entry.high)}
            sub={upsideHigh !== null
              ? <span className={upsideHigh >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"}>
                  {upsideHigh >= 0 ? "+" : ""}{upsideHigh.toFixed(1)}%
                </span>
              : null}
            accent
          />
          <MetricCard label="停損參考" value={fmt(conclusion.stop_loss)} />
          <MetricCard label="目前價" value={fmt(currentPrice)} />
        </div>
      )}

      {conclusion.disclaimer && (
        <p className="text-xs text-[#6e7681] italic text-center mt-2">
          {conclusion.disclaimer}
        </p>
      )}
    </Card>
  );
}
