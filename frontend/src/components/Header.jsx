import { Radar, Layers } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function Header({ subtitle }) {
  const loc = useLocation();
  return (
    <header
      data-testid="app-header"
      className="border-b border-slate-800 bg-[#0B0F19]/80 backdrop-blur-md sticky top-0 z-20"
    >
      <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group" data-testid="header-home-link">
          <div className="w-9 h-9 rounded-sm border border-emerald-500/40 bg-emerald-500/10 flex items-center justify-center">
            <Radar className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
          </div>
          <div>
            <div className="font-display font-semibold text-[15px] tracking-tight text-slate-100">
              BBD · Prospect Intelligence
            </div>
            <div className="text-[11px] text-slate-500 uppercase tracking-[0.12em] font-mono-data">
              {subtitle || "Massif des Bauges · Opération PAC 2026"}
            </div>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          <Link to="/"
            data-testid="nav-communes"
            className={`text-xs px-3 py-1.5 rounded-sm border transition-colors ${
              loc.pathname === "/"
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
            }`}>
            Communes
          </Link>
          <Link to="/pipeline"
            data-testid="nav-pipeline"
            className={`text-xs px-3 py-1.5 rounded-sm border transition-colors inline-flex items-center gap-1.5 ${
              loc.pathname === "/pipeline"
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                : "border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
            }`}>
            <Layers className="w-3 h-3" /> Pipeline
          </Link>
          <div className="hidden md:flex items-center gap-2 text-[11px] font-mono-data text-slate-500 ml-3">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            Moteur actif
          </div>
        </nav>
      </div>
    </header>
  );
}
