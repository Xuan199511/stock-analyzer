import { Card, fmt, Badge } from "./shared";

export default function CompetitorsCard({ competitors, ownPeerPE }) {
  if (!competitors || competitors.length === 0) {
    return (
      <Card title="五、競爭對手比較" icon="🥊">
        <p className="text-sm text-[#6e7681] text-center py-6">查無同業對照資料</p>
      </Card>
    );
  }

  const cols = [
    { key: "name",         label: "名稱",     fmt: v => v || "—" },
    { key: "market_cap",   label: "市值",     fmt: v => fmt(v, { bn: true }) },
    { key: "revenue",      label: "營收",     fmt: v => fmt(v, { bn: true }) },
    { key: "gross_margin", label: "毛利率",   fmt: v => fmt(v, { pct: true }) },
    { key: "eps",          label: "EPS",      fmt: v => fmt(v) },
    { key: "pe_ratio",     label: "P/E",      fmt: v => fmt(v) },
  ];

  return (
    <Card
      title="五、競爭對手比較"
      icon="🥊"
      right={
        ownPeerPE?.avg
          ? <Badge tone="info">同業 P/E 均值 {ownPeerPE.avg}</Badge>
          : null
      }
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[#8b949e] text-xs uppercase tracking-wider border-b border-[#30363d]">
              <th className="text-left py-2 pr-3">代號</th>
              {cols.map(c => (
                <th key={c.key} className="text-right py-2 px-3">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {competitors.map((c, i) => (
              <tr key={c.symbol || i} className="border-b border-[#21262d] last:border-0">
                <td className="py-2 pr-3 font-mono text-[#58a6ff]">{c.symbol}</td>
                {cols.map(col => (
                  <td key={col.key} className="py-2 px-3 text-right font-mono text-white">
                    {col.fmt(c[col.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
