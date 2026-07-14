"""
Générateur PDF de feuille de route commerciale pour Gaël.
Prend une liste de maisons, calcule un ordre de visite optimisé (nearest neighbor),
et produit un PDF imprimable A4.
"""
import io
import math
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas


def _haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    R = 6371.0
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    aa = (math.sin(dlat / 2) ** 2
          + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat))
          * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


def optimize_route(houses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Nearest-neighbor heuristic starting from the highest-scoring house."""
    if not houses:
        return []
    remaining = list(houses)
    # Start with the best-scoring house
    remaining.sort(key=lambda h: h["score"], reverse=True)
    route = [remaining.pop(0)]
    while remaining:
        last = route[-1]
        remaining.sort(key=lambda h: _haversine_km(last["lat"], last["lon"], h["lat"], h["lon"]))
        route.append(remaining.pop(0))
    return route


def _total_distance_km(route: List[Dict[str, Any]]) -> float:
    if len(route) < 2:
        return 0.0
    d = 0.0
    for i in range(len(route) - 1):
        d += _haversine_km(route[i]["lat"], route[i]["lon"],
                           route[i+1]["lat"], route[i+1]["lon"])
    return d


BG = HexColor("#0B0F19")
CARD = HexColor("#111827")
BORDER = HexColor("#1E293B")
GREEN = HexColor("#10B981")
AMBER = HexColor("#F59E0B")
RED = HexColor("#EF4444")
GRAY = HexColor("#6B7280")
LIGHT = HexColor("#E5E7EB")


def _score_color(score: float):
    if score >= 75:
        return GREEN
    if score >= 55:
        return AMBER
    return RED


STATUS_LABELS = {
    "a_analyser": "À analyser", "a_contacter": "À contacter",
    "interesse": "Intéressé", "rdv": "Rendez-vous",
    "transmis_gael": "Transmis à Gaël", "vendu": "Vendu", "perdu": "Perdu",
}


def build_tour_pdf(houses: List[Dict[str, Any]], meta: Dict[str, Any]) -> bytes:
    """
    Produit un PDF (bytes) contenant :
      - Couverture (date, nb prospects, distance totale, carte des points)
      - 1 page par maison avec fiche complète + espace notes terrain
    """
    route = optimize_route(houses)
    total_km = _total_distance_km(route)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    # ---------- COVER PAGE ----------
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Header band
    c.setFillColor(GREEN)
    c.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)

    # Title
    c.setFillColor(LIGHT)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(20*mm, H - 30*mm, "Feuille de route BBD")
    c.setFont("Helvetica", 12)
    c.setFillColor(GRAY)
    c.drawString(20*mm, H - 38*mm,
                 f"Prospect Intelligence · Massif des Bauges · {meta.get('date', datetime.now().strftime('%d/%m/%Y'))}")

    # Metrics box
    y = H - 60*mm
    c.setStrokeColor(BORDER)
    c.setFillColor(CARD)
    c.rect(20*mm, y - 30*mm, W - 40*mm, 30*mm, fill=1, stroke=1)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    labels = ["Prospects", "Distance totale estimée", "Score moyen", "Top score"]
    values = [
        f"{len(route)}",
        f"{total_km:.1f} km",
        f"{sum(h['score'] for h in route) / max(len(route), 1):.1f}/100",
        f"{max((h['score'] for h in route), default=0):.1f}/100",
    ]
    col_w = (W - 40*mm) / 4
    for i, (lbl, val) in enumerate(zip(labels, values)):
        x = 20*mm + i * col_w + 5*mm
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(x, y - 10*mm, lbl.upper())
        c.setFillColor(LIGHT)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(x, y - 20*mm, val)

    # Route list
    c.setFillColor(LIGHT)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(20*mm, y - 45*mm, "Ordre de visite recommandé")
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawString(20*mm, y - 51*mm,
                 "Optimisé par proximité géographique à partir du meilleur score")

    # List of houses
    list_y = y - 60*mm
    line_h = 8*mm
    max_rows = int((list_y - 20*mm) / line_h)
    for i, h in enumerate(route[:max_rows]):
        row_y = list_y - i * line_h
        # rank badge
        c.setFillColor(_score_color(h["score"]))
        c.circle(24*mm, row_y, 3*mm, fill=1, stroke=0)
        c.setFillColor(BG)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(24*mm, row_y - 2, str(i + 1))
        # info
        c.setFillColor(LIGHT)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(32*mm, row_y - 1, h["commune_nom"])
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        info = f"{h['type_label']} · {h['surface_habitable_estimee_m2']} m² · {STATUS_LABELS.get(h.get('status','a_analyser'))}"
        c.drawString(72*mm, row_y - 1, info)
        # score right
        c.setFillColor(_score_color(h["score"]))
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - 25*mm, row_y - 1, f"{h['score']:.1f}")

    # Footer
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(20*mm, 12*mm,
                 "BBD · Prospect Intelligence · Document confidentiel — usage interne uniquement")

    # ---------- INDIVIDUAL PAGES ----------
    for i, h in enumerate(route):
        c.showPage()
        c.setFillColor(BG)
        c.rect(0, 0, W, H, fill=1, stroke=0)

        # Header band
        c.setFillColor(_score_color(h["score"]))
        c.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)

        # Rank + title
        c.setFillColor(LIGHT)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(20*mm, H - 25*mm, f"#{i+1} · {h['commune_nom']}")
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 10)
        c.drawString(20*mm, H - 32*mm, f"{h['type_label']} · OSM {h['osm_id']}")

        # Score badge
        col = _score_color(h["score"])
        c.setFillColor(col)
        c.roundRect(W - 55*mm, H - 30*mm, 35*mm, 12*mm, 2*mm, fill=1, stroke=0)
        c.setFillColor(BG)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(W - 37.5*mm, H - 25*mm, f"{h['score']:.1f}")
        c.setFont("Helvetica", 6)
        c.drawCentredString(W - 37.5*mm, H - 28*mm, "SCORE / 100")

        # Data grid
        y2 = H - 50*mm
        c.setStrokeColor(BORDER)
        c.setFillColor(CARD)
        c.rect(20*mm, y2 - 55*mm, W - 40*mm, 55*mm, fill=1, stroke=1)

        rows = [
            ("Surface habitable estimée", f"{h['surface_habitable_estimee_m2']} m²"),
            ("Surface au sol", f"{h['surface_sol_m2']} m²"),
            ("Ancienneté", h["age_label"]),
            ("Étages", str(h.get("levels") or "n.c.")),
            ("Chauffage fossile probable", f"{h['proba_chauffage_fossile_pct']}%"),
            ("Coordonnées GPS", f"{h['lat']:.5f}, {h['lon']:.5f}"),
            ("Statut prospect", STATUS_LABELS.get(h.get("status", "a_analyser"), h.get("status"))),
        ]
        for j, (k, v) in enumerate(rows):
            row_y = y2 - 8*mm - j * 7*mm
            c.setFillColor(GRAY)
            c.setFont("Helvetica", 8)
            c.drawString(25*mm, row_y, k.upper())
            c.setFillColor(LIGHT)
            c.setFont("Helvetica", 10)
            c.drawString(85*mm, row_y, v)

        # Visual verification links
        y3 = y2 - 65*mm
        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(20*mm, y3, "VÉRIFICATION VISUELLE (à ouvrir sur téléphone)")
        c.setFillColor(LIGHT)
        c.setFont("Helvetica", 8)
        gmaps = f"maps.google.com/?q={h['lat']},{h['lon']}"
        sv = f"maps.google.com/?layer=c&cbll={h['lat']},{h['lon']}"
        ign = f"geoportail.gouv.fr/carte?c={h['lon']},{h['lat']}&z=19"
        c.drawString(20*mm, y3 - 6*mm, f"• Google Maps : {gmaps}")
        c.drawString(20*mm, y3 - 11*mm, f"• Street View : {sv}")
        c.drawString(20*mm, y3 - 16*mm, f"• IGN Ortho   : {ign}")

        # Existing notes
        y4 = y3 - 25*mm
        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(20*mm, y4, "NOTES ACTUELLES BBD")
        c.setFillColor(LIGHT)
        c.setFont("Helvetica", 9)
        notes_txt = h.get("notes") or "(aucune)"
        for k, line in enumerate(_wrap(notes_txt, 90)[:3]):
            c.drawString(20*mm, y4 - 6*mm - k * 5*mm, line)

        # Contact
        y5 = y4 - 25*mm
        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(20*mm, y5, "CONTACT")
        c.setFillColor(LIGHT)
        c.setFont("Helvetica", 9)
        c.drawString(20*mm, y5 - 6*mm,
                     f"Nom : {h.get('contact_nom') or '____________________________'}")
        c.drawString(20*mm, y5 - 12*mm,
                     f"Tél : {h.get('contact_tel') or '____________________________'}")
        c.drawString(20*mm, y5 - 18*mm,
                     f"Mail: {h.get('contact_email') or '____________________________'}")

        # Field notes area
        y6 = y5 - 30*mm
        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(20*mm, y6, "OBSERVATIONS TERRAIN")
        c.setStrokeColor(BORDER)
        c.setFillColor(CARD)
        c.rect(20*mm, 20*mm, W - 40*mm, y6 - 25*mm, fill=1, stroke=1)
        # Ruled lines
        for k in range(int((y6 - 25*mm) / 6*mm) - 1):
            ly = y6 - 8*mm - k * 6*mm
            if ly < 25*mm:
                break
            c.setStrokeColor(BORDER)
            c.line(24*mm, ly, W - 24*mm, ly)

        # Footer
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawRightString(W - 20*mm, 12*mm, f"Page {i+2} / {len(route)+1}")

    c.save()
    return buf.getvalue()


def _wrap(text: str, width: int) -> List[str]:
    words = (text or "").split()
    lines, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 > width:
            lines.append(current)
            current = w
        else:
            current = f"{current} {w}".strip()
    if current:
        lines.append(current)
    return lines
