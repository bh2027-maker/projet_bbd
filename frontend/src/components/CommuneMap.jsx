import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";

const scoreToColor = (s) => {
  if (s >= 80) return "#10B981";
  if (s >= 70) return "#34D399";
  if (s >= 55) return "#F59E0B";
  return "#EF4444";
};

export default function CommuneMap({ communes }) {
  const navigate = useNavigate();
  // Skip first render to bypass React 19 StrictMode double-mount which
  // triggers leaflet "Map container is already initialized".
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setReady(true), 0);
    return () => clearTimeout(t);
  }, []);

  if (!ready) {
    return (
      <div className="bbd-card flex items-center justify-center text-slate-500"
           style={{ height: 480 }}>
        Chargement de la carte…
      </div>
    );
  }

  return (
    <div
      className="bbd-card overflow-hidden"
      style={{ height: 480 }}
      data-testid="communes-map"
    >
      <MapContainer
        center={[45.72, 6.13]}
        zoom={10}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; OpenStreetMap &copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {communes.map((c) => {
          const color = scoreToColor(c.score_bbd);
          const radius = 8 + (c.score_bbd / 100) * 14;
          return (
            <CircleMarker
              key={c.code_insee}
              center={[c.lat, c.lon]}
              radius={radius}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: 0.55,
                weight: 2,
              }}
              eventHandlers={{
                click: () => navigate(`/communes/${c.code_insee}`),
              }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div className="text-xs">
                  <div className="font-semibold">{c.nom}</div>
                  <div>Score BBD : <b>{c.score_bbd}</b>/100</div>
                  <div>{c.nb_maisons_individuelles} maisons indiv.</div>
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
