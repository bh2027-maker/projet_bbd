"""
Scoring individuel par maison (Modules 3 & 4 du cahier des charges).
Retourne un score /100 par maison basé sur ses caractéristiques + contexte commune.
"""
from typing import Dict, Any


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def _norm(v, lo, hi):
    if hi == lo:
        return 50.0
    return _clamp((v - lo) / (hi - lo) * 100)


# Statuts pipeline (Module 7)
STATUSES = [
    "a_analyser",     # défaut
    "a_contacter",
    "interesse",
    "rdv",
    "transmis_gael",
    "vendu",
    "perdu",
]

STATUS_LABELS = {
    "a_analyser": "À analyser",
    "a_contacter": "À contacter",
    "interesse": "Intéressé",
    "rdv": "Rendez-vous",
    "transmis_gael": "Transmis à Gaël",
    "vendu": "Vendu",
    "perdu": "Perdu",
}


def score_maison(maison: Dict[str, Any], commune: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcule le score BBD (0-100) pour UNE maison individuelle.

    Critères prioritaires (cahier des charges) :
    - Maison individuelle (type building)
    - Surface > 90 m² (habitable estimée)
    - Construction avant 2000 (heuristique : tag OSM sinon part ancienne commune)
    - Zone climatique H1 (Bauges = 100%)
    - Forte probabilité chauffage fossile (fioul/gaz/charbon)
    - Accessibilité correcte
    """
    surface = maison.get("surface_habitable_estimee_m2", 0)
    building_type = maison.get("building_type", "yes")
    start_date_raw = maison.get("start_date")

    # 1. Type maison individuelle
    if building_type in ("house", "detached"):
        score_type = 100
        type_label = "Maison certaine"
    elif building_type == "residential":
        score_type = 75
        type_label = "Résidentiel"
    else:  # 'yes' (cadastre import) — incertain mais probablement maison en zone rurale
        score_type = 60
        type_label = "Probable (cadastre)"

    # 2. Surface habitable estimée
    #    <60 = trop petit (secondaire ?), 60-90 = correct, 90-150 = sweet spot,
    #    >150 = grande maison (potentiel élevé)
    if surface < 60:
        score_surface = _norm(surface, 30, 60) * 0.5
    elif surface < 90:
        score_surface = 55 + (surface - 60) * (25 / 30)  # 55->80
    elif surface <= 180:
        score_surface = 80 + (surface - 90) * (20 / 90)  # 80->100
    else:
        score_surface = _clamp(100 - (surface - 180) / 10)

    # 3. Ancienneté
    year = None
    if start_date_raw:
        # OSM start_date peut être "1850", "1850-01-01", "1800..1900" etc.
        digits = "".join(c for c in str(start_date_raw)[:4] if c.isdigit())
        if len(digits) == 4:
            year = int(digits)

    if year:
        if year < 1948:
            score_age = 95  # ancien, gros potentiel fioul/bois
        elif year < 1975:
            score_age = 90
        elif year < 2000:
            score_age = 80
        elif year < 2013:
            score_age = 55
        else:
            score_age = 25  # récent, souvent déjà PAC
        age_label = f"Construite ~{year}"
    else:
        # Pas d'info : on hérite de la moyenne communale
        part_anciens = commune.get("part_logements_avant_2000_pct", 60)
        score_age = _norm(part_anciens, 40, 90) * 0.9 + 5
        age_label = f"Estimée via commune ({part_anciens}% avant 2000)"

    # 4. Probabilité chauffage fossile (fonction de l'âge)
    if year and year < 1975:
        proba_fossile = 82
    elif year and year < 2000:
        proba_fossile = 65
    elif year and year >= 2013:
        proba_fossile = 25
    else:
        # Hérite de la commune
        proba_fossile = min(80, commune.get("part_logements_avant_2000_pct", 60) + 15)

    score_chauffage = proba_fossile

    # 5. Zone climatique (Bauges = H1 : 100)
    score_climat = 100

    # 6. Accessibilité (heuristique : maison avec adresse OSM = mieux)
    has_address = bool(maison.get("addr_street") or maison.get("addr_housenumber"))
    score_access = 85 if has_address else 70

    # Pondération finale
    total = (
        score_type * 0.20 +
        score_age * 0.30 +
        score_surface * 0.20 +
        score_chauffage * 0.15 +
        score_climat * 0.05 +
        score_access * 0.10
    )

    return {
        "score": round(total, 1),
        "breakdown": {
            "type_maison": round(score_type, 1),
            "anciennete": round(score_age, 1),
            "surface": round(score_surface, 1),
            "chauffage_fossile": round(score_chauffage, 1),
            "climat_h1": round(score_climat, 1),
            "accessibilite": round(score_access, 1),
        },
        "type_label": type_label,
        "age_label": age_label,
        "proba_chauffage_fossile_pct": proba_fossile,
        "has_address": has_address,
    }
