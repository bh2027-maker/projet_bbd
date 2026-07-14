"""
Module 9 : Écosystème local d'une commune via l'API SIRENE
(recherche-entreprises.api.gouv.fr).
"""
import asyncio
import httpx
from typing import Dict, List, Any

API_URL = "https://recherche-entreprises.api.gouv.fr/search"


# Groupes NAF pertinents pour la prospection terrain
CATEGORIES = {
    "artisans_btp": {
        "label": "Artisans BTP",
        "naf": ["43.22A", "43.21A", "43.99C", "43.31Z", "43.32A", "43.33Z",
                "43.34Z", "43.39Z", "43.91A", "41.20A", "41.20B"],
    },
    "commerces_proximite": {
        "label": "Commerces de proximité",
        "naf": ["47.11B", "47.11D", "47.11F", "47.22Z", "47.24Z",
                "47.26Z", "47.73Z", "47.29Z", "10.71C", "10.13B"],
    },
    "restauration": {
        "label": "Bars & restaurants",
        "naf": ["56.30Z", "56.10A", "56.10B", "56.10C", "56.29A", "56.29B"],
    },
    "auto_moto": {
        "label": "Garages & auto",
        "naf": ["45.20A", "45.20B", "45.32Z", "47.30Z"],
    },
    "bricolage_agri": {
        "label": "Bricolage & agricole",
        "naf": ["47.52A", "47.52B", "46.21Z", "01.61Z", "10.51D"],
    },
    "sante": {
        "label": "Santé",
        "naf": ["86.21Z", "86.22A", "86.22B", "86.22C", "86.23Z", "47.73Z", "47.74Z"],
    },
    "associations_sport_culture": {
        "label": "Associations & clubs",
        "naf": ["94.99Z", "93.12Z", "93.13Z", "93.19Z", "93.29Z", "94.11Z", "94.20Z"],
    },
}


async def _fetch_naf(client: httpx.AsyncClient, code_insee: str, naf: str) -> List[dict]:
    r = await client.get(API_URL, params={
        "code_commune": code_insee,
        "activite_principale": naf,
        "per_page": 25,
        "etat_administratif": "A",  # actives only
    })
    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def _clean_entity(e: dict) -> dict:
    siege = e.get("siege") or {}
    return {
        "nom": e.get("nom_complet") or e.get("nom_raison_sociale"),
        "siret": siege.get("siret"),
        "naf": e.get("activite_principale"),
        "activite_libelle": e.get("libelle_activite_principale"),
        "adresse": siege.get("adresse") or siege.get("libelle_voie"),
        "code_postal": siege.get("code_postal"),
        "commune": siege.get("libelle_commune"),
        "categorie_juridique": e.get("nature_juridique"),
        "dirigeant": (e.get("dirigeants") or [{}])[0].get("nom_complet") if e.get("dirigeants") else None,
        "tranche_effectif": siege.get("tranche_effectif_salarie"),
    }


async def fetch_ecosysteme(code_insee: str) -> Dict[str, Any]:
    """Retourne les entités locales groupées par catégorie."""
    result: Dict[str, Any] = {"categories": {}, "total": 0}

    async with httpx.AsyncClient(timeout=15) as client:
        for cat_key, cat in CATEGORIES.items():
            # Fetch each NAF code in parallel for this category
            tasks = [_fetch_naf(client, code_insee, naf) for naf in cat["naf"]]
            batches = await asyncio.gather(*tasks, return_exceptions=True)
            entities: List[dict] = []
            seen = set()
            for b in batches:
                if isinstance(b, Exception):
                    continue
                for e in b:
                    siret = (e.get("siege") or {}).get("siret")
                    if siret and siret not in seen:
                        seen.add(siret)
                        entities.append(_clean_entity(e))
            # Sort by name and keep top 25 per category
            entities.sort(key=lambda x: (x.get("nom") or "").lower())
            result["categories"][cat_key] = {
                "label": cat["label"],
                "count": len(entities),
                "entities": entities[:25],
            }
            result["total"] += len(entities)
    return result
