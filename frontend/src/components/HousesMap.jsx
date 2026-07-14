import { MapContainer, TileLayer, Polygon, CircleMarker, Tooltip } from "react-leaflet";
import { useEffect, useState, useMemo } from "react";

const scoreColorHex = (s) => {
  if (s >= 75) return "#10B981";
  if (s >= 65) return "#34D399";
  if (s >= 55) return "#F59E0B";
  return "#EF4444";
};

/**
 * Carte détaillée d'une commune montrant les footprints des maisons détectées.
 * onSelect(house) déclenché au clic.
 */
export default function HousesMap({ houses, center, onSelect, selectedId }) {
  const [ready, setReady] = useState(false);
  useEffect(() => { setReady(true); }, []);

  const bounds = useMemo(() => {
    if (!houses.length) return null;
    const lats = houses.map((h) => h.lat);
    const lons = houses.map((h) => h.lon);
    return [
      [Math.min(...lats) - 0.002, Math.min(...lons) - 0.002],
      [Math.max(...lats) + 0.002, Math.max(...lons) + 0.002],
    ];
  }, [houses]);

  if (!ready) {
    return (
      <div className="bbd-card flex items-center justify-center text-slate-500"
           style={{ height: 500 }}>
        Chargement de la carte…
      </div>
    );
  }

  return (
    <div className="bbd-card overflow-hidden" style={{ height: 500 }}
         data-testid="houses-map">
      <MapContainer
        center={center || [45.72, 6.13]}
        zoom={14}
        bounds={bounds || undefined}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; OSM &copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {houses.map((h) => {
          const color = scoreColorHex(h.score);
          const isSelected = selectedId === h.id;
          return h.footprint && h.footprint.length >= 3 ? (
            <Polygon
              key={h.id}
              positions={h.footprint}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: isSelected ? 0.75 : 0.4,
                weight: isSelected ? 3 : 1.5,
              }}
              eventHandlers={{ click: () => onSelect(h) }}
            >
              <Tooltip direction="top" offset={[0, -6]}>
                <div className="text-xs">
                  <div className="font-semibold">{h.type_label}</div>
                  <div>Score <b>{h.score}</b>/100 · {h.surface_habitable_estimee_m2} m²</div>
                </div>
              </Tooltip>
            </Polygon>
          ) : (
            <CircleMarker
              key={h.id}
              center={[h.lat, h.lon]}
              radius={6}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.55, weight: 2 }}
              eventHandlers={{ click: () => onSelect(h) }}
            >
              <Tooltip direction="top">
                Score {h.score}/100
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
