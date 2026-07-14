import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPipeline, statusColor, generateTourPdf, api } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge } from "../components/Widgets";
import { Layers, Flame, ArrowLeft, ExternalLink, FileDown, Loader2, Filter, FileSpreadsheet } from "lucide-react";
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
  // Filters
  const [filterStatuses, setFilterStatuses] = useState(new Set());
  const [filterCommunes, setFilterCommunes] = useState(new Set());
  const [filterScoreMin, setFilterScoreMin] = useState(0);
  const [filterSurfaceMin, setFilterSurfaceMin] = useState(0);
  const [showFilters, setShowFilters] = useState(false);
  const [maxPerDay, setMaxPerDay] = useState(8);
  const [maxKmPerDay, setMaxKmPerDay] = useState(40);

  useEffect(() => {
    (async () => setData(await fetchPipeline()))();
  }, []);

  const rawList = topMode ? topHouses : (data?.hot_prospects || []);
  const activeList = useMemo(() => {
    return rawList.filter((h) => {
      if (filterStatuses.size > 0 && !filterStatuses.has(h.status)) return false;
      if (filterCommunes.size > 0 && !filterCommunes.has(h.commune_nom)) return false;
      if (h.score < filterScoreMin) return false;
      if (h.surface_habitable_estimee_m2 < filterSurfaceMin) return false;
      return true;
    });
  }, [rawList, filterStatuses, filterCommunes, filterScoreMin, filterSurfaceMin]);

  const availableCommunes = useMemo(
    () => [...new Set(rawList.map((h) => h.commune_nom))].sort(),
    [rawList]
  );

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleStatus = (s) => {
    setFilterStatuses((prev) => {
      const n = new Set(prev);
      n.has(s) ? n.delete(s) : n.add(s);
      return n;
    });
  };
  const toggleCommune = (c) => {
    setFilterCommunes((prev) => {
      const n = new Set(prev);
      n.has(c) ? n.delete(c) : n.add(c);
      return n;
    });
  };
  const resetFilters = () => {
    setFilterStatuses(new Set());
    setFilterCommunes(new Set());
    setFilterScoreMin(0);
    setFilterSurfaceMin(0);
  };

  const exportCsv = () => {
    if (activeList.length === 0) {
      toast.error("Rien à exporter");
      return;
    }
    const cols = [
      "id","commune","code_insee","score","statut","type","surface_hab_m2","surface_sol_m2",
      "anciennete","proba_chauffage_fossile_pct","contact_nom","contact_tel","contact_email",
      "lat","lon","gmaps","notes"
    ];
    const rows = activeList.map((h) => ({
      id: h.id,
      commune: h.commune_nom,
      code_insee: h.code_insee,
      score: h.score,
      statut: (data?.labels?.[h.status]) || h.status,
      type: h.type_label,
      surface_hab_m2: h.surface_habitable_estimee_m2,
      surface_sol_m2: h.surface_sol_m2,
      anciennete: h.age_label,
      proba_chauffage_fossile_pct: h.proba_chauffage_fossile_pct,
      contact_nom: h.contact_nom || "",
      contact_tel: h.contact_tel || "",
      contact_email: h.contact_email || "",
      lat: h.lat,
      lon: h.lon,
      gmaps: `https://www.google.com/maps/search/?api=1&query=${h.lat},${h.lon}`,
      notes: (h.notes || "").replace(/"/g, '""'),
    }));
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [
      cols.join(";"),
      ...rows.map((r) => cols.map((c) => esc(r[c])).join(";")),
    ].join("\n");
    // BOM for Excel FR
    const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prospects-BBD-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast.success(`${activeList.length} prospects exportés en CSV`);
  };

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
      const blob = await generateTourPdf(Array.from(selected), {
        maxPerDay, maxKmPerDay,
        label: `Tournée ${new Date().toLocaleDateString("fr-FR")}`,
      });
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
              <div className="hidden md:flex items-center gap-2 text-xs text-slate-400 border border-slate-800 rounded-sm px-2 py-1 h-8">
                <span className="text-slate-500">Max/jour</span>
                <input type="number" min="1" max="30"
                  value={maxPerDay}
                  onChange={(e) => setMaxPerDay(Math.max(1, Number(e.target.value)))}
                  data-testid="tour-max-per-day"
                  className="bg-transparent w-10 text-slate-100 text-center outline-none" />
                <span className="text-slate-700">|</span>
                <span className="text-slate-500">Km/jour</span>
                <input type="number" min="5" max="200"
                  value={maxKmPerDay}
                  onChange={(e) => setMaxKmPerDay(Math.max(5, Number(e.target.value)))}
                  data-testid="tour-max-km"
                  className="bg-transparent w-12 text-slate-100 text-center outline-none" />
              </div>
              <Button size="sm"
                onClick={exportCsv}
                data-testid="pipeline-csv-btn"
                className="bg-slate-700/40 border border-slate-600 text-slate-200 hover:bg-slate-700">
                <FileSpreadsheet className="w-3.5 h-3.5 mr-2" /> CSV ({activeList.length})
              </Button>
              <Button size="sm" variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                data-testid="pipeline-toggle-filters"
                className="border-slate-700 text-slate-300 hover:bg-slate-800">
                <Filter className="w-3.5 h-3.5 mr-2" /> Filtres
                {(filterStatuses.size + filterCommunes.size + (filterScoreMin>0?1:0) + (filterSurfaceMin>0?1:0)) > 0 && (
                  <span className="ml-1.5 text-[10px] px-1.5 rounded-sm bg-emerald-500/20 text-emerald-300">
                    {filterStatuses.size + filterCommunes.size + (filterScoreMin>0?1:0) + (filterSurfaceMin>0?1:0)}
                  </span>
                )}
              </Button>
            </div>
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-slate-800 space-y-4" data-testid="pipeline-filters">
              <div>
                <div className="text-[10.5px] uppercase tracking-wider text-slate-500 mb-2">Statut</div>
                <div className="flex flex-wrap gap-1.5">
                  {ORDER.map((s) => {
                    const on = filterStatuses.has(s);
                    return (
                      <button key={s} onClick={() => toggleStatus(s)}
                        data-testid={`filter-status-${s}`}
                        className={`text-[10.5px] px-2 py-1 rounded-sm border font-mono-data uppercase tracking-wider transition-colors ${
                          on ? statusColor(s) : "border-slate-800 text-slate-500 hover:border-slate-600"
                        }`}>
                        {data.labels[s]}
                      </button>
                    );
                  })}
                </div>
              </div>
              {availableCommunes.length > 0 && (
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500 mb-2">
                    Commune ({availableCommunes.length})
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {availableCommunes.map((c) => {
                      const on = filterCommunes.has(c);
                      return (
                        <button key={c} onClick={() => toggleCommune(c)}
                          data-testid={`filter-commune-${c}`}
                          className={`text-[10.5px] px-2 py-1 rounded-sm border transition-colors ${
                            on
                              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                              : "border-slate-800 text-slate-400 hover:border-slate-600"
                          }`}>
                          {c}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500 mb-2">
                    Score min : <span className="text-slate-200 font-mono-data ml-1">{filterScoreMin}</span>
                  </div>
                  <input type="range" min="0" max="100" step="5"
                    value={filterScoreMin}
                    onChange={(e) => setFilterScoreMin(Number(e.target.value))}
                    data-testid="filter-score-min"
                    className="accent-emerald-500 w-full" />
                </div>
                <div>
                  <div className="text-[10.5px] uppercase tracking-wider text-slate-500 mb-2">
                    Surface hab. min : <span className="text-slate-200 font-mono-data ml-1">{filterSurfaceMin} m²</span>
                  </div>
                  <input type="range" min="0" max="300" step="10"
                    value={filterSurfaceMin}
                    onChange={(e) => setFilterSurfaceMin(Number(e.target.value))}
                    data-testid="filter-surface-min"
                    className="accent-emerald-500 w-full" />
                </div>
              </div>
              <button onClick={resetFilters}
                data-testid="filter-reset"
                className="text-xs text-slate-400 hover:text-emerald-400 underline">
                Réinitialiser tous les filtres
              </button>
            </div>
          )}
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
