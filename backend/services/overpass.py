"""Fetch real building footprints from OpenStreetMap via Overpass API."""
import math
import httpx
from typing import List, Dict, Any

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

UA = {"User-Agent": "BBD-ProspectIntelligence/1.0"}


def _polygon_area_m2(coords: List[Dict[str, float]]) -> float:
    """Approx polygon area in m² using equirectangular projection.
    coords = list of {'lat':..., 'lon':...}. Suitable for small polygons.
    """
    n = len(coords)
    if n < 3:
        return 0.0
    mean_lat = sum(c["lat"] for c in coords) / n
    R = 6378137.0
    cos_lat = math.cos(math.radians(mean_lat))
    xs = [R * math.radians(c["lon"]) * cos_lat for c in coords]
    ys = [R * math.radians(c["lat"]) for c in coords]
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j] - xs[j] * ys[i]
    return abs(area) / 2.0


def _centroid(coords: List[Dict[str, float]]) -> Dict[str, float]:
    n = len(coords)
    if n == 0:
        return {"lat": 0.0, "lon": 0.0}
    return {
        "lat": sum(c["lat"] for c in coords) / n,
        "lon": sum(c["lon"] for c in coords) / n,
    }


def _build_query(code_insee: str) -> str:
    return f"""
[out:json][timeout:60];
area["ref:INSEE"="{code_insee}"]->.a;
(
  way["building"="house"](area.a);
  way["building"="detached"](area.a);
  way["building"="residential"](area.a);
  way["building"="yes"](area.a);
);
out geom;
""".strip()


async def fetch_buildings(code_insee: str,
                          min_area: float = 55.0,
                          max_area: float = 500.0,
                          limit: int = 800) -> List[Dict[str, Any]]:
    """
    Fetch buildings within a commune, keep only those with reasonable
    footprint (min_area..max_area m²) — typical individual house range in France.
    """
    query = _build_query(code_insee)
    last_error = None
    async with httpx.AsyncClient(timeout=90) as client:
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                r = await client.post(endpoint,
                                      data={"data": query},
                                      headers=UA)
                r.raise_for_status()
                data = r.json()
                break
            except Exception as e:  # noqa
                last_error = e
                continue
        else:
            raise RuntimeError(f"Overpass unreachable: {last_error}")

    houses = []
    for el in data.get("elements", []):
        geom = el.get("geometry") or []
        if len(geom) < 3:
            continue
        area = _polygon_area_m2(geom)
        if area < min_area or area > max_area:
            continue
        c = _centroid(geom)
        tags = el.get("tags", {}) or {}
        building_type = tags.get("building", "yes")
        levels = None
        if "building:levels" in tags:
            try:
                levels = int(float(tags["building:levels"]))
            except Exception:  # noqa
                pass

        houses.append({
            "osm_id": el["id"],
            "lat": c["lat"],
            "lon": c["lon"],
            "surface_sol_m2": round(area, 1),
            "surface_habitable_estimee_m2": round(area * (levels or 1.4), 1),
            "levels": levels,
            "building_type": building_type,
            "roof_shape": tags.get("roof:shape"),
            "start_date": tags.get("start_date") or tags.get("building:year_built"),
            "addr_housenumber": tags.get("addr:housenumber"),
            "addr_street": tags.get("addr:street"),
            "footprint": [[p["lat"], p["lon"]] for p in geom],
        })

    # Sort by footprint desc (bigger houses first) and cap
    houses.sort(key=lambda h: h["surface_sol_m2"], reverse=True)
    return houses[:limit]
