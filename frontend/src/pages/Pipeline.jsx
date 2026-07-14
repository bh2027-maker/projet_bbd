import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPipeline, statusColor } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge } from "../components/Widgets";
import { Layers, Flame, ArrowLeft, ExternalLink } from "lucide-react";

const ORDER = ["a_analyser", "a_contacter", "interesse", "rdv", "transmis_gael", "vendu", "perdu"];

export default function Pipeline() {
  const [data, setData] = useState(null);

  useEffect(() => {
    (async () => setData(await fetchPipeline()))();
  }, []);

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

        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Layers className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
            <h1 className="font-display text-3xl md:text-4xl font-semibold text-slate-100 tracking-tight">
              Pipeline commercial
            </h1>
          </div>
          <p className="text-slate-400 text-sm max-w-2xl">
            Vision consolidée des prospects par statut. Le pipeline s'alimente automatiquement
            au fur et à mesure de la qualification des maisons dans les fiches communes.
          </p>
        </div>

        {/* Kanban horizontal des statuts */}
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

        {/* Hot prospects */}
        <div className="flex items-center gap-2 mb-4">
          <Flame className="w-4 h-4 text-amber-400" strokeWidth={1.5} />
          <h2 className="font-display text-lg text-slate-100">Prospects actifs</h2>
          <span className="text-xs text-slate-500 ml-2">
            {data.hot_prospects.length} en cours de qualification
          </span>
        </div>

        {data.hot_prospects.length === 0 && (
          <div className="bbd-card p-8 text-center text-slate-500">
            Aucun prospect actif pour l'instant. Passez des maisons en « À contacter » depuis les fiches communes.
          </div>
        )}

        {data.hot_prospects.length > 0 && (
          <div className="bbd-card overflow-hidden">
            <table className="w-full bbd-table" data-testid="hot-prospects-table">
              <thead>
                <tr>
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
                {data.hot_prospects.map((h) => (
                  <tr key={h.id} data-testid={`hot-row-${h.id}`}>
                    <td>
                      <Link to={`/communes/${h.code_insee}`}
                            className="text-slate-100 hover:text-emerald-400"
                            data-testid={`hot-commune-link-${h.id}`}>
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </>
  );
}
