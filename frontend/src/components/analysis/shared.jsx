/** Shared UI primitives for the deep-analysis cards. */

export function fmt(value, { pct = false, bn = false, dp = 2, prefix = "", suffix = "" } = {}) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const n = Number(value);
  if (pct) return `${prefix}${(n * 100).toFixed(dp)}%${suffix}`;
  if (bn) {
    if (Math.abs(n) >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)} T${suffix}`;
    if (Math.abs(n) >= 1e9)  return `${prefix}${(n / 1e9).toFixed(2)} B${suffix}`;
    if (Math.abs(n) >= 1e6)  return `${prefix}${(n / 1e6).toFixed(2)} M${suffix}`;
  }
  return `${prefix}${n.toFixed(dp)}${suffix}`;
}

export function Card({ title, icon, right = null, children, className = "" }) {
  return (
    <section className={`bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden ${className}`}>
      <header className="px-5 py-3 border-b border-[#30363d] flex items-center gap-2">
        {icon && <span className="text-base">{icon}</span>}
        <h2 className="font-semibold text-white text-sm">{title}</h2>
        {right && <div className="ml-auto">{right}</div>}
      </header>
      <div className="p-5">{children}</div>
    </section>
  );
}

export function MetricCard({ label, value, sub = null, accent = false }) {
  const empty = value === null || value === undefined || value === "—";
  return (
    <div className="bg-[#21262d] rounded-xl p-4 flex flex-col gap-1 min-w-0">
      <span className="text-xs text-[#8b949e] truncate">{label}</span>
      <span className={`text-xl font-mono font-bold truncate ${accent ? "text-[#58a6ff]" : empty ? "text-[#484f58]" : "text-white"}`}>
        {empty ? "—" : value}
      </span>
      {sub && <span className="text-xs text-[#8b949e] truncate">{sub}</span>}
    </div>
  );
}

export function Row({ label, value }) {
  if (value === null || value === undefined || value === "—") return null;
  return (
    <div className="flex justify-between items-center py-2 border-b border-[#21262d] last:border-0">
      <span className="text-sm text-[#8b949e]">{label}</span>
      <span className="text-sm font-mono text-white">{value}</span>
    </div>
  );
}

export function Badge({ children, tone = "neutral" }) {
  const color = {
    positive: "bg-[#26a69a22] text-[#26a69a]",
    negative: "bg-[#ef535022] text-[#ef5350]",
    neutral:  "bg-[#30363d] text-[#8b949e]",
    info:     "bg-[#1f6feb22] text-[#58a6ff]",
    warn:     "bg-[#f0b42922] text-[#f0b429]",
  }[tone] || "bg-[#30363d] text-[#8b949e]";
  return <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full ${color}`}>{children}</span>;
}

export function Placeholder({ title }) {
  return (
    <div className="bg-[#21262d] rounded-xl px-4 py-6 text-center text-[#6e7681] text-sm">
      {title}（資料待後續階段補齊）
    </div>
  );
}

/** Staggered fade-in wrapper — pass `index` to offset the delay. */
export function FadeIn({ children, index = 0, className = "" }) {
  const delay = `${Math.min(index * 60, 600)}ms`;
  return (
    <div className={`fade-in ${className}`} style={{ animationDelay: delay }}>
      {children}
    </div>
  );
}

/** Shimmering grey block.  Width/height via Tailwind or style. */
export function Skeleton({ className = "", style }) {
  return <div className={`skeleton ${className}`} style={style} />;
}

/** Card-shaped skeleton used for deep-analysis loading state. */
export function SkeletonCard({ title, icon, rows = 3 }) {
  return (
    <section className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
      <header className="px-5 py-3 border-b border-[#30363d] flex items-center gap-2">
        {icon && <span className="text-base opacity-40">{icon}</span>}
        <h2 className="font-semibold text-[#8b949e] text-sm">{title}</h2>
        <Skeleton className="ml-auto h-4 w-16" />
      </header>
      <div className="p-5 flex flex-col gap-3">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-4" style={{ width: `${100 - i * 12}%` }} />
        ))}
      </div>
    </section>
  );
}
