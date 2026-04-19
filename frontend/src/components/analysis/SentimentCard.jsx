import { Card, Badge, Row, fmt } from "./shared";

const TONE = {
  positive: { tone: "positive", label: "偏正面" },
  negative: { tone: "negative", label: "偏負面" },
  neutral:  { tone: "neutral",  label: "中性" },
};

function ToneBar({ score }) {
  const pct = ((score + 1) / 2) * 100;
  return (
    <div className="flex items-center gap-2 w-full max-w-[200px]">
      <span className="text-xs text-[#ef5350]">負</span>
      <div className="flex-1 h-2 bg-[#21262d] rounded overflow-hidden relative">
        <div className="absolute inset-y-0 left-1/2 w-px bg-[#484f58]" />
        <div
          className="h-full"
          style={{
            width: `${Math.abs(score) * 50}%`,
            marginLeft: score >= 0 ? "50%" : `${50 - Math.abs(score) * 50}%`,
            background: score >= 0 ? "#26a69a" : "#ef5350",
          }}
        />
      </div>
      <span className="text-xs text-[#26a69a]">正</span>
    </div>
  );
}

function PillList({ items, tone }) {
  if (!items || items.length === 0) return <span className="text-xs text-[#484f58]">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {items.map((t, i) => <Badge key={i} tone={tone}>{t}</Badge>)}
    </div>
  );
}

export default function SentimentCard({ sentiment }) {
  if (!sentiment) return null;
  const t = TONE[sentiment.media_tone] || TONE.neutral;
  const margin = sentiment.margin_trading_change || {};
  const hasNews = (sentiment.news_items || []).length > 0;
  const hasMargin = margin.margin_change !== null && margin.margin_change !== undefined;

  return (
    <Card
      title="四、市場情緒分析"
      icon="📰"
      right={<Badge tone={t.tone}>{t.label}</Badge>}
    >
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div>
          <div className="text-xs text-[#8b949e] mb-1">情緒指數</div>
          <ToneBar score={Number(sentiment.tone_score) || 0} />
        </div>
        {sentiment.social_heat !== null && sentiment.social_heat !== undefined && (
          <div>
            <div className="text-xs text-[#8b949e] mb-1">熱度</div>
            <span className="text-xl font-mono font-bold text-[#58a6ff]">{sentiment.social_heat}</span>
            <span className="text-xs text-[#8b949e]">/100</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
        <div>
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">題材熱點</div>
          <PillList items={sentiment.hot_topics} tone="info" />
        </div>
        <div>
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">催化事件</div>
          <PillList items={sentiment.key_catalysts} tone="positive" />
        </div>
        <div>
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">主要風險</div>
          <PillList items={sentiment.key_risks} tone="warn" />
        </div>
      </div>

      {hasMargin && (
        <div className="bg-[#21262d] rounded-xl px-4 mb-4">
          <div className="text-xs text-[#8b949e] py-2 border-b border-[#30363d]">
            近 {margin.period_days || 5} 日融資融券變化（張）
          </div>
          <Row label="融資餘額變化" value={fmt(margin.margin_change, { dp: 0 })} />
          <Row label="融券餘額變化" value={fmt(margin.short_change, { dp: 0 })} />
        </div>
      )}

      {hasNews ? (
        <div>
          <div className="text-xs text-[#8b949e] uppercase tracking-wider mb-2">近期新聞</div>
          <ul className="space-y-2">
            {sentiment.news_items.slice(0, 8).map((n, i) => {
              const senT = TONE[n.sentiment] || TONE.neutral;
              return (
                <li key={i} className="flex gap-2 items-start text-sm">
                  <Badge tone={senT.tone}>{senT.label}</Badge>
                  <a
                    href={n.url || "#"}
                    target="_blank" rel="noreferrer"
                    className="flex-1 text-[#c9d1d9] hover:text-[#58a6ff] line-clamp-2"
                  >
                    {n.title}
                  </a>
                  <span className="text-xs text-[#6e7681] whitespace-nowrap">{n.date}</span>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        <p className="text-xs text-[#6e7681] text-center py-3">
          無新聞資料（需設定 NEWS_API_KEY）
        </p>
      )}
    </Card>
  );
}
