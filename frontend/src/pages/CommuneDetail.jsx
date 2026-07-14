import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchCommune, generateAiComment, scoreLabel } from "../lib/api";
import Header from "../components/Header";
import { ScoreBadge } from "../components/Widgets";
import { ArrowLeft, Sparkles, Mountain, Home as HomeIcon, Euro, Calendar, MapPin, Loader2, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/button";

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

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchCommune(codeInsee);
        setC(data);
        if (data.ai_comment) setAiComment(data.ai_comment);
      } catch (e) {
        toast.error("Impossible de charger la commune");
      }
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
