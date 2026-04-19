import { Card } from "./shared";

const QUADRANTS = [
  { key: "strengths",     label: "優勢 S", color: "#26a69a", bg: "#26a69a1a", border: "#26a69a66" },
  { key: "weaknesses",    label: "劣勢 W", color: "#ef5350", bg: "#ef53501a", border: "#ef535066" },
  { key: "opportunities", label: "機會 O", color: "#58a6ff", bg: "#58a6ff1a", border: "#58a6ff66" },
  { key: "threats",       label: "威脅 T", color: "#f0b429", bg: "#f0b4291a", border: "#f0b42966" },
];

export default function SwotCard({ swot }) {
  if (!swot) return null;
  const hasAny = Object.values(swot).some(v => Array.isArray(v) && v.length > 0);

  return (
    <Card title="六、競爭優勢與劣勢（SWOT）" icon="⚖">
      {!hasAny ? (
        <p className="text-sm text-[#6e7681] text-center py-6">
          暫無 SWOT 資料（需設定 ANTHROPIC_API_KEY）
        </p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {QUADRANTS.map(q => (
            <div
              key={q.key}
              className="rounded-xl p-3 border"
              style={{ background: q.bg, borderColor: q.border }}
            >
              <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: q.color }}>
                {q.label}
              </div>
              {(swot[q.key] || []).length === 0 ? (
                <p className="text-xs text-[#484f58]">—</p>
              ) : (
                <ul className="space-y-1 text-sm text-[#c9d1d9] list-disc list-inside">
                  {(swot[q.key] || []).map((item, i) => <li key={i}>{item}</li>)}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
