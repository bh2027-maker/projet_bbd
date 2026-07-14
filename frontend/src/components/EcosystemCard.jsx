import { useEffect, useState } from "react";
import { fetchEcosysteme } from "../lib/api";
import { Store, Loader2, Users, Wrench, UtensilsCrossed, Car, Sprout, Stethoscope, ChevronDown, ChevronRight } from "lucide-react";

const ICONS = {
  artisans_btp: Wrench,
  commerces_proximite: Store,
  restauration: UtensilsCrossed,
  auto_moto: Car,
  bricolage_agri: Sprout,
  sante: Stethoscope,
  associations_sport_culture: Users,
};

export default function EcosystemCard({ codeInsee }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const d = await fetchEcosysteme(codeInsee);
        setData(d);
      } catch {
        setData(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [codeInsee]);

  if (loading) return (
    <div className="bbd-card p-5 flex items-center gap-2 text-slate-500 text-sm">
      <Loader2 className="w-4 h-4 animate-spin" /> Chargement écosystème local…
    </div>
  );
  if (!data || !data.total) return null;

  const cats = Object.entries(data.categories || {}).filter(([_, c]) => c.count > 0);

  return (
    <div className="bbd-card p-5" data-testid="ecosystem-card">
      <div className="flex items-center gap-2 mb-4">
        <Store className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
        <h3 className="font-display text-lg text-slate-100">Écosystème local</h3>
        <span className="text-xs text-slate-500 ml-2 font-mono-data">
          {data.total} acteurs · source SIRENE
        </span>
      </div>
      <p className="text-xs text-slate-500 mb-4 max-w-2xl">
        Ces acteurs peuvent servir de relais locaux pour ouvrir des portes ou obtenir des recommandations
        (artisans partenaires, commerces où déposer un flyer, associations à sensibiliser…).
      </p>

      <div className="space-y-2">
        {cats.map(([key, cat]) => {
          const Icon = ICONS[key] || Store;
          const isOpen = open === key;
          return (
            <div key={key} className="border border-slate-800 rounded-sm bg-slate-900/40"
                 data-testid={`eco-category-${key}`}>
              <button
                onClick={() => setOpen(isOpen ? null : key)}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/40 transition-colors"
                data-testid={`eco-toggle-${key}`}
              >
                <Icon className="w-4 h-4 text-slate-400" strokeWidth={1.5} />
                <span className="text-sm text-slate-200 font-medium flex-1 text-left">{cat.label}</span>
                <span className="text-xs text-slate-500 font-mono-data">{cat.count}</span>
                {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
              </button>
              {isOpen && (
                <div className="border-t border-slate-800 divide-y divide-slate-800/70">
                  {cat.entities.map((e) => (
                    <div key={e.siret} className="px-4 py-2 text-xs" data-testid={`eco-entity-${e.siret}`}>
                      <div className="text-slate-200 font-medium">{e.nom}</div>
                      <div className="text-slate-500 font-mono-data mt-0.5">
                        {e.activite_libelle || e.naf} · {e.commune}
                        {e.adresse && ` · ${e.adresse}`}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
