"""
Estimation des aides financières pour l'installation d'une pompe à chaleur air-eau
(BAR-TH-171 + Coup de pouce Chauffage + MaPrimeRénov' + TVA 5,5%).

Valeurs indicatives, arrondies aux 500€, basées sur les barèmes 2025 :
- Coup de pouce CEE : 5000€ (ménages modestes+très modestes) / 4000€ (autres)
- MaPrimeRénov' PAC air/eau : Bleu 4000€ / Jaune 3000€ / Violet 2000€
- TVA 5.5% ~ économie 1500€
Le profil dominant est estimé à partir du revenu médian INSEE de la commune.
"""

def estimate_household_profile(revenu_median: float) -> str:
    """Détermine le profil dominant (modeste/intermediaire/superieur)."""
    if revenu_median < 25000:
        return "modeste"
    elif revenu_median < 30000:
        return "intermediaire"
    return "superieur"


def estimate_aides(surface_m2: float, revenu_median: float) -> dict:
    """
    Retourne une fourchette d'aides estimées et un total « best case » et « worst case ».
    """
    profile = estimate_household_profile(revenu_median)

    if profile == "modeste":
        cee = 5000
        mpr_low, mpr_high = 3000, 4000
    elif profile == "intermediaire":
        cee = 4000
        mpr_low, mpr_high = 2000, 3000
    else:
        cee = 4000
        mpr_low, mpr_high = 0, 2000  # supérieurs souvent ineligibles

    tva_savings = 1500  # forfait indicatif TVA 5.5 vs 20 sur ~15k€

    low = cee + mpr_low + tva_savings
    high = cee + mpr_high + tva_savings

    # Bump legèrement pour grandes maisons (>140 m²)
    if surface_m2 > 140:
        bump = 500
        low += bump
        high += bump

    return {
        "profile": profile,
        "coup_de_pouce": cee,
        "mpr_low": mpr_low,
        "mpr_high": mpr_high,
        "tva_savings": tva_savings,
        "aides_low": low,
        "aides_high": high,
        "argument": _format_argument(profile, low, high),
    }


def _format_argument(profile: str, low: int, high: int) -> str:
    label = {"modeste": "modeste/très modeste",
             "intermediaire": "intermédiaire",
             "superieur": "supérieur"}[profile]
    return (f"Profil dominant : {label}. Aides cumulables estimées entre "
            f"{low:,}€ et {high:,}€ (Coup de pouce CEE + MaPrimeRénov' + TVA 5,5%).").replace(",", " ")
