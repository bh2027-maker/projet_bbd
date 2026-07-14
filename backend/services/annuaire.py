"""Fetch mairie contact info from the French public directory API."""
import httpx
from typing import Optional


API_URL = ("https://api-lannuaire.service-public.fr/api/explore/v2.1/"
           "catalog/datasets/api-lannuaire-administration/records")


async def fetch_mairie(code_insee: str) -> Optional[dict]:
    """Retourne les coordonnées de la mairie d'une commune, ou None."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            API_URL,
            params={
                "where": f'code_insee_commune="{code_insee}" AND pivot LIKE "%mairie%"',
                "limit": 1,
            },
        )
        if r.status_code != 200:
            return None
        results = r.json().get("results", [])
        if not results:
            return None
        rec = results[0]

    # Parse structured fields (they come as JSON strings)
    import json as _json

    def _first(field, key):
        val = rec.get(field)
        if not val:
            return None
        try:
            arr = _json.loads(val) if isinstance(val, str) else val
            if isinstance(arr, list) and arr:
                return arr[0].get(key)
        except Exception:  # noqa
            return None
        return None

    adresse_full = None
    addr = None
    try:
        addr = _json.loads(rec["adresse"]) if isinstance(rec.get("adresse"), str) else rec.get("adresse")
    except Exception:  # noqa
        pass
    if isinstance(addr, list) and addr:
        a = addr[0]
        adresse_full = ", ".join(
            filter(None, [a.get("numero_voie"), a.get("complement2"),
                          a.get("code_postal"), a.get("nom_commune")])
        )

    tel = _first("telephone", "valeur")
    site = _first("site_internet", "valeur")

    return {
        "nom": rec.get("nom"),
        "adresse": adresse_full,
        "telephone": tel,
        "email": rec.get("adresse_courriel"),
        "site_web": site,
        "url_annuaire": rec.get("url_service_public"),
    }
