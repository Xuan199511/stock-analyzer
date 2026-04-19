import { Card, MetricCard, fmt, Badge } from "./shared";

const RATING_MAP = {
  buy:  { tone: "positive", label: "買進" },
  hold: { tone: "neutral",  label: "持有" },
  sell: { tone: "negative", label: "賣出" },
};

export default function InstitutionalCard({ consensus, targets, currentPrice }) {
  const hasConsensus = consensus && (consensus.avg || consensus.count > 0);
  const hasTargets = targets && targets.length > 0;

  if (!hasConsensus && !hasTargets) {
    return (
      <Card title="八、外資與法人目標價" icon="🎯">
        <p className="text-sm text-[#6e7681] text-center py-6">查無法人目標價資料（台股覆蓋率有限）</p>
      </Card>
    );
  }

  const upside =
    consensus?.avg && currentPrice
      ? ((consensus.avg - currentPrice) / currentPrice) * 100
      : null;

  return (
    <Card
      title="八、外資與法人目標價"
      icon="🎯"
      right={
        upside !== null
          ? <Badge tone={upside >= 0 ? "positive" : "negative"}>
              {upside >= 0 ? "上檔" : "下檔"} {Math.abs(upside).toFixed(1)}%
            </Badge>
          : null
      }
    >
      {hasConsensus && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
          <MetricCard label="目標價均值" value={fmt(consensus.avg)} accent />
          <MetricCard label="高目標價"   value={fmt(consensus.high)} />
          <MetricCard label="低目標價"   value={fmt(consensus.low)} />
          <MetricCard label="分析師家數" value={consensus.count || "—"} />
        </div>
      )}

      {hasTargets && (
        <div className="bg-[#21262d] rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[#8b949e] text-xs uppercase tracking-wider border-b border-[#30363d]">
                <th className="text-left py-2 px-3">券商</th>
                <th className="text-left py-2 px-3">評等</th>
                <th className="text-right py-2 px-3">目標價</th>
                <th className="text-right py-2 px-3">日期</th>
              </tr>
            </thead>
            <tbody>
              {targets.map((t, i) => {
                const r = RATING_MAP[t.rating] || RATING_MAP.hold;
                return (
                  <tr key={i} className="border-b border-[#30363d] last:border-0">
                    <td className="py-2 px-3 text-white">{t.broker}</td>
                    <td className="py-2 px-3"><Badge tone={r.tone}>{r.label}</Badge></td>
                    <td className="py-2 px-3 text-right font-mono text-white">
                      {fmt(t.target_price)}
                    </td>
                    <td className="py-2 px-3 text-right text-xs text-[#8b949e]">
                      {t.report_date || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
