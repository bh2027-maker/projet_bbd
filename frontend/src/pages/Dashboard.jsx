import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { fetchCommunes, fetchStats, scoreLabel } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge, KpiCard } from "../components/Widgets";
import CommuneMap from "../components/CommuneMap";
import { Search, TrendingUp, Home as HomeIcon, Target, Map as MapIcon } from "lucide-react";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

export default function Dashboard() {
  const nav = useNavigate();
  const [communes, setCommunes] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [minScore, setMinScore] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const [c, s] = await Promise.all([fetchCommunes(), fetchStats()]);
        setCommunes(c.items || []);
        setStats(s);
      } catch (e) {
        toast.error("Erreur chargement des données");
        console.error(e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered = useMemo(() => {
    return communes
      .filter((c) => c.score_bbd >= minScore)
      .filter(
        (c) =>
          !query ||
          c.nom.toLowerCase().includes(query.toLowerCase()) ||
          c.code_postal.startsWith(query) ||
          c.code_insee.startsWith(query),
      );
  }, [communes, query, minScore]);

  return (
    <>
      <Header />
      <main className="max-w-[1600px] mx-auto px-6 py-8" data-testid="dashboard-main">
        {/* Titre + intro */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <h1 className="font-display text-3xl md:text-4xl font-semibold text-slate-100 tracking-tight">
              Classement stratégique des communes
            </h1>
            <p className="text-slate-400 mt-2 max-w-2xl text-sm leading-relaxed">
              Le moteur BBD analyse le potentiel de prospection pompe à chaleur de chaque
              commune du Massif des Bauges de moins de 2 500 habitants. Score sur 100 basé
              sur l'ancienneté du parc, le revenu médian, le volume de maisons individuelles
              et la zone climatique H1.
            </p>
          </div>
          {stats && (
            <div className="text-right shrink-0">
              <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500">Top prioritaire</div>
              <div className="font-display text-xl text-emerald-400 mt-1">{stats.top_commune}</div>
            </div>
          )}
        </div>

        {/* KPI */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8" data-testid="kpi-grid">
            <KpiCard testid="kpi-communes" label="Communes analysées" value={stats.nb_communes}
              hint={`< 2 500 hab`} />
            <KpiCard testid="kpi-prioritaires" label="Score ≥ 70" value={stats.nb_score_sup_70}
              hint={`${stats.nb_score_sup_80} ≥ 80`} />
            <KpiCard testid="kpi-maisons" label="Maisons individuelles"
              value={stats.total_maisons_individuelles.toLocaleString("fr-FR")}
              hint="Estimation communale" />
            <KpiCard testid="kpi-maisons-detectees" label="Maisons détectées"
              value={(stats.total_maisons_detectees || 0).toLocaleString("fr-FR")}
              hint="OSM/cadastre (Module 2)" />
            <KpiCard testid="kpi-prospects-actifs" label="Prospects actifs"
              value={stats.total_prospects_actifs || 0}
              hint="Dans le pipeline" />
            <KpiCard testid="kpi-dossiers" label="Dossiers estimés"
              value={stats.total_dossiers_estimes.toLocaleString("fr-FR")}
              hint="BAR-TH-171 CEE" />
          </div>
        )}

        {/* Carte */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <MapIcon className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
            <h2 className="font-display text-lg text-slate-200">Vision géographique</h2>
            <span className="text-xs text-slate-500 ml-2">
              Cliquez sur un cercle pour ouvrir la fiche
            </span>
          </div>
          {!loading && communes.length > 0 && <CommuneMap communes={communes} />}
          {loading && <div className="bbd-card h-[480px] flex items-center justify-center text-slate-500">
            Chargement de la carte…</div>}
        </div>

        {/* Table + filtres */}
        <div className="flex flex-col md:flex-row md:items-center gap-3 mb-4">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
            <h2 className="font-display text-lg text-slate-200">Classement détaillé</h2>
          </div>
          <div className="md:ml-auto flex flex-col md:flex-row gap-2 md:items-center">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                data-testid="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Nom, CP, code INSEE…"
                className="pl-9 h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600 w-64"
              />
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="uppercase tracking-wider">Score min</span>
              <input
                data-testid="minscore-slider"
                type="range" min="0" max="100" step="5"
                value={minScore}
                onChange={(e) => setMinScore(Number(e.target.value))}
                className="accent-emerald-500 w-32"
              />
              <span className="font-mono-data text-slate-200 w-8 text-right">{minScore}</span>
            </div>
          </div>
        </div>

        <div className="bbd-card overflow-hidden" data-testid="communes-table-wrap">
          <table className="w-full bbd-table" data-testid="communes-table">
            <thead>
              <tr>
                <th className="w-12">#</th>
                <th>Commune</th>
                <th>Dép.</th>
                <th className="text-right">Hab.</th>
                <th className="text-right">Maisons ind.</th>
                <th className="text-right">% avant 2000</th>
                <th className="text-right">Rev. médian</th>
                <th className="text-right">Alt.</th>
                <th className="text-right">Dossiers est.</th>
                <th className="text-right">Priorité</th>
                <th className="text-right">Score</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.code_insee}
                    data-testid={`row-${c.code_insee}`}
                    onClick={() => nav(`/communes/${c.code_insee}`)}>
                  <td className="font-mono-data text-slate-500">{c.rank}</td>
                  <td>
                    <div className="text-slate-100 font-medium">{c.nom}</div>
                    <div className="text-xs text-slate-500">{c.code_postal} · {c.code_insee}</div>
                  </td>
                  <td className="font-mono-data text-slate-400">{c.departement}</td>
                  <td className="text-right font-mono-data text-slate-300">{c.population}</td>
                  <td className="text-right font-mono-data text-slate-300">
                    {c.nb_maisons_individuelles}
                    <span className="text-slate-600 text-xs"> ({c.part_maisons_pct}%)</span>
                  </td>
                  <td className="text-right font-mono-data text-slate-300">{c.part_logements_avant_2000_pct}%</td>
                  <td className="text-right font-mono-data text-slate-300">{c.revenu_median.toLocaleString("fr-FR")} €</td>
                  <td className="text-right font-mono-data text-slate-400">{c.altitude_m} m</td>
                  <td className="text-right font-mono-data text-emerald-400">{c.dossiers_bar_th_171_estimes}</td>
                  <td className="text-right text-xs text-slate-400">{scoreLabel(c.score_bbd)}</td>
                  <td className="text-right"><ScoreBadge score={c.score_bbd} /></td>
                </tr>
              ))}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={11} className="text-center py-8 text-slate-500">Aucune commune ne correspond</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <footer className="text-[11px] text-slate-600 mt-6 font-mono-data">
          BBD Prospect Intelligence · Sources INSEE 2020-2022, IGN · Zone climatique H1
        </footer>
      </main>
    </>
  );
}
