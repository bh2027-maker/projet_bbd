import { useEffect, useState } from "react";
import { startDiscoveryAll, fetchDiscoveryStatus } from "../lib/api";
import { Button } from "./ui/button";
import { Radar, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

export default function DiscoverAllButton({ onRefresh }) {
  const [state, setState] = useState(null);

  useEffect(() => {
    let stop = false;
    const poll = async () => {
      try {
        const s = await fetchDiscoveryStatus();
        if (stop) return;
        setState(s);
        if (s.running) setTimeout(poll, 3000);
        else if (s.finished_at) onRefresh && onRefresh();
      } catch {}
    };
    poll();
    return () => { stop = true; };
  }, [onRefresh]);

  const start = async () => {
    try {
      const res = await startDiscoveryAll();
      if (res.status === "already_running") {
        toast.info("Détection déjà en cours");
      } else {
        toast.success("Détection lancée en arrière-plan");
      }
      // start polling
      const s = await fetchDiscoveryStatus();
      setState(s);
      const poll = async () => {
        const s2 = await fetchDiscoveryStatus();
        setState(s2);
        if (s2.running) setTimeout(poll, 3000);
        else if (s2.finished_at) {
          toast.success(`Détection terminée : ${s2.done}/${s2.total} communes traitées`);
          onRefresh && onRefresh();
        }
      };
      setTimeout(poll, 2500);
    } catch (e) {
      toast.error("Erreur : " + (e.response?.data?.detail || e.message));
    }
  };

  if (!state) return null;

  const running = state.running;
  const done = state.done;
  const total = state.total;
  const progress = total > 0 ? (done / total) * 100 : 0;

  if (!running && total === 0) {
    // Nothing to do → button not shown
    return (
      <Button
        onClick={start}
        data-testid="discover-all-btn"
        size="sm"
        className="bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25"
      >
        <Radar className="w-3.5 h-3.5 mr-2" strokeWidth={1.5} />
        Lancer la détection sur toutes les communes
      </Button>
    );
  }

  if (running) {
    return (
      <div className="bbd-card px-4 py-3 flex items-center gap-3" data-testid="discover-all-progress">
        <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" strokeWidth={1.5} />
        <div className="flex-1">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-300">
              Détection en cours : <span className="text-emerald-400">{state.current || "…"}</span>
            </span>
            <span className="text-slate-500 font-mono-data">{done}/{total}</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-sm overflow-hidden">
            <div className="h-full bg-emerald-400 transition-all duration-500"
                 style={{ width: `${progress}%` }} />
          </div>
        </div>
      </div>
    );
  }

  // Finished
  return (
    <div className="bbd-card px-4 py-3 flex items-center gap-3" data-testid="discover-all-done">
      <CheckCircle2 className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
      <div className="text-xs text-slate-300">
        Détection terminée : <span className="text-emerald-400 font-mono-data">{done}/{total}</span> communes traitées.{" "}
        <button onClick={start} className="text-slate-400 underline hover:text-emerald-400 ml-1"
                data-testid="discover-all-relaunch">
          Relancer
        </button>
      </div>
    </div>
  );
}
