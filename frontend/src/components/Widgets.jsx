import { scoreColor } from "../lib/api";

export function ScoreBadge({ score, size = "md" }) {
  const cls = scoreColor(score);
  const s = size === "lg" ? "text-2xl px-4 py-2" : "";
  return (
    <span className={`score-pill ${cls} ${s}`} data-testid={`score-badge-${score}`}>
      {Number(score).toFixed(1)}
    </span>
  );
}

export function KpiCard({ label, value, hint, testid }) {
  return (
    <div className="bbd-card p-5" data-testid={testid}>
      <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 font-medium">
        {label}
      </div>
      <div className="font-mono-data text-3xl font-semibold text-slate-100 mt-2 tracking-tight">
        {value}
      </div>
      {hint && <div className="text-xs text-slate-500 mt-2">{hint}</div>}
    </div>
  );
}
