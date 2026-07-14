"""
Enrichissement des maisons OSM avec les données réelles de BD TOPO IGN.
API : https://data.geopf.fr/wfs/ows (WFS 2.0)
Layer : BDTOPO_V3:batiment
"""
import math
import httpx
from typing import List, Dict, Any, Optional


WFS_URL = "https://data.geopf.fr/wfs/ows"


def _polygon_centroid(coords: List[List[float]]) -> tuple:
    """Centroid of a polygon ring (list of [lon, lat] or [lon, lat, z])."""
    n = len(coords)
    if n == 0:
        return (0.0, 0.0)
    lon = sum(c[0] for c in coords) / n
    lat = sum(c[1] for c in coords) / n
    return (lat, lon)


def _multipolygon_centroid(geom: Dict[str, Any]) -> tuple:
    if geom["type"] == "Polygon":
        return _polygon_centroid(geom["coordinates"][0])
    # MultiPolygon: use first ring of first polygon
    return _polygon_centroid(geom["coordinates"][0][0])


def _haversine_m(a_lat, a_lon, b_lat, b_lon):
    R = 6371000.0
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    aa = (math.sin(dlat/2)**2
          + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat))
          * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


async def fetch_bdtopo(bbox: Dict[str, float], limit: int = 3000) -> List[Dict[str, Any]]:
    """
    Fetch buildings inside a bbox. bbox = {min_lat, min_lon, max_lat, max_lon}.
    Returns simplified list [{lat, lon, date, logements, etages, hauteur, usage, materiaux}].
    """
    bbox_str = f"{bbox['min_lon']},{bbox['min_lat']},{bbox['max_lon']},{bbox['max_lat']},EPSG:4326"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(WFS_URL, params={
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "typeName": "BDTOPO_V3:batiment",
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "bbox": bbox_str, "count": limit,
        })
    r.raise_for_status()
    feats = r.json().get("features", [])
    out = []
    for f in feats:
        p = f.get("properties", {}) or {}
        try:
            lat, lon = _multipolygon_centroid(f["geometry"])
        except Exception:  # noqa
            continue
        date_raw = p.get("date_d_apparition")
        year = None
        if date_raw and isinstance(date_raw, str) and len(date_raw) >= 4:
            digits = date_raw[:4]
            if digits.isdigit():
                year = int(digits)
        out.append({
            "lat": lat, "lon": lon,
            "year": year,
            "logements": p.get("nombre_de_logements"),
            "etages": p.get("nombre_d_etages"),
            "hauteur_m": p.get("hauteur"),
            "usage": p.get("usage_1"),
            "materiaux_murs": p.get("materiaux_des_murs"),
            "materiaux_toit": p.get("materiaux_de_la_toiture"),
        })
    return out


def match_houses_to_bdtopo(
    houses: List[Dict[str, Any]],
    bdtopo: List[Dict[str, Any]],
    tolerance_m: float = 15.0,
) -> List[tuple]:
    """
    Return list of (house, matched_bdtopo | None). Uses simple nearest-neighbor
    within tolerance based on centroid distance.
    """
    matches = []
    for h in houses:
        best = None
        best_d = tolerance_m
        for b in bdtopo:
            d = _haversine_m(h["lat"], h["lon"], b["lat"], b["lon"])
            if d < best_d:
                best_d = d
                best = b
        matches.append((h, best))
    return matches


def compute_bbox(lat: float, lon: float, radius_km: float = 3.5) -> Dict[str, float]:
    """Simple square bbox around a center."""
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(math.radians(lat)))
    return {
        "min_lat": lat - dlat, "max_lat": lat + dlat,
        "min_lon": lon - dlon, "max_lon": lon + dlon,
    }
