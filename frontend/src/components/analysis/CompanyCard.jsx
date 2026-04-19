import { Card, Row, Badge } from "./shared";

export default function CompanyCard({ company }) {
  if (!company) return null;
  const {
    symbol, name, market, industry, sub_industry,
    description, supply_chain_position, top_customers, business_segments = [],
  } = company;

  return (
    <Card
      title="一、公司基本資料"
      icon="🏢"
      right={<Badge tone="info">{symbol} · {market}</Badge>}
    >
      <div className="flex items-baseline gap-2 mb-3 flex-wrap">
        <h3 className="text-lg font-bold text-white">{name}</h3>
        {industry && industry !== "N/A" && <Badge tone="neutral">{industry}</Badge>}
        {sub_industry && sub_industry !== industry && <Badge tone="neutral">{sub_industry}</Badge>}
      </div>

      {description && (
        <p className="text-sm text-[#8b949e] leading-relaxed line-clamp-4 mb-4">{description}</p>
      )}

      <div className="bg-[#21262d] rounded-xl px-4">
        <Row label="產業"   value={industry || "—"} />
        <Row label="子產業" value={sub_industry || "—"} />
        <Row label="供應鏈位置" value={supply_chain_position && supply_chain_position !== "N/A" ? supply_chain_position : "—"} />
        {business_segments.length > 0 && (
          <Row
            label="營收結構"
            value={business_segments.map(s => `${s.name}${s.revenue_pct ? `(${s.revenue_pct}%)` : ""}`).join("｜")}
          />
        )}
        {top_customers && top_customers.length > 0 && (
          <Row label="主要客戶" value={top_customers.slice(0, 5).join("、")} />
        )}
      </div>
    </Card>
  );
}
