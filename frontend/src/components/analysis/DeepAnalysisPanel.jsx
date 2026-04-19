import CompanyCard from "./CompanyCard";
import FundamentalCard from "./FundamentalCard";
import TechnicalCard from "./TechnicalCard";
import SentimentCard from "./SentimentCard";
import CompetitorsCard from "./CompetitorsCard";
import SwotCard from "./SwotCard";
import MoatCard from "./MoatCard";
import InstitutionalCard from "./InstitutionalCard";
import ConclusionCard from "./ConclusionCard";
import { Badge, FadeIn, SkeletonCard } from "./shared";

function formatGenerated(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return ts;
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const SECTION_SKELETONS = [
  { title: "一、公司基本資料", icon: "🏢", rows: 4 },
  { title: "二、基本面分析",  icon: "📊", rows: 5 },
  { title: "三、技術面分析",  icon: "📈", rows: 5 },
  { title: "四、市場情緒分析", icon: "📰", rows: 4 },
  { title: "五、競爭對手比較", icon: "🥊", rows: 5 },
  { title: "六、SWOT",          icon: "⚖",  rows: 4 },
  { title: "七、獨佔性與護城河", icon: "🏰", rows: 5 },
  { title: "八、外資與法人目標價", icon: "🎯", rows: 4 },
  { title: "九、綜合結論與操作建議", icon: "🧭", rows: 6 },
];

export default function DeepAnalysisPanel({ report, loading, error, onRefresh }) {
  if (error) {
    return (
      <div className="bg-[#2d0808] border border-[#f85149] rounded-lg p-4 text-[#ff7b72] text-sm">
        深度分析載入失敗：{error}
      </div>
    );
  }

  if (loading && !report) {
    return (
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 text-xs text-[#8b949e]">
          <span className="spinner" style={{ width: 20, height: 20, borderWidth: 2 }} />
          <span>正在進行深度分析（9 大面向 + AI 綜合結論）...</span>
          <span className="text-[#6e7681]">首次分析約 10~20 秒</span>
        </div>
        {SECTION_SKELETONS.map((s, i) => (
          <FadeIn key={s.title} index={i}>
            <SkeletonCard {...s} />
          </FadeIn>
        ))}
      </div>
    );
  }

  if (!report) return null;

  const cards = [
    <CompanyCard      company={report.company} />,
    <FundamentalCard  fundamental={report.fundamental} />,
    <TechnicalCard    technical={report.technical} />,
    <SentimentCard    sentiment={report.sentiment} />,
    <CompetitorsCard  competitors={report.competitors} ownPeerPE={report.fundamental?.peer_pe_comparison} />,
    <SwotCard         swot={report.ai_conclusion?.swot} />,
    <MoatCard         moat={report.moat} />,
    <InstitutionalCard
      consensus={report.consensus_target}
      targets={report.institutional_targets}
      currentPrice={report.technical?.current_price}
    />,
    <ConclusionCard
      conclusion={report.ai_conclusion}
      currentPrice={report.technical?.current_price}
    />,
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-xs text-[#8b949e]">
        <span>🧠 深度分析</span>
        <span>·</span>
        <span>產生於 {formatGenerated(report.generated_at)}</span>
        {report.cached && <Badge tone="neutral">已快取</Badge>}
        {report.data_sources?.map(s => <Badge key={s} tone="info">{s}</Badge>)}
        <button
          onClick={onRefresh}
          disabled={loading}
          className="ml-auto text-xs px-3 py-1 rounded-md border border-[#30363d] hover:border-[#1f6feb] hover:text-white transition-colors disabled:opacity-50"
        >
          {loading ? "載入中..." : "🔄 強制刷新"}
        </button>
      </div>

      {report.errors?.length > 0 && (
        <div className="bg-[#2d2208] border border-[#f0b429] rounded-lg p-3 text-[#f0b429] text-xs">
          ⚠ 部分資料載入失敗：
          <ul className="mt-1 list-disc list-inside">
            {report.errors.map((e, i) => <li key={i}>{e.section}：{e.error}</li>)}
          </ul>
        </div>
      )}

      {cards.map((card, i) => (
        <FadeIn key={i} index={i}>{card}</FadeIn>
      ))}
    </div>
  );
}
