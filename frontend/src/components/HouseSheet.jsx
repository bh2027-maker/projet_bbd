import { useState, useEffect } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./ui/sheet";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { ScoreBadge } from "./Widgets";
import { updateHouse, statusColor } from "../lib/api";
import { ExternalLink, MapPin, Save, User, Phone, Mail, Ruler, Calendar, Home as HomeIcon } from "lucide-react";
import { toast } from "sonner";

export default function HouseSheet({ house, statuses, statusLabels, onClose, onUpdated }) {
  const [local, setLocal] = useState(house);
  const [saving, setSaving] = useState(false);

  useEffect(() => { setLocal(house); }, [house?.id]);

  if (!local) return null;

  const gmaps = `https://www.google.com/maps/search/?api=1&query=${local.lat},${local.lon}`;
  const streetView = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${local.lat},${local.lon}`;
  const ign = `https://www.geoportail.gouv.fr/carte?c=${local.lon},${local.lat}&z=19&l0=ORTHOIMAGERY.ORTHOPHOTOS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes`;

  const save = async () => {
    setSaving(true);
    try {
      const updated = await updateHouse(local.id, {
        status: local.status,
        notes: local.notes || "",
        contact_nom: local.contact_nom || "",
        contact_tel: local.contact_tel || "",
        contact_email: local.contact_email || "",
      });
      toast.success("Fiche prospect enregistrée");
      onUpdated && onUpdated(updated);
    } catch (e) {
      toast.error("Erreur : " + (e.response?.data?.detail || e.message));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Sheet open={!!house} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-[540px] bg-[#0B0F19] border-l border-slate-800 text-slate-200 overflow-y-auto"
        data-testid="house-sheet"
      >
        <SheetHeader className="mb-4">
          <SheetTitle className="font-display text-2xl text-slate-100 flex items-center gap-3">
            <HomeIcon className="w-5 h-5 text-emerald-400" strokeWidth={1.5} />
            Maison #{local.rank}
            <ScoreBadge score={local.score} />
          </SheetTitle>
          <div className="text-xs text-slate-500 font-mono-data">
            {local.commune_nom} · {local.type_label} · OSM {local.osm_id}
          </div>
        </SheetHeader>

        {/* Données */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <Cell icon={Ruler} label="Surface sol" value={`${local.surface_sol_m2} m²`} />
          <Cell icon={Ruler} label="Surface hab. estimée" value={`${local.surface_habitable_estimee_m2} m²`} />
          <Cell icon={Calendar} label="Ancienneté" value={local.age_label} />
          <Cell icon={HomeIcon} label="Étages" value={local.levels || "n.c."} />
          <Cell icon={MapPin} label="GPS" value={`${local.lat.toFixed(5)}, ${local.lon.toFixed(5)}`} full />
        </div>

        {/* Score breakdown */}
        <div className="bbd-card p-4 mb-5" data-testid="house-breakdown">
          <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-3">
            Décomposition du score
          </div>
          {[
            ["Type de maison", "type_maison", "20%"],
            ["Ancienneté", "anciennete", "30%"],
            ["Surface", "surface", "20%"],
            ["Chauffage fossile prob.", "chauffage_fossile", "15%"],
            ["Accessibilité", "accessibilite", "10%"],
            ["Climat H1", "climat_h1", "5%"],
          ].map(([label, key, weight]) => (
            <div key={key} className="flex items-center gap-3 text-xs mb-2">
              <div className="w-40 text-slate-400">{label}</div>
              <div className="text-slate-600 w-10 font-mono-data">{weight}</div>
              <div className="flex-1 h-1.5 rounded-sm bg-slate-800 overflow-hidden">
                <div className="h-full bg-emerald-400/70"
                     style={{ width: `${local.breakdown[key]}%` }} />
              </div>
              <div className="font-mono-data w-10 text-right text-slate-200">
                {local.breakdown[key]}
              </div>
            </div>
          ))}
          <div className="text-xs text-slate-500 mt-2">
            Probabilité chauffage fossile : <span className="text-amber-400 font-mono-data">
              {local.proba_chauffage_fossile_pct}%
            </span>
          </div>
        </div>

        {/* Liens visuels */}
        <div className="bbd-card p-4 mb-5">
          <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-3">
            Vérification visuelle
          </div>
          <div className="flex flex-wrap gap-2">
            <ExtLink href={gmaps} testid="link-gmaps">Google Maps</ExtLink>
            <ExtLink href={streetView} testid="link-streetview">Street View</ExtLink>
            <ExtLink href={ign} testid="link-ign">IGN Orthophoto</ExtLink>
            <ExtLink
              href={`https://www.pagesjaunes.fr/pagesblanches/recherche?quoiqui=&ou=${encodeURIComponent(local.commune_nom)}`}
              testid="link-pagesjaunes"
            >
              Pages Jaunes ({local.commune_nom})
            </ExtLink>
          </div>
        </div>

        {/* Pipeline + contact */}
        <div className="bbd-card p-4 mb-5" data-testid="house-pipeline">
          <div className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500 mb-3">
            Statut prospect (Module 7)
          </div>
          <Select value={local.status} onValueChange={(v) => setLocal({ ...local, status: v })}>
            <SelectTrigger className="bg-slate-900 border-slate-700 text-slate-200" data-testid="house-status-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-slate-200">
              {statuses.map((s) => (
                <SelectItem key={s} value={s} className="text-slate-200 focus:bg-slate-800">
                  {statusLabels[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="grid grid-cols-1 gap-2 mt-4">
            <LabInput icon={User} placeholder="Nom du propriétaire (optionnel)"
              value={local.contact_nom || ""}
              onChange={(v) => setLocal({ ...local, contact_nom: v })} testid="house-contact-nom" />
            <LabInput icon={Phone} placeholder="Téléphone"
              value={local.contact_tel || ""}
              onChange={(v) => setLocal({ ...local, contact_tel: v })} testid="house-contact-tel" />
            <LabInput icon={Mail} placeholder="Email"
              value={local.contact_email || ""}
              onChange={(v) => setLocal({ ...local, contact_email: v })} testid="house-contact-email" />
          </div>

          <Textarea
            data-testid="house-notes"
            className="mt-3 bg-slate-900 border-slate-700 text-slate-200 min-h-[80px]"
            placeholder="Notes commerciales (visite, observations, cuve fioul visible, etc.)"
            value={local.notes || ""}
            onChange={(e) => setLocal({ ...local, notes: e.target.value })}
          />

          <Button
            onClick={save}
            disabled={saving}
            data-testid="house-save-btn"
            className="mt-3 w-full bg-emerald-500/20 border border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/30"
          >
            <Save className="w-3.5 h-3.5 mr-2" />
            {saving ? "Enregistrement…" : "Enregistrer la fiche prospect"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Cell({ icon: Icon, label, value, full }) {
  return (
    <div className={`bbd-card p-3 ${full ? "col-span-2" : ""}`}>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 flex items-center gap-1">
        {Icon && <Icon className="w-3 h-3" strokeWidth={1.5} />}
        {label}
      </div>
      <div className="font-mono-data text-slate-100 text-sm mt-1">{value}</div>
    </div>
  );
}

function ExtLink({ href, children, testid }) {
  return (
    <a href={href} target="_blank" rel="noreferrer"
       data-testid={testid}
       className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm border border-slate-700
                  bg-slate-800/60 text-slate-300 text-xs hover:border-emerald-500/50 hover:text-emerald-300 transition-colors">
      {children} <ExternalLink className="w-3 h-3" />
    </a>
  );
}

function LabInput({ icon: Icon, placeholder, value, onChange, testid }) {
  return (
    <div className="relative">
      {Icon && <Icon className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />}
      <Input data-testid={testid}
        value={value} onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pl-9 h-9 bg-slate-900 border-slate-700 text-slate-200 placeholder:text-slate-600" />
    </div>
  );
}
