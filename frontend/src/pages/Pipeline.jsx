import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPipeline, statusColor, generateTourPdf, api } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge } from "../components/Widgets";
import { Layers, Flame, ArrowLeft, ExternalLink, FileDown, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Checkbox } from "../components/ui/checkbox";
import { toast } from "sonner";

const ORDER = ["a_analyser", "a_contacter", "interesse", "rdv", "transmis_gael", "vendu", "perdu"];

export default function Pipeline() {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [pdfLoading, setPdfLoading] = useState(false);
  const [topMode, setTopMode] = useState(false);
  const [topHouses, setTopHouses] = useState([]);

  useEffect(() => {
    (async () => setData(await fetchPipeline()))();
  }, []);

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const activeList = topMode ? topHouses : (data?.hot_prospects || []);

  const selectAllVisible = () => {
    setSelected(new Set(activeList.map((h) => h.id)));
  };
  const clearSelection = () => setSelected(new Set());

  const loadTopFromAllCommunes = async () => {
    // Aggregate top 20 across all communes: uses list of ALL houses via a helper
    try {
      const communes = await api.get("/communes");
      const all = [];
      for (const c of communes.data.items) {
        const { data: h } = await api.get(`/communes/${c.code_insee}/houses`, {
          params: { min_score: 65 },
        });
        all.push(...(h.items || []));
      }
      all.sort((a, b) => b.score - a.score);
      setTopHouses(all.slice(0, 20));
      setTopMode(true);
      toast.info(`${Math.min(20, all.length)} meilleurs prospects chargés`);
    } catch (e) {
      toast.error("Erreur : " + e.message);
    }
  };

  const generatePdf = async () => {
    if (selected.size === 0) {
      toast.error("Sélectionnez au moins une maison");
      return;
    }
    setPdfLoading(true);
    try {
      const blob = await generateTourPdf(Array.from(selected),
                                          `Tournée ${new Date().toLocaleDateString("fr-FR")}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `feuille-de-route-BBD-${new Date().toISOString().slice(0,10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Feuille de route téléchargée");
    } catch (e) {
      toast.error("Erreur PDF : " + (e.response?.data?.detail || e.message));
    } finally {
      setPdfLoading(false);
    }
  };

  if (!data) return <><Header /><div className="p-10 text-slate-500">Chargement…</div></>;

  const total = ORDER.reduce((s, k) => s + (data.counts[k] || 0), 0);

  return (
    <>
      <Header subtitle="Pipeline prospect" />
      <main className="max-w-[1500px] mx-auto px-6 py-8" data-testid="pipeline-main">
        <Link to="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-emerald-400 mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Retour au classement
        </Link>

        <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
              <h1 className="font-display text-3xl md:text-4xl font-semibold text-slate-100 tracking-tight">
                Pipeline commercial
              </h1>
            </div>
            <p className="text-slate-400 text-sm max-w-2xl">
              Vision consolidée des prospects par statut. Sélectionnez des maisons pour générer
              une feuille de route imprimable pour Gaël (itinéraire optimisé + fiches terrain).
            </p>
          </div>
        </div>

        {/* Kanban */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-8" data-testid="pipeline-kanban">
          {ORDER.map((s) => (
            <div key={s} className={`bbd-card p-4 border ${statusColor(s).split(" ").find(c=>c.startsWith("border")) || ""}`}
                 data-testid={`pipeline-col-${s}`}>
              <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-400">
                {data.labels[s]}
              </div>
              <div className="font-mono-data text-3xl font-semibold text-slate-100 mt-2">
                {data.counts[s] || 0}
              </div>
              <div className="text-[10px] text-slate-600 mt-1 font-mono-data">
                {total > 0 ? Math.round(((data.counts[s] || 0) * 100) / total) : 0}% du total
              </div>
            </div>
          ))}
        </div>

        {/* Selection toolbar */}
        <div className="bbd-card p-4 mb-4" data-testid="pipeline-toolbar">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-400" strokeWidth={1.5} />
              <span className="text-sm text-slate-200">
                {topMode
                  ? `Top ${activeList.length} prospects (tous statuts)`
                  : `${activeList.length} prospects actifs`}
              </span>
            </div>
            <div className="flex gap-2 md:ml-auto">
              {!topMode ? (
                <Button size="sm" variant="outline"
                  onClick={loadTopFromAllCommunes}
                  data-testid="pipeline-load-top"
                  className="border-slate-700 text-slate-300 hover:bg-slate-800">
                  Charger le top 20 (toutes communes)
                </Button>
              ) : (
                <Button size="sm" variant="outline"
                  onClick={() => { setTopMode(false); clearSelection(); }}
                  className="border-slate-700 text-slate-300 hover:bg-slate-800">
                  Retour aux prospects actifs
                </Button>
              )}
              <Button size="sm" variant="outline"
                onClick={selectAllVisible}
                data-testid="pipeline-select-all"
                className="border-slate-700 text-slate-300 hover:bg-slate-800">
                Tout sélectionner
              </Button>
              <Button size="sm" variant="outline"
                onClick={clearSelection}
                className="border-slate-700 text-slate-300 hover:bg-slate-800">
                Effacer
              </Button>
              <Button size="sm"
                onClick={generatePdf}
                disabled={pdfLoading || selected.size === 0}
                data-testid="pipeline-pdf-btn"
                className="bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/30">
                {pdfLoading
                  ? <><Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> PDF…</>
                  : <><FileDown className="w-3.5 h-3.5 mr-2" /> Feuille de route PDF ({selected.size})</>}
              </Button>
            </div>
          </div>
        </div>

        {activeList.length === 0 && (
          <div className="bbd-card p-8 text-center text-slate-500">
            {topMode
              ? "Aucun prospect ≥ 65."
              : "Aucun prospect actif. Passez des maisons en « À contacter » depuis les fiches communes, ou cliquez sur « Charger le top 20 » pour préparer une tournée sans qualifier au préalable."}
          </div>
        )}

        {activeList.length > 0 && (
          <div className="bbd-card overflow-hidden">
            <table className="w-full bbd-table" data-testid="pipeline-table">
              <thead>
                <tr>
                  <th className="w-10"></th>
                  <th>Commune</th>
                  <th>Type</th>
                  <th className="text-right">Surface hab.</th>
                  <th>Contact</th>
                  <th>Statut</th>
                  <th className="text-right">Score</th>
                  <th className="w-8"></th>
                </tr>
              </thead>
              <tbody>
                {activeList.map((h) => {
                  const isSel = selected.has(h.id);
                  return (
                    <tr key={h.id} data-testid={`pipeline-row-${h.id}`}
                        className={isSel ? "!bg-emerald-500/5" : ""}>
                      <td onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={isSel}
                          onCheckedChange={() => toggle(h.id)}
                          className="border-slate-600"
                          data-testid={`pipeline-check-${h.id}`}
                        />
                      </td>
                      <td>
                        <Link to={`/communes/${h.code_insee}`}
                              className="text-slate-100 hover:text-emerald-400">
                          {h.commune_nom}
                        </Link>
                      </td>
                      <td className="text-xs text-slate-400">{h.type_label}</td>
                      <td className="text-right font-mono-data text-slate-300">
                        {h.surface_habitable_estimee_m2} m²
                      </td>
                      <td className="text-xs">
                        {h.contact_nom ? (
                          <>
                            <div className="text-slate-100">{h.contact_nom}</div>
                            {h.contact_tel && <div className="text-slate-500 font-mono-data">{h.contact_tel}</div>}
                          </>
                        ) : <span className="text-slate-600">—</span>}
                      </td>
                      <td>
                        <span className={`text-[10.5px] px-2 py-0.5 rounded-sm border font-mono-data uppercase tracking-wider ${statusColor(h.status)}`}>
                          {data.labels[h.status]}
                        </span>
                      </td>
                      <td className="text-right"><ScoreBadge score={h.score} /></td>
                      <td>
                        <Link to={`/communes/${h.code_insee}`} className="text-slate-500 hover:text-emerald-400">
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
