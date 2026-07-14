"""
Générateur PDF v2 : feuille de route avec CEE, photo satellite IGN,
découpage multi-jours.
"""
import io
import math
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from services.cee_estimator import estimate_aides
from services.ign_tiles import fetch_ortho_image


def _haversine_km(a_lat, a_lon, b_lat, b_lon):
    R = 6371.0
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    aa = (math.sin(dlat/2)**2
          + math.cos(math.radians(a_lat))*math.cos(math.radians(b_lat))
          * math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(aa), math.sqrt(1 - aa))


def _optimize(houses):
    if not houses:
        return []
    remaining = list(houses)
    remaining.sort(key=lambda h: h["score"], reverse=True)
    route = [remaining.pop(0)]
    while remaining:
        last = route[-1]
        remaining.sort(key=lambda h: _haversine_km(last["lat"], last["lon"], h["lat"], h["lon"]))
        route.append(remaining.pop(0))
    return route


def split_days(houses, max_per_day: int = 8, max_km_per_day: float = 40.0) -> List[List[Dict]]:
    """Répartit les maisons en journées respectant les plafonds visites+km."""
    if not houses:
        return []
    ordered = _optimize(houses)
    days: List[List[Dict]] = []
    current: List[Dict] = []
    km = 0.0
    for h in ordered:
        if not current:
            current.append(h)
            continue
        last = current[-1]
        dist = _haversine_km(last["lat"], last["lon"], h["lat"], h["lon"])
        if (len(current) + 1) > max_per_day or (km + dist) > max_km_per_day:
            days.append(current)
            current = [h]
            km = 0.0
        else:
            current.append(h)
            km += dist
    if current:
        days.append(current)
    return days


def _day_distance(day):
    if len(day) < 2:
        return 0.0
    return sum(_haversine_km(day[i]["lat"], day[i]["lon"],
                              day[i+1]["lat"], day[i+1]["lon"])
               for i in range(len(day)-1))


BG = HexColor("#0B0F19")
CARD = HexColor("#111827")
BORDER = HexColor("#1E293B")
GREEN = HexColor("#10B981")
BLUE = HexColor("#3B82F6")
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


def _wrap(text, width=90):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur: lines.append(cur)
    return lines


def _draw_cover(c, W, H, days, meta, communes_by_code):
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(GREEN); c.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)

    c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 26)
    c.drawString(20*mm, H - 30*mm, "Feuille de route BBD")
    c.setFont("Helvetica", 12); c.setFillColor(GRAY)
    c.drawString(20*mm, H - 38*mm,
                 f"Prospect Intelligence · Massif des Bauges · {meta.get('date', datetime.now().strftime('%d/%m/%Y'))}")

    total_h = sum(len(d) for d in days)
    total_km = sum(_day_distance(d) for d in days)
    all_h = [h for d in days for h in d]
    avg_score = sum(h["score"] for h in all_h) / max(len(all_h), 1)
    top_score = max((h["score"] for h in all_h), default=0)
    total_aides_low = sum(estimate_aides(h["surface_habitable_estimee_m2"],
                                          communes_by_code.get(h["code_insee"], {}).get("revenu_median", 27000))["aides_low"]
                          for h in all_h)

    y = H - 60*mm
    c.setStrokeColor(BORDER); c.setFillColor(CARD)
    c.rect(20*mm, y - 32*mm, W - 40*mm, 32*mm, fill=1, stroke=1)
    metrics = [("Journées", str(len(days))),
               ("Prospects", str(total_h)),
               ("Distance totale", f"{total_km:.1f} km"),
               ("Score moyen", f"{avg_score:.1f}/100"),
               ("Aides mini estimées", f"{total_aides_low:,}€".replace(",", " "))]
    col_w = (W - 40*mm) / len(metrics)
    for i, (lbl, val) in enumerate(metrics):
        x = 20*mm + i * col_w + 5*mm
        c.setFillColor(GRAY); c.setFont("Helvetica", 7)
        c.drawString(x, y - 10*mm, lbl.upper())
        c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y - 20*mm, val)

    # Days summary
    c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 13)
    c.drawString(20*mm, y - 48*mm, "Résumé des journées")

    for j, day in enumerate(days):
        dy = y - 58*mm - j * 12*mm
        c.setFillColor(BLUE); c.circle(24*mm, dy + 2, 3.5*mm, fill=1, stroke=0)
        c.setFillColor(BG); c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(24*mm, dy - 1, f"J{j+1}")
        c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 10)
        c.drawString(32*mm, dy + 1, f"Jour {j+1}")
        c.setFillColor(GRAY); c.setFont("Helvetica", 9)
        c.drawString(52*mm, dy + 1,
                     f"{len(day)} prospects · {_day_distance(day):.1f} km · "
                     f"communes: {', '.join(sorted({h['commune_nom'] for h in day}))[:70]}")

    c.setFillColor(GRAY); c.setFont("Helvetica", 7)
    c.drawString(20*mm, 12*mm,
                 "BBD · Prospect Intelligence · Document confidentiel — usage interne uniquement")


async def _draw_house_page(c, W, H, h, i, total, day_idx, day_total, commune_ctx):
    c.showPage()
    c.setFillColor(BG); c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(_score_color(h["score"])); c.rect(0, H - 6*mm, W, 6*mm, fill=1, stroke=0)

    # Title
    c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 18)
    c.drawString(20*mm, H - 22*mm, f"J{day_idx+1} · #{i+1}/{day_total} · {h['commune_nom']}")
    c.setFillColor(GRAY); c.setFont("Helvetica", 9)
    c.drawString(20*mm, H - 28*mm, f"{h['type_label']} · OSM {h['osm_id']}")

    # Score badge
    col = _score_color(h["score"])
    c.setFillColor(col); c.roundRect(W - 45*mm, H - 27*mm, 25*mm, 10*mm, 2*mm, fill=1, stroke=0)
    c.setFillColor(BG); c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W - 32.5*mm, H - 22*mm, f"{h['score']:.1f}")
    c.setFont("Helvetica", 5)
    c.drawCentredString(W - 32.5*mm, H - 25.5*mm, "SCORE / 100")

    # --- Left: satellite photo IGN ---
    photo_x = 20*mm; photo_y = H - 110*mm
    photo_w = 75*mm; photo_h = 75*mm
    try:
        img_bytes = await fetch_ortho_image(h["lat"], h["lon"], zoom=18, grid=3)
        img = ImageReader(io.BytesIO(img_bytes))
        c.drawImage(img, photo_x, photo_y, width=photo_w, height=photo_h,
                    preserveAspectRatio=True, mask="auto")
        c.setStrokeColor(BORDER); c.rect(photo_x, photo_y, photo_w, photo_h, fill=0, stroke=1)
    except Exception:  # noqa
        c.setFillColor(CARD); c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)
        c.setFillColor(GRAY); c.setFont("Helvetica", 8)
        c.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2, "(photo satellite indisponible)")
    c.setFillColor(GRAY); c.setFont("Helvetica", 7)
    c.drawString(photo_x, photo_y - 4*mm, "Orthophoto IGN · Géoplateforme (zoom 18)")

    # --- Right: house data grid ---
    dx = 105*mm; dy_top = H - 40*mm
    c.setStrokeColor(BORDER); c.setFillColor(CARD)
    c.rect(dx, dy_top - 74*mm, W - dx - 20*mm, 74*mm, fill=1, stroke=1)
    rows = [
        ("Surface habitable", f"{h['surface_habitable_estimee_m2']} m²"),
        ("Surface au sol", f"{h['surface_sol_m2']} m²"),
        ("Ancienneté", h.get("age_label", "n.c.")),
        ("Étages", str(h.get("levels") or h.get("bdtopo_etages") or "n.c.")),
        ("Chauffage fossile prob.", f"{h['proba_chauffage_fossile_pct']}%"),
        ("Coordonnées GPS", f"{h['lat']:.5f}, {h['lon']:.5f}"),
        ("Statut prospect", STATUS_LABELS.get(h.get("status", "a_analyser"), h.get("status"))),
    ]
    for j, (k, v) in enumerate(rows):
        row_y = dy_top - 8*mm - j * 8*mm
        c.setFillColor(GRAY); c.setFont("Helvetica", 7)
        c.drawString(dx + 4*mm, row_y, k.upper())
        c.setFillColor(LIGHT); c.setFont("Helvetica", 9)
        c.drawString(dx + 45*mm, row_y, str(v))

    # --- CEE panel ---
    aides = estimate_aides(h["surface_habitable_estimee_m2"],
                            commune_ctx.get("revenu_median", 27000))
    cee_y = photo_y - 24*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 9)
    c.drawString(20*mm, cee_y + 12*mm, "ARGUMENT COMMERCIAL — AIDES ESTIMÉES")

    c.setStrokeColor(GREEN); c.setFillColor(HexColor("#0f2a1f"))
    c.rect(20*mm, cee_y - 20*mm, W - 40*mm, 30*mm, fill=1, stroke=1)
    c.setFillColor(LIGHT); c.setFont("Helvetica-Bold", 16)
    c.drawString(25*mm, cee_y + 4*mm,
                 f"{aides['aides_low']:,}€".replace(",", " ") + " — " +
                 f"{aides['aides_high']:,}€".replace(",", " "))
    c.setFillColor(GRAY); c.setFont("Helvetica", 8)
    c.drawString(25*mm, cee_y - 2*mm,
                 f"Coup de pouce CEE : {aides['coup_de_pouce']:,}€".replace(",", " ") +
                 f"   ·   MaPrimeRénov' : {aides['mpr_low']:,}-{aides['mpr_high']:,}€".replace(",", " ") +
                 f"   ·   TVA 5,5% : ~{aides['tva_savings']:,}€".replace(",", " "))
    c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 8)
    for k, line in enumerate(_wrap(aides["argument"], 110)):
        c.drawString(25*mm, cee_y - 8*mm - k * 4*mm, line)

    # --- Bottom: liens + notes + contact + observations ---
    y2 = cee_y - 28*mm
    c.setFillColor(GRAY); c.setFont("Helvetica-Bold", 7)
    c.drawString(20*mm, y2, "VÉRIFICATION VISUELLE (téléphone)")
    c.setFillColor(LIGHT); c.setFont("Helvetica", 7)
    c.drawString(20*mm, y2 - 4*mm, f"Google Maps : maps.google.com/?q={h['lat']},{h['lon']}")
    c.drawString(20*mm, y2 - 8*mm, f"Street View : maps.google.com/?layer=c&cbll={h['lat']},{h['lon']}")

    y3 = y2 - 16*mm
    c.setFillColor(GRAY); c.setFont("Helvetica-Bold", 7)
    c.drawString(20*mm, y3, "CONTACT")
    c.setFillColor(LIGHT); c.setFont("Helvetica", 8)
    c.drawString(20*mm, y3 - 5*mm, f"Nom : {h.get('contact_nom') or '____________________________'}")
    c.drawString(90*mm, y3 - 5*mm, f"Tél : {h.get('contact_tel') or '____________________________'}")

    y4 = y3 - 12*mm
    c.setFillColor(GRAY); c.setFont("Helvetica-Bold", 7)
    c.drawString(20*mm, y4, "OBSERVATIONS TERRAIN")
    c.setStrokeColor(BORDER); c.setFillColor(CARD)
    bottom_h = y4 - 22*mm
    c.rect(20*mm, 22*mm, W - 40*mm, y4 - 25*mm, fill=1, stroke=1)
    for k in range(int((y4 - 25*mm) / (6*mm))):
        ly = y4 - 6*mm - k * 6*mm
        if ly < 25*mm: break
        c.setStrokeColor(BORDER); c.line(24*mm, ly, W - 24*mm, ly)

    # Footer
    c.setFillColor(GRAY); c.setFont("Helvetica", 6)
    c.drawRightString(W - 20*mm, 12*mm, f"Prospect {i+1}/{total}")


async def build_tour_pdf_v2(houses: List[Dict[str, Any]],
                             communes: List[Dict[str, Any]],
                             meta: Dict[str, Any],
                             max_per_day: int = 8,
                             max_km_per_day: float = 40.0) -> bytes:
    """
    Version 2 avec :
    - Découpage multi-journées (max_per_day / max_km_per_day)
    - Estimation CEE par maison (basée sur revenu médian communal)
    - Photo satellite IGN embarquée
    """
    days = split_days(houses, max_per_day=max_per_day, max_km_per_day=max_km_per_day)
    communes_by_code = {c["code_insee"]: c for c in communes}

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4

    _draw_cover(c, W, H, days, meta, communes_by_code)

    total_h = sum(len(d) for d in days)
    idx = 0
    for day_idx, day in enumerate(days):
        for i_in_day, h in enumerate(day):
            commune_ctx = communes_by_code.get(h["code_insee"], {})
            await _draw_house_page(c, W, H, h, idx, total_h,
                                    day_idx, len(day), commune_ctx)
            idx += 1

    c.save()
    return buf.getvalue()
