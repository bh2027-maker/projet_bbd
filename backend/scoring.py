"""
Moteur de scoring BBD.
Calcule un score sur 100 par commune, exprimant le potentiel de prospection
pour la vente de pompes à chaleur (BAR-TH-171).

Critères (Modules 3, 4, 5 du cahier des charges) :
- Part de logements individuels (plus il y en a, mieux c'est)
- Ancienneté du parc (>2000 = fioul/gaz probable, remplacement PAC pertinent)
- Nombre absolu de maisons individuelles (volume de dossiers potentiels)
- Revenu médian (capacité à financer un reste à charge)
- Zone climatique H1 (toutes les Bauges = 100%)
- Altitude (les zones froides = fort besoin chauffage = ROI PAC élevé)
"""
from typing import Dict, Any


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _normalize(value: float, lo: float, hi: float) -> float:
    """Retourne un score 0-100 par interpolation linéaire entre lo et hi."""
    if hi == lo:
        return 50.0
    return _clamp((value - lo) / (hi - lo) * 100)


def compute_score(commune: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retourne le score BBD sur 100 et le détail par critère.
    """
    pop = commune["population"]
    logements = commune["nb_logements"]
    maisons = commune["nb_maisons_individuelles"]
    part_anciens = commune["part_logements_avant_2000_pct"]
    revenu = commune["revenu_median"]
    altitude = commune["altitude_m"]

    # Sous-scores 0-100
    # 1. Part maisons individuelles (plus la commune est pavillonnaire, mieux c'est)
    part_maisons = (maisons / logements * 100) if logements > 0 else 0
    score_maisons_indiv = _normalize(part_maisons, 40, 95)

    # 2. Ancienneté du parc (>60% avant 2000 = très bon terrain)
    score_anciennete = _normalize(part_anciens, 40, 90)

    # 3. Volume : nb absolu de maisons (log-ish via bornes)
    score_volume = _normalize(maisons, 80, 600)

    # 4. Revenu médian : sweet spot 25-35k€ (assez pour financer, pas trop riche
    #    pour ignorer les aides MPR)
    if revenu < 22000:
        score_revenu = _normalize(revenu, 18000, 22000) * 0.6  # trop précaire
    elif revenu <= 32000:
        score_revenu = 85 + _normalize(revenu, 22000, 32000) * 0.15
    else:
        score_revenu = _clamp(100 - (revenu - 32000) / 200)

    # 5. Altitude / zone climatique H1 (les Bauges sont toutes en H1)
    #    Plus c'est haut, plus les besoins chauffage sont élevés.
    score_climat = _normalize(altitude, 400, 1100)

    # Pondération finale
    weights = {
        "maisons_indiv": 0.20,
        "anciennete": 0.30,   # critère prioritaire du cahier
        "volume": 0.20,
        "revenu": 0.20,
        "climat": 0.10,
    }
    total = (
        score_maisons_indiv * weights["maisons_indiv"] +
        score_anciennete * weights["anciennete"] +
        score_volume * weights["volume"] +
        score_revenu * weights["revenu"] +
        score_climat * weights["climat"]
    )

    # Estimation nb dossiers éligibles BAR-TH-171 : maisons anciennes × part
    # probable chauffage fossile (estimé ~55% en zone rurale H1 avant 2000)
    dossiers_estimes = int(maisons * (part_anciens / 100) * 0.55)

    return {
        "score_bbd": round(total, 1),
        "breakdown": {
            "maisons_individuelles": round(score_maisons_indiv, 1),
            "anciennete_parc": round(score_anciennete, 1),
            "volume_maisons": round(score_volume, 1),
            "revenu_median": round(score_revenu, 1),
            "climat_altitude": round(score_climat, 1),
        },
        "part_maisons_pct": round(part_maisons, 1),
        "dossiers_bar_th_171_estimes": dossiers_estimes,
    }


def enrichir_commune(commune: Dict[str, Any]) -> Dict[str, Any]:
    """Retourne la commune enrichie avec son score et son classement."""
    scoring = compute_score(commune)
    return {**commune, **scoring, "zone_climatique": "H1"}
