/**
 * ScanPanel — 訊號掃描 & LINE 通知面板
 *
 * 功能：
 *   - 掃描台股 / 美股 / 全部 watchlist 的即時訊號
 *   - 結果以表格呈現，含訊號強度、策略標籤、漲跌幅
 *   - 一鍵發送 LINE Notify 通知
 */
import { useState } from "react";
import axios from "axios";

// ── Signal config ─────────────────────────────────────────────────────────────

const SIG = {
  BUY:  { label: "買入", color: "#26a69a", bg: "bg-[#26a69a22]", text: "text-[#26a69a]", border: "border-[#26a69a44]" },
  SELL: { label: "賣出", color: "#ef5350", bg: "bg-[#ef535022]", text: "text-[#ef5350]", border: "border-[#ef535044]" },
  NONE: { label: "觀望", color: "#8b949e", bg: "bg-[#30363d]",   text: "text-[#8b949e]", border: "border-[#30363d]" },
};

const STRENGTH = {
  strong:   { label: "強烈", dot: "bg-[#26a69a]" },
  moderate: { label: "中等", dot: "bg-[#f0b429]" },
  weak:     { label: "弱",   dot: "bg-[#8b949e]" },
  "":       { label: "",     dot: "" },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function ChangeCell({ v }) {
  const up  = v > 0;
  const cls = up ? "text-[#26a69a]" : v < 0 ? "text-[#ef5350]" : "text-[#8b949e]";
  return (
    <span className={`font-mono text-sm ${cls}`}>
      {up ? "+" : ""}{v.toFixed(2)}%
    </span>
  );
}

function SignalBadge({ signal }) {
  const s = SIG[signal] || SIG.NONE;
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${s.bg} ${s.text} ${s.border}`}>
      {s.label}
    </span>
  );
}

function StrengthDot({ strength }) {
  const s = STRENGTH[strength] || STRENGTH[""];
  if (!s.label) return null;
  return (
    <span className="flex items-center gap-1.5 text-xs text-[#8b949e]">
      <span className={`inline-block w-2 h-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function StrategyTags({ strategies }) {
  if (!strategies || strategies.length === 0) return <span className="text-[#484f58] text-xs">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {strategies.map((s) => (
        <span key={s} className="text-xs px-1.5 py-0.5 rounded bg-[#30363d] text-[#8b949e]">{s}</span>
      ))}
    </div>
  );
}

// ── Market filter button ──────────────────────────────────────────────────────

function MarketBtn({ value, current, onClick, children }) {
  const active = value === current;
  return (
    <button
      type="button"
      onClick={() => onClick(value)}
      className={`px-4 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-[#1f6feb] text-white"
          : "bg-[#21262d] text-[#8b949e] hover:text-white"
      }`}
    >
      {children}
    </button>
  );
}

// ── Result table ──────────────────────────────────────────────────────────────

function ResultTable({ rows }) {
  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-[#8b949e]">
        <span className="text-3xl mb-3">🔍</span>
        <p className="text-sm">本次掃描無明顯訊號</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-[#30363d]">
            {["股票", "市場", "現價", "漲跌", "訊號", "強度", "策略"].map((h) => (
              <th key={h} className="pb-3 pr-5 text-xs text-[#8b949e] font-medium whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.market}-${r.symbol}`}
                className="border-b border-[#21262d] last:border-0 hover:bg-[#21262d44] transition-colors">
              <td className="py-3 pr-5">
                <div className="font-semibold text-sm text-white">{r.name}</div>
                <div className="text-xs text-[#8b949e] font-mono">{r.symbol}</div>
              </td>
              <td className="py-3 pr-5">
                <span className="text-xs px-2 py-0.5 rounded bg-[#21262d] text-[#8b949e] uppercase">
                  {r.market}
                </span>
              </td>
              <td className="py-3 pr-5 font-mono text-sm text-white whitespace-nowrap">
                {r.price.toLocaleString()}
              </td>
              <td className="py-3 pr-5">
                <ChangeCell v={r.change_pct} />
              </td>
              <td className="py-3 pr-5">
                <SignalBadge signal={r.signal} />
              </td>
              <td className="py-3 pr-5">
                <StrengthDot strength={r.strength} />
              </td>
              <td className="py-3">
                <StrategyTags strategies={r.strategies} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Summary counts ────────────────────────────────────────────────────────────

function ScanSummary({ rows }) {
  const buy  = rows.filter((r) => r.signal === "BUY").length;
  const sell = rows.filter((r) => r.signal === "SELL").length;
  const none = rows.filter((r) => r.signal === "NONE").length;

  return (
    <div className="flex gap-3 flex-wrap">
      {[
        { label: "買入", count: buy,  cls: "text-[#26a69a]" },
        { label: "賣出", count: sell, cls: "text-[#ef5350]" },
        { label: "觀望", count: none, cls: "text-[#8b949e]" },
      ].map(({ label, count, cls }) => (
        <div key={label} className="flex items-center gap-1.5 text-sm">
          <span className={`font-bold font-mono text-base ${cls}`}>{count}</span>
          <span className="text-[#8b949e]">{label}</span>
        </div>
      ))}
    </div>
  );
}

// ── Main Export ───────────────────────────────────────────────────────────────

export default function ScanPanel() {
  const [market,      setMarket]      = useState("ALL");
  const [rows,        setRows]        = useState([]);
  const [scanned,     setScanned]     = useState(false);
  const [scanLoading, setScanLoading] = useState(false);
  const [lineLoading, setLineLoading] = useState(false);
  const [scanError,   setScanError]   = useState(null);
  const [lineStatus,  setLineStatus]  = useState(null);   // null | "sent" | "error"
  const [lineMsg,     setLineMsg]     = useState("");

  const handleScan = async () => {
    setScanLoading(true);
    setScanError(null);
    setLineStatus(null);
    setRows([]);

    try {
      const res = await axios.get("/api/scan", { params: { market } });
      setRows(res.data);
      setScanned(true);
    } catch (err) {
      setScanError(err.response?.data?.detail || err.message);
    } finally {
      setScanLoading(false);
    }
  };

  const handleLineNotify = async () => {
    setLineLoading(true);
    setLineStatus(null);
    setLineMsg("");

    try {
      await axios.post("/api/notify/line", {});
      setLineStatus("sent");
      setLineMsg("LINE 通知已發送！");
    } catch (err) {
      setLineStatus("error");
      setLineMsg(err.response?.data?.detail || err.message);
    } finally {
      setLineLoading(false);
    }
  };

  const activeSignals = rows.filter((r) => r.signal !== "NONE");

  return (
    <div className="space-y-6">
      {/* ── Control bar ─────────────────────────────────────────────────────── */}
      <div className="bg-[#161b22] border border-[#30363d] rounded-xl p-5">
        <div className="flex flex-wrap items-center gap-4">
          {/* Market filter */}
          <div className="flex rounded-lg overflow-hidden border border-[#30363d]">
            <MarketBtn value="ALL" current={market} onClick={setMarket}>全部</MarketBtn>
            <MarketBtn value="TW"  current={market} onClick={setMarket}>🇹🇼 台股</MarketBtn>
            <MarketBtn value="US"  current={market} onClick={setMarket}>🇺🇸 美股</MarketBtn>
          </div>

          {/* Scan button */}
          <button
            type="button"
            onClick={handleScan}
            disabled={scanLoading}
            className="px-5 py-2 bg-[#238636] hover:bg-[#2ea043] disabled:opacity-50
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            {scanLoading ? "掃描中..." : "🔍 開始掃描"}
          </button>

          {/* LINE Notify button — always visible, runs its own scan */}
          <button
            type="button"
            onClick={handleLineNotify}
            disabled={lineLoading}
            className="px-5 py-2 bg-[#00b300] hover:bg-[#00cc00] disabled:opacity-50
                       text-white text-sm font-medium rounded-lg transition-colors"
          >
            {lineLoading ? "發送中..." : "📱 發送 LINE 通知"}
          </button>

          {/* Scan summary (after scanning) */}
          {scanned && !scanLoading && <ScanSummary rows={rows} />}
        </div>

        {/* LINE status */}
        {lineStatus && (
          <div className={`mt-3 text-sm px-3 py-2 rounded-lg ${
            lineStatus === "sent"
              ? "bg-[#26a69a22] text-[#26a69a]"
              : "bg-[#3d1f1f] text-[#f85149]"
          }`}>
            {lineStatus === "sent" ? "✅" : "⚠"} {lineMsg}
          </div>
        )}
      </div>

      {/* ── Error ──────────────────────────────────────────────────────────── */}
      {scanError && (
        <div className="bg-[#3d1f1f] border border-[#f85149] rounded-lg p-4 text-[#f85149] text-sm">
          ⚠ {scanError}
        </div>
      )}

      {/* ── Loading ─────────────────────────────────────────────────────────── */}
      {scanLoading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="spinner" />
          <p className="text-[#8b949e] text-sm">正在掃描 {market === "ALL" ? "台股 + 美股" : market} 訊號...</p>
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────────────────── */}
      {!scanLoading && scanned && (
        <div className="bg-[#161b22] border border-[#30363d] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[#30363d] flex items-center gap-2 flex-wrap">
            <span className="text-base">📡</span>
            <h2 className="font-semibold text-white">掃描結果</h2>
            <span className="text-xs text-[#484f58]">
              共 {rows.length} 支 · {activeSignals.length} 支有訊號
            </span>
          </div>
          <div className="p-5">
            <ResultTable rows={rows} />
          </div>
        </div>
      )}

      {/* ── Empty / initial state ────────────────────────────────────────────── */}
      {!scanLoading && !scanned && !scanError && (
        <div className="flex flex-col items-center justify-center py-24 text-[#8b949e]">
          <span className="text-5xl mb-4">📡</span>
          <p className="text-lg">點擊「開始掃描」偵測今日訊號</p>
          <p className="text-sm mt-2">
            台股：2330 / 2317 / 2454 / 2308 / 2382 / 6505
          </p>
          <p className="text-sm mt-1">
            美股：AAPL / NVDA / TSLA / MSFT / META / GOOGL
          </p>
          <p className="text-xs mt-4 text-[#484f58]">
            排程：台股 22:30 · 美股 15:00（台灣時間）自動掃描並發送 LINE 通知
          </p>
        </div>
      )}
    </div>
  );
}
