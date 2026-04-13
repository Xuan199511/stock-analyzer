/**
 * SentimentPanel — 話題性 / 市場情緒面板
 *
 * Props:
 *   data: {
 *     symbol, market, source,
 *     overall: "positive" | "neutral" | "negative",
 *     score:   0-100,
 *     summary: string,
 *     news:    [{title, url, source, date, sentiment, reason}],
 *     trend:   [{date, score, count}],   // 近 7 天
 *   }
 */
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
dayjs.extend(relativeTime);

// ── Config maps ───────────────────────────────────────────────────────────────

const SENT = {
  positive: { label: "正面", color: "#26a69a", bg: "bg-[#26a69a22]", text: "text-[#26a69a]" },
  negative: { label: "負面", color: "#ef5350", bg: "bg-[#ef535022]", text: "text-[#ef5350]" },
  neutral:  { label: "中性", color: "#8b949e", bg: "bg-[#30363d]",   text: "text-[#8b949e]" },
};

const OVERALL = {
  positive: { label: "整體看漲", emoji: "🐂", color: "#26a69a" },
  negative: { label: "整體看跌", emoji: "🐻", color: "#ef5350" },
  neutral:  { label: "市場中性", emoji: "〜",  color: "#8b949e" },
};

const SOURCE_LABEL = { claude: "Claude AI", keyword: "關鍵字", none: "無資料" };

// ── Score Gauge (SVG half-circle) ─────────────────────────────────────────────
//
// Layout (viewBox 0 0 220 130):
//   center: (110, 90)   radius: 75
//   arc spans 180°: left (35,90) → top (110,15) → right (185,90)
//   sweep=0 (CCW in SVG) produces the upper half ✓

function ScoreGauge({ score, overall }) {
  const W = 220, H = 130;
  const cx = 110, cy = 90, R = 75;

  const pct  = Math.max(0, Math.min(99.9, score)) / 100;  // clamp away from exact 100 (degenerate)
  const col  = score >= 60 ? SENT.positive.color : score >= 40 ? "#f0b429" : SENT.negative.color;
  const over = OVERALL[overall] || OVERALL.neutral;

  // Math-style angle (0 = right, π = left); score→right means pct=1→angle=0
  const angle    = (1 - pct) * Math.PI;
  const scoreX   = cx + R * Math.cos(angle);
  const scoreY   = cy - R * Math.sin(angle);        // minus → SVG y-flip

  // Needle (shorter)
  const NR      = R - 18;
  const needleX  = cx + NR * Math.cos(angle);
  const needleY  = cy - NR * Math.sin(angle);

  // Arc paths: sweep-flag=0 (CCW in SVG) traces the upper half
  const bgArc   = `M ${cx - R} ${cy} A ${R} ${R} 0 0 0 ${cx + R} ${cy}`;
  const fillArc = pct > 0.005
    ? `M ${cx - R} ${cy} A ${R} ${R} 0 0 0 ${scoreX.toFixed(2)} ${scoreY.toFixed(2)}`
    : null;

  // Tick marks at 0 / 25 / 50 / 75 / 100
  const ticks = [0, 25, 50, 75, 100].map((v) => {
    const a  = (1 - v / 100) * Math.PI;
    const x1 = cx + (R + 4)  * Math.cos(a);
    const y1 = cy - (R + 4)  * Math.sin(a);
    const x2 = cx + (R + 11) * Math.cos(a);
    const y2 = cy - (R + 11) * Math.sin(a);
    return { x1, y1, x2, y2, v };
  });

  return (
    <div className="flex flex-col items-center gap-1">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[200px]" aria-label={`情緒分數 ${score}`}>
        {/* Background arc */}
        <path d={bgArc} fill="none" stroke="#21262d" strokeWidth="10" strokeLinecap="round" />

        {/* Filled arc */}
        {fillArc && (
          <path d={fillArc} fill="none" stroke={col} strokeWidth="10" strokeLinecap="round" />
        )}

        {/* Tick marks */}
        {ticks.map(({ x1, y1, x2, y2, v }) => (
          <line key={v} x1={x1.toFixed(1)} y1={y1.toFixed(1)}
                x2={x2.toFixed(1)} y2={y2.toFixed(1)}
                stroke="#484f58" strokeWidth="1.5" />
        ))}

        {/* Needle */}
        <line x1={cx} y1={cy}
              x2={needleX.toFixed(2)} y2={needleY.toFixed(2)}
              stroke="#e6edf3" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="4.5" fill="#e6edf3" />

        {/* Score number */}
        <text x={cx} y={cy + 28} textAnchor="middle"
              fontSize="26" fontWeight="bold" fill={col} fontFamily="monospace">
          {score}
        </text>

        {/* 0 / 100 labels */}
        <text x={cx - R - 2} y={cy + 16} textAnchor="middle" fontSize="9" fill="#484f58">0</text>
        <text x={cx + R + 2} y={cy + 16} textAnchor="middle" fontSize="9" fill="#484f58">100</text>
      </svg>

      {/* Overall label */}
      <div className="flex items-center gap-1.5 text-sm font-semibold" style={{ color: over.color }}>
        <span>{over.emoji}</span>
        <span>{over.label}</span>
      </div>
    </div>
  );
}

// ── 7-day Trend Chart (SVG polyline) ─────────────────────────────────────────

function TrendChart({ data }) {
  if (!data || data.length < 2) return null;

  const W = 300, H = 80;
  const PAD = { top: 8, right: 8, bottom: 22, left: 8 };
  const iW  = W - PAD.left - PAD.right;
  const iH  = H - PAD.top - PAD.bottom;

  const xFor = (i) => PAD.left + (i / (data.length - 1)) * iW;
  const yFor = (s) => PAD.top + iH * (1 - s / 100);

  const pts  = data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.score).toFixed(1)}`).join(" ");
  const area = [
    `${xFor(0).toFixed(1)},${(PAD.top + iH).toFixed(1)}`,
    ...data.map((d, i) => `${xFor(i).toFixed(1)},${yFor(d.score).toFixed(1)}`),
    `${xFor(data.length - 1).toFixed(1)},${(PAD.top + iH).toFixed(1)}`,
  ].join(" ");

  // Neutral baseline at score=50
  const baseY = yFor(50).toFixed(1);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" aria-label="7天情緒趨勢">
      <defs>
        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#58a6ff" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#58a6ff" stopOpacity="0"   />
        </linearGradient>
      </defs>

      {/* Neutral line */}
      <line x1={PAD.left} y1={baseY} x2={W - PAD.right} y2={baseY}
            stroke="#30363d" strokeWidth="1" strokeDasharray="3 3" />

      {/* Area */}
      <polygon points={area} fill="url(#trendGrad)" />

      {/* Line */}
      <polyline points={pts} fill="none" stroke="#58a6ff"
                strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />

      {/* Dots — colour by score */}
      {data.map((d, i) => {
        const col = d.score >= 60 ? "#26a69a" : d.score >= 40 ? "#f0b429" : "#ef5350";
        return (
          <circle key={i} cx={xFor(i)} cy={yFor(d.score)} r="3" fill={col} />
        );
      })}

      {/* Date labels — first, middle, last */}
      {[0, Math.floor((data.length - 1) / 2), data.length - 1].map((i) => (
        <text key={i} x={xFor(i)} y={H - 4} textAnchor="middle" fontSize="8.5" fill="#6e7681">
          {data[i]?.date?.slice(5)}
        </text>
      ))}
    </svg>
  );
}

// ── News Article Card ─────────────────────────────────────────────────────────

function ArticleCard({ article }) {
  const s = SENT[article.sentiment] || SENT.neutral;
  const ago = article.date ? dayjs(article.date).fromNow() : "";

  return (
    <div className="py-3 border-b border-[#21262d] last:border-0">
      <div className="flex items-start gap-2">
        {/* Sentiment badge */}
        <span className={`mt-0.5 shrink-0 text-xs font-medium px-2 py-0.5 rounded-md ${s.bg} ${s.text}`}>
          {s.label}
        </span>

        <div className="flex-1 min-w-0">
          {/* Title / link */}
          {article.url ? (
            <a href={article.url} target="_blank" rel="noopener noreferrer"
               className="text-sm text-[#e6edf3] hover:text-[#58a6ff] transition-colors line-clamp-2">
              {article.title}
            </a>
          ) : (
            <p className="text-sm text-[#e6edf3] line-clamp-2">{article.title}</p>
          )}

          {/* Meta row */}
          <div className="flex items-center flex-wrap gap-x-2 mt-1">
            {article.source && (
              <span className="text-xs text-[#8b949e]">{article.source}</span>
            )}
            {ago && (
              <span className="text-xs text-[#484f58]">· {ago}</span>
            )}
            {article.reason && (
              <span className="text-xs text-[#6e7681] italic truncate max-w-[200px]">
                — {article.reason}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export default function SentimentPanel({ data }) {
  const {
    symbol, market,
    overall = "neutral",
    score   = 50,
    summary = "",
    news    = [],
    trend   = [],
    source  = "none",
  } = data;

  const hasData  = news.length > 0;
  const srcLabel = SOURCE_LABEL[source] || source;

  return (
    <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2">
        <span className="text-base">💬</span>
        <h2 className="font-semibold text-white">話題性 / 市場情緒</h2>
        <span className="ml-auto flex items-center gap-2 text-xs text-[#8b949e]">
          <span className="uppercase">{symbol} · {market}</span>
          <span className="px-1.5 py-0.5 rounded bg-[#21262d] text-[#6e7681]">{srcLabel}</span>
        </span>
      </div>

      <div className="p-5 overflow-y-auto max-h-[680px]">
        {!hasData ? (
          /* ── Empty state ────────────────────────────────────────────────── */
          <div className="flex flex-col items-center justify-center py-16 text-[#8b949e]">
            <span className="text-4xl mb-3">📰</span>
            <p className="text-sm">目前無相關新聞資料</p>
            <p className="text-xs mt-1 text-[#484f58]">請確認 NEWS_API_KEY 已設定</p>
          </div>
        ) : (
          <>
            {/* ── Gauge + summary ─────────────────────────────────────────── */}
            <div className="mb-5">
              <ScoreGauge score={score} overall={overall} />
              {summary && (
                <p className="mt-3 text-sm text-[#8b949e] text-center leading-relaxed px-2">
                  {summary}
                </p>
              )}
            </div>

            {/* ── 7-day trend chart ────────────────────────────────────────── */}
            {trend.length >= 2 && (
              <div className="mb-5">
                <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
                  近 7 天情緒走勢
                </h3>
                <div className="bg-[#21262d] rounded-xl p-3">
                  <TrendChart data={trend} />
                </div>
              </div>
            )}

            {/* ── News list ────────────────────────────────────────────────── */}
            <div>
              <h3 className="text-xs font-semibold text-[#8b949e] uppercase tracking-wider mb-2">
                相關新聞（{news.length} 筆）
              </h3>
              <div className="bg-[#21262d] rounded-xl px-4">
                {news.map((a, i) => (
                  <ArticleCard key={i} article={a} />
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
