import { useEffect, useState } from "react";
import { fetchMairie } from "../lib/api";
import { Building2, Phone, Mail, Globe, ExternalLink } from "lucide-react";

export default function MairieCard({ codeInsee }) {
  const [m, setM] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchMairie(codeInsee);
        setM(data && data.nom ? data : null);
      } catch {
        setM(null);
      } finally {
        setLoaded(true);
      }
    })();
  }, [codeInsee]);

  if (!loaded) return null;
  if (!m) return null;

  return (
    <div className="bbd-card p-5 border-blue-500/25" data-testid="mairie-card">
      <div className="flex items-center gap-2 mb-3">
        <Building2 className="w-4 h-4 text-blue-400" strokeWidth={1.5} />
        <div className="text-[10.5px] uppercase tracking-[0.12em] text-blue-400">
          Mairie · Point de contact local
        </div>
      </div>
      <div className="text-slate-100 font-medium mb-1">{m.nom}</div>
      {m.adresse && <div className="text-xs text-slate-400 mb-3">{m.adresse}</div>}
      <div className="space-y-1.5 text-sm">
        {m.telephone && (
          <a href={`tel:${m.telephone.replace(/\s/g, "")}`}
             data-testid="mairie-tel"
             className="flex items-center gap-2 text-slate-200 hover:text-emerald-400 transition-colors">
            <Phone className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span className="font-mono-data">{m.telephone}</span>
          </a>
        )}
        {m.email && (
          <a href={`mailto:${m.email}`}
             data-testid="mairie-email"
             className="flex items-center gap-2 text-slate-200 hover:text-emerald-400 transition-colors truncate">
            <Mail className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span className="font-mono-data text-xs">{m.email}</span>
          </a>
        )}
        {m.site_web && (
          <a href={m.site_web} target="_blank" rel="noreferrer"
             data-testid="mairie-site"
             className="flex items-center gap-2 text-slate-200 hover:text-emerald-400 transition-colors">
            <Globe className="w-3.5 h-3.5" strokeWidth={1.5} />
            <span className="text-xs">Site web</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  );
}
