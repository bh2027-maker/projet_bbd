import { useEffect, useState } from "react";
import { startEnrichment, fetchEnrichmentStatus } from "../lib/api";
import { Button } from "./ui/button";
import { CheckCircle2, Loader2, Sparkle } from "lucide-react";
import { toast } from "sonner";

export default function EnrichButton({ onRefresh }) {
  const [state, setState] = useState(null);

  useEffect(() => {
    let stop = false;
    (async () => {
      const s = await fetchEnrichmentStatus();
      if (!stop) setState(s);
      if (s.running) startPoll();
    })();
    return () => { stop = true; };
    // eslint-disable-next-line
  }, []);

  const startPoll = () => {
    const tick = async () => {
      const s = await fetchEnrichmentStatus();
      setState(s);
      if (s.running) setTimeout(tick, 3000);
      else if (s.finished_at) onRefresh && onRefresh();
    };
    setTimeout(tick, 2500);
  };

  const start = async () => {
    try {
      const res = await startEnrichment();
      if (res.status === "already_running") {
        toast.info("Enrichissement déjà en cours");
      } else {
        toast.success("Enrichissement BD TOPO IGN lancé");
      }
      const s = await fetchEnrichmentStatus();
      setState(s);
      startPoll();
    } catch (e) {
      toast.error("Erreur : " + (e.response?.data?.detail || e.message));
    }
  };

  if (!state) return null;

  const running = state.running;
  const done = state.done;
  const total = state.total;
  const progress = total > 0 ? (done / total) * 100 : 0;

  if (running) {
    return (
      <div className="bbd-card px-4 py-3 flex items-center gap-3" data-testid="enrich-progress">
        <Loader2 className="w-4 h-4 text-blue-400 animate-spin" strokeWidth={1.5} />
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-300">
              Enrichissement IGN : <span className="text-blue-400">{state.current || "…"}</span>
            </span>
            <span className="text-slate-500 font-mono-data">{done}/{total}</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-sm overflow-hidden">
            <div className="h-full bg-blue-400 transition-all duration-500"
                 style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>
    );
  }

  if (state.finished_at) {
    const results = state.results || [];
    const withDate = results.reduce((s, r) => s + (r.enriched_with_date || 0), 0);
    return (
      <div className="bbd-card px-4 py-3 flex items-center gap-3" data-testid="enrich-done">
        <CheckCircle2 className="w-4 h-4 text-blue-400" strokeWidth={1.5} />
        <div className="text-xs text-slate-300 flex-1">
          Enrichissement BD TOPO IGN terminé : <span className="text-blue-400 font-mono-data">
            {done} communes</span> ·{" "}
          <span className="text-blue-400 font-mono-data">{withDate}</span> vraies dates de construction récupérées.{" "}
          <button onClick={start} className="text-slate-400 underline hover:text-blue-400 ml-1"
                  data-testid="enrich-relaunch">Relancer</button>
        </div>
      </div>
    );
  }

  return (
    <Button
      onClick={start}
      data-testid="enrich-btn"
      size="sm"
      className="bg-blue-500/15 border border-blue-500/40 text-blue-300 hover:bg-blue-500/25"
    >
      <Sparkle className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} />
      Enrichir avec BD TOPO IGN (dates réelles)
    </Button>
  );
}
