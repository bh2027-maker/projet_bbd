import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchCommune, generateAiComment, scoreLabel,
         discoverHouses, fetchHouses, fetchStatuses, statusColor } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge } from "../components/Widgets";
import HousesMap from "../components/HousesMap";
import HouseSheet from "../components/HouseSheet";
import MairieCard from "../components/MairieCard";
import EcosystemCard from "../components/EcosystemCard";
import { ArrowLeft, Sparkles, Mountain, Home as HomeIcon, Euro, Calendar,
         MapPin, Loader2, ExternalLink, Radar, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";

const criteres = [
  { key: "anciennete_parc", label: "Ancienneté du parc", weight: "30%", icon: Calendar },
  { key: "maisons_individuelles", label: "Part maisons individuelles", weight: "20%", icon: HomeIcon },
  { key: "volume_maisons", label: "Volume (nb maisons)", weight: "20%", icon: HomeIcon },
  { key: "revenu_median", label: "Revenu médian", weight: "20%", icon: Euro },
  { key: "climat_altitude", label: "Climat / Altitude H1", weight: "10%", icon: Mountain },
];

export default function CommuneDetail() {
  const { codeInsee } = useParams();
  const [c, setC] = useState(null);
  const [aiComment, setAiComment] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [houses, setHouses] = useState([]);
  const [housesLoaded, setHousesLoaded] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [selected, setSelected] = useState(null);
  const [houseQuery, setHouseQuery] = useState("");
  const [statuses, setStatuses] = useState([]);
  const [statusLabels, setStatusLabels] = useState({});

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchCommune(codeInsee);
        setC(data);
        if (data.ai_comment) setAiComment(data.ai_comment);
      } catch (e) {
        toast.error("Impossible de charger la commune");
      }
      try {
        const { statuses: s, labels } = await fetchStatuses();
        setStatuses(s); setStatusLabels(labels);
      } catch {}
      try {
        const { items } = await fetchHouses(codeInsee);
        setHouses(items);
        setHousesLoaded(true);
      } catch {}
    })();
  }, [codeInsee]);

  const askAi = async () => {
    setAiLoading(true);
    try {
      const { comment } = await generateAiComment(codeInsee);
      setAiComment(comment);
      toast.success("Analyse IA générée");
    } catch (e) {
      toast.error("Erreur IA : " + (e.response?.data?.detail || e.message));
    } finally {
      setAiLoading(false);
    }
  };

  const launchDiscovery = async () => {
    setDiscovering(true);
    toast.info("Détection en cours via OpenStreetMap/cadastre… (~15-30s)");
    try {
      const res = await discoverHouses(codeInsee);
      toast.success(`${res.maisons_detectees} maisons détectées · top score ${res.top_score}`);
      const { items } = await fetchHouses(codeInsee);
      setHouses(items);
      setHousesLoaded(true);
    } catch (e) {
      toast.error("Erreur détection : " + (e.response?.data?.detail || e.message));
    } finally {
      setDiscovering(false);
    }
  };

  const onHouseUpdated = (updated) => {
    setHouses((prev) => prev.map((h) => (h.id === updated.id ? { ...h, ...updated } : h)));
    setSelected((s) => (s && s.id === updated.id ? { ...s, ...updated } : s));
  };

  const filteredHouses = houses.filter((h) => {
    if (!houseQuery) return true;
    const q = houseQuery.toLowerCase();
    return (h.contact_nom || "").toLowerCase().includes(q) ||
           (h.notes || "").toLowerCase().includes(q) ||
           String(h.osm_id).includes(q) ||
           String(h.surface_habitable_estimee_m2).includes(q);
  });

  if (!c) return <><Header /><div className="p-10 text-slate-500">Chargement…</div></>;

  const gmaps = `https://www.google.com/maps/search/?api=1&query=${c.lat},${c.lon}`;

  return (
    <>
      <Header subtitle={`Fiche ${c.nom}`} />
      <main className="max-w-[1400px] mx-auto px-6 py-8" data-testid="commune-detail-main">
        <Link to="/"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-emerald-400 mb-6 transition-colors"
          data-testid="back-link">
          <ArrowLeft className="w-4 h-4" /> Retour au classement
        </Link>

        {/* En-tête */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <div className="text-[11px] uppercase tracking-[0.12em] text-slate-500 font-mono-data">
              Rang #{c.rank || "—"} · {scoreLabel(c.score_bbd)}
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-semibold text-slate-100 mt-1">
              {c.nom}
            </h1>
            <div className="text-slate-500 text-sm mt-2 font-mono-data">
              {c.code_postal} · INSEE {c.code_insee} · Département {c.departement}
              &nbsp;·&nbsp;<a href={gmaps} target="_blank" rel="noreferrer"
                className="text-emerald-400 hover:underline inline-flex items-center gap-1"
                data-testid="gmaps-link">
                Voir sur Google Maps <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
          <div className="text-center bbd-card px-8 py-5">
            <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-1">Score BBD</div>
            <ScoreBadge score={c.score_bbd} size="lg" />
            <div className="text-xs text-slate-500 mt-2">sur 100</div>
          </div>
        </div>

        {/* Grille données */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bbd-card p-5 md:col-span-1">
            <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-3">
              Données socio-démo
            </div>
            <div className="space-y-2.5 text-sm">
              <Row label="Population" value={`${c.population} hab.`} />
              <Row label="Logements totaux" value={c.nb_logements} />
              <Row label="Maisons individuelles" value={`${c.nb_maisons_individuelles} (${c.part_maisons_pct}%)`} />
              <Row label="Revenu médian" value={`${c.revenu_median.toLocaleString("fr-FR")} €`} />
            </div>
          </div>
          <div className="bbd-card p-5 md:col-span-1">
            <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-3">
              Bâti & climat
            </div>
            <div className="space-y-2.5 text-sm">
              <Row label="Logements avant 2000" value={`${c.part_logements_avant_2000_pct}%`} />
              <Row label="Altitude" value={`${c.altitude_m} m`} />
              <Row label="Zone climatique" value={c.zone_climatique} />
              <Row label="Coordonnées GPS" value={`${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}`} />
            </div>
          </div>
          <div className="bbd-card p-5 md:col-span-1 border-emerald-500/25">
            <div className="text-[10.5px] uppercase tracking-[0.12em] text-emerald-400 mb-3">
              Potentiel commercial
            </div>
            <div className="space-y-2.5 text-sm">
              <Row label="Dossiers BAR-TH-171 estimés" value={
                <span className="text-emerald-400 font-semibold font-mono-data">
                  {c.dossiers_bar_th_171_estimes}
                </span>
              } />
              <Row label="Priorité BBD" value={scoreLabel(c.score_bbd)} />
              <Row label="Statut" value={<span className="text-amber-400">À prospecter</span>} />
            </div>
          </div>
        </div>

        {/* Mairie (Module 8) */}
        <div className="mb-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MairieCard codeInsee={codeInsee} />
          <EcosystemCard codeInsee={codeInsee} />
        </div>

        {/* Breakdown score */}
        <div className="bbd-card p-6 mb-8" data-testid="score-breakdown">
          <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-4">
            Décomposition du score
          </div>
          <div className="space-y-3">
            {criteres.map(({ key, label, weight, icon: Icon }) => {
              const v = c.breakdown[key];
              return (
                <div key={key} className="flex items-center gap-4">
                  <Icon className="w-4 h-4 text-slate-500 shrink-0" strokeWidth={1.5} />
                  <div className="w-56 shrink-0 text-sm text-slate-300">{label}</div>
                  <div className="text-xs text-slate-500 w-12 font-mono-data">{weight}</div>
                  <div className="flex-1 h-2 rounded-sm bg-slate-800 overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-emerald-500/50 to-emerald-400"
                         style={{ width: `${v}%` }} />
                  </div>
                  <div className="font-mono-data text-slate-200 w-14 text-right">{v}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Commentaire IA */}
        <div className="bbd-card p-6 border-blue-500/25 bg-gradient-to-br from-slate-900 to-slate-900/50"
             data-testid="ai-comment-block">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-400" strokeWidth={1.5} />
              <div className="text-[10.5px] uppercase tracking-[0.12em] text-blue-400">
                Analyse IA · Claude Sonnet 4.5
              </div>
            </div>
            {!aiComment && (
              <Button
                onClick={askAi}
                disabled={aiLoading}
                data-testid="ai-generate-btn"
                className="bg-blue-500/15 border border-blue-500/40 text-blue-300 hover:bg-blue-500/25"
                size="sm"
              >
                {aiLoading
                  ? <><Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> Analyse…</>
                  : <>Générer l'analyse</>}
              </Button>
            )}
          </div>
          {aiComment ? (
            <p className="text-slate-200 leading-relaxed text-[15px]" data-testid="ai-comment-text">
              {aiComment}
            </p>
          ) : (
            <p className="text-slate-500 text-sm italic">
              Cliquez sur « Générer l'analyse » pour obtenir la synthèse commerciale de
              Claude sur cette commune (ancienneté, revenu, points d'attention).
            </p>
          )}
        </div>

        <div className="text-[11px] text-slate-600 mt-8 font-mono-data">
          Fiche générée par BBD · La prospection terrain reste sous la responsabilité du commercial.
        </div>

        {/* ---------- Module 2 : recensement des maisons ---------- */}
        <section className="mt-12" data-testid="houses-section">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Radar className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
              <h2 className="font-display text-xl text-slate-100">
                Recensement des maisons individuelles
              </h2>
              {housesLoaded && (
                <span className="text-xs text-slate-500 ml-2 font-mono-data">
                  {houses.length} maisons · source OSM/cadastre
                </span>
              )}
            </div>
            <Button
              onClick={launchDiscovery}
              disabled={discovering}
              data-testid="discover-btn"
              size="sm"
              className="bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/25"
            >
              {discovering
                ? <><Loader2 className="w-3.5 h-3.5 mr-2 animate-spin" /> Détection…</>
                : houses.length > 0
                  ? <>Relancer la détection</>
                  : <>Lancer la détection</>}
            </Button>
          </div>

          {!housesLoaded && (
            <div className="bbd-card p-8 text-center text-slate-500">
              Chargement…
            </div>
          )}

          {housesLoaded && houses.length === 0 && !discovering && (
            <div className="bbd-card p-8 text-center text-slate-500">
              Aucune maison détectée pour l'instant.{" "}
              <span className="text-slate-400">
                Cliquez sur « Lancer la détection » pour interroger OpenStreetMap/cadastre.
              </span>
            </div>
          )}

          {houses.length > 0 && (
            <>
              {/* Carte des maisons */}
              <div className="mb-4">
                <HousesMap
                  houses={houses}
                  center={[c.lat, c.lon]}
                  onSelect={setSelected}
                  selectedId={selected?.id}
                />
              </div>

              {/* Filtre + table */}
              <div className="flex flex-col md:flex-row gap-3 mb-3">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    data-testid="house-search"
                    value={houseQuery}
                    onChange={(e) => setHouseQuery(e.target.value)}
                    placeholder="Rechercher (OSM ID, surface, nom, notes)…"
                    className="pl-9 h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600 w-80"
                  />
                </div>
                <div className="text-xs text-slate-500 md:ml-auto self-center font-mono-data">
                  Cliquez sur une ligne (ou un polygone sur la carte) pour ouvrir la fiche prospect
                </div>
              </div>

              <div className="bbd-card overflow-hidden">
                <div className="max-h-[440px] overflow-y-auto">
                  <table className="w-full bbd-table" data-testid="houses-table">
                    <thead className="sticky top-0">
                      <tr>
                        <th className="w-12">#</th>
                        <th>Type</th>
                        <th className="text-right">Surface hab.</th>
                        <th className="text-right">Surface sol</th>
                        <th>Ancienneté</th>
                        <th className="text-right">% chauf. fossile</th>
                        <th>Statut</th>
                        <th className="text-right">Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredHouses.slice(0, 200).map((h) => (
                        <tr key={h.id}
                            data-testid={`house-row-${h.id}`}
                            onClick={() => setSelected(h)}>
                          <td className="font-mono-data text-slate-500">{h.rank}</td>
                          <td>
                            <div className="text-slate-100 text-xs">{h.type_label}</div>
                            <div className="text-[10px] text-slate-500 font-mono-data">OSM {h.osm_id}</div>
                          </td>
                          <td className="text-right font-mono-data text-slate-200">{h.surface_habitable_estimee_m2} m²</td>
                          <td className="text-right font-mono-data text-slate-400">{h.surface_sol_m2} m²</td>
                          <td className="text-xs text-slate-400">{h.age_label}</td>
                          <td className="text-right font-mono-data text-amber-400">{h.proba_chauffage_fossile_pct}%</td>
                          <td>
                            <span className={`text-[10.5px] px-2 py-0.5 rounded-sm border font-mono-data uppercase tracking-wider ${statusColor(h.status)}`}>
                              {statusLabels[h.status] || h.status}
                            </span>
                          </td>
                          <td className="text-right"><ScoreBadge score={h.score} /></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {filteredHouses.length > 200 && (
                  <div className="text-xs text-slate-500 text-center py-2 border-t border-slate-800 font-mono-data">
                    Affichage des 200 premières sur {filteredHouses.length} · affinez avec la recherche
                  </div>
                )}
              </div>
            </>
          )}
        </section>

        <HouseSheet
          house={selected}
          statuses={statuses}
          statusLabels={statusLabels}
          onClose={() => setSelected(null)}
          onUpdated={onHouseUpdated}
        />
      </main>
    </>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-center border-b border-slate-800/70 pb-2 last:border-0">
      <span className="text-slate-500 text-xs uppercase tracking-wider">{label}</span>
      <span className="text-slate-100 font-mono-data text-sm">{value}</span>
    </div>
  );
}
