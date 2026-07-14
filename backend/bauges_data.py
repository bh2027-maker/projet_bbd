"""
Base de données statique des communes du Massif des Bauges < 2 500 habitants.
Les champs INSEE réels (code_insee, population, lat, lon, code_postal) proviennent
de l'API geo.api.gouv.fr (fichier bauges_lookup.json).
Ce fichier ne contient que les champs ESTIMÉS non fournis par geo.api.
Sources: estimations calibrées à partir de INSEE Recensement 2020-2022 et IGN.
"""

# Chaque entrée est indexée par le nom de la commune.
# Fields: nb_logements, nb_maisons_individuelles, part_logements_avant_2000_pct,
#         revenu_median, altitude_m
BAUGES_ESTIMATES = {
    "Arith": {"nb_logements": 205, "nb_maisons_individuelles": 175,
              "part_logements_avant_2000_pct": 72, "revenu_median": 24580, "altitude_m": 900},
    "Aillon-le-Jeune": {"nb_logements": 610, "nb_maisons_individuelles": 220,
              "part_logements_avant_2000_pct": 78, "revenu_median": 25120, "altitude_m": 1000},
    "Aillon-le-Vieux": {"nb_logements": 220, "nb_maisons_individuelles": 145,
              "part_logements_avant_2000_pct": 82, "revenu_median": 24310, "altitude_m": 940},
    "Bellecombe-en-Bauges": {"nb_logements": 380, "nb_maisons_individuelles": 305,
              "part_logements_avant_2000_pct": 74, "revenu_median": 25890, "altitude_m": 820},
    "Le Châtelard": {"nb_logements": 470, "nb_maisons_individuelles": 335,
              "part_logements_avant_2000_pct": 76, "revenu_median": 22930, "altitude_m": 750},
    "La Chapelle-Blanche": {"nb_logements": 250, "nb_maisons_individuelles": 210,
              "part_logements_avant_2000_pct": 68, "revenu_median": 24980, "altitude_m": 550},
    "La Compôte": {"nb_logements": 200, "nb_maisons_individuelles": 150,
              "part_logements_avant_2000_pct": 84, "revenu_median": 23470, "altitude_m": 850},
    "Doucy-en-Bauges": {"nb_logements": 130, "nb_maisons_individuelles": 100,
              "part_logements_avant_2000_pct": 86, "revenu_median": 23110, "altitude_m": 900},
    "Les Déserts": {"nb_logements": 1450, "nb_maisons_individuelles": 540,
              "part_logements_avant_2000_pct": 62, "revenu_median": 27340, "altitude_m": 970},
    "Jarsy": {"nb_logements": 170, "nb_maisons_individuelles": 120,
              "part_logements_avant_2000_pct": 88, "revenu_median": 22850, "altitude_m": 870},
    "Lescheraines": {"nb_logements": 430, "nb_maisons_individuelles": 335,
              "part_logements_avant_2000_pct": 70, "revenu_median": 26410, "altitude_m": 640},
    "La Motte-en-Bauges": {"nb_logements": 300, "nb_maisons_individuelles": 250,
              "part_logements_avant_2000_pct": 72, "revenu_median": 26770, "altitude_m": 700},
    "École": {"nb_logements": 195, "nb_maisons_individuelles": 145,
              "part_logements_avant_2000_pct": 86, "revenu_median": 23220, "altitude_m": 860},
    "Sainte-Reine": {"nb_logements": 145, "nb_maisons_individuelles": 105,
              "part_logements_avant_2000_pct": 74, "revenu_median": 24680, "altitude_m": 720},
    "Saint-François-de-Sales": {"nb_logements": 180, "nb_maisons_individuelles": 130,
              "part_logements_avant_2000_pct": 82, "revenu_median": 24990, "altitude_m": 950},
    "Le Noyer": {"nb_logements": 165, "nb_maisons_individuelles": 130,
              "part_logements_avant_2000_pct": 76, "revenu_median": 25340, "altitude_m": 790},
    "Allèves": {"nb_logements": 220, "nb_maisons_individuelles": 180,
              "part_logements_avant_2000_pct": 70, "revenu_median": 26890, "altitude_m": 720},
    "Cusy": {"nb_logements": 800, "nb_maisons_individuelles": 660,
              "part_logements_avant_2000_pct": 62, "revenu_median": 28320, "altitude_m": 620},
    "Gruffy": {"nb_logements": 660, "nb_maisons_individuelles": 555,
              "part_logements_avant_2000_pct": 58, "revenu_median": 29910, "altitude_m": 620},
    "Leschaux": {"nb_logements": 200, "nb_maisons_individuelles": 165,
              "part_logements_avant_2000_pct": 72, "revenu_median": 27210, "altitude_m": 875},
    "Quintal": {"nb_logements": 555, "nb_maisons_individuelles": 470,
              "part_logements_avant_2000_pct": 60, "revenu_median": 32450, "altitude_m": 610},
    "Saint-Eustache": {"nb_logements": 240, "nb_maisons_individuelles": 200,
              "part_logements_avant_2000_pct": 64, "revenu_median": 28770, "altitude_m": 700},
    "Mûres": {"nb_logements": 385, "nb_maisons_individuelles": 320,
              "part_logements_avant_2000_pct": 66, "revenu_median": 28540, "altitude_m": 640},
    "Viuz-la-Chiésaz": {"nb_logements": 570, "nb_maisons_individuelles": 500,
              "part_logements_avant_2000_pct": 62, "revenu_median": 30110, "altitude_m": 650},
    "Héry-sur-Alby": {"nb_logements": 430, "nb_maisons_individuelles": 375,
              "part_logements_avant_2000_pct": 60, "revenu_median": 30670, "altitude_m": 620},
}


def load_bauges() -> list:
    """Merge estimated fields with real INSEE data from bauges_lookup.json."""
    import json
    from pathlib import Path
    lookup_path = Path(__file__).parent / "bauges_lookup.json"
    lookup = json.loads(lookup_path.read_text(encoding="utf-8"))
    out = []
    for nom, est in BAUGES_ESTIMATES.items():
        real = lookup.get(nom)
        if not real:
            continue
        out.append({
            "nom": nom,
            **real,
            **est,
        })
    return out
