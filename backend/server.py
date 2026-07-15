"""BBD Prospect Intelligence – Backend FastAPI."""
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import io
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List

from bauges_data import load_bauges
from scoring import enrichir_commune
from ai_service import generate_commune_comment
from services.overpass import fetch_buildings
from services.house_scoring import score_maison, STATUSES, STATUS_LABELS
from services.annuaire import fetch_mairie
from services.pdf_tour import build_tour_pdf
from services.pdf_tour_v2 import build_tour_pdf_v2
from services.bdtopo import fetch_bdtopo, match_houses_to_bdtopo, compute_bbox
from services.sirene import fetch_ecosysteme

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="BBD Prospect Intelligence")
api_router = APIRouter(prefix="/api")


@app.get("/")
def read_root():
    return {"status": "ok", "message": "BBD Prospect Intelligence API is running"}


# ---------- Helpers ----------
async def _seed_if_empty():
    """Seed les communes des Bauges (idempotent)."""
    count = await db.communes.count_documents({})
    if count > 0:
        return count
    docs = []
    for c in load_bauges():
        enriched = enrichir_commune(c)
        enriched["seeded_at"] = datetime.now(timezone.utc).isoformat()
        docs.append(enriched)
    await db.communes.insert_many(docs)
    return len(docs)


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ---------- Routes ----------
@api_router.get("/")
async def root():
    return {"service": "BBD Prospect Intelligence", "version": "1.0"}


@api_router.post("/seed")
async def seed():
    """(Ré)initialise la base des communes."""
    await db.communes.delete_many({})
    n = await _seed_if_empty()
    return {"seeded": n}


@api_router.get("/communes")
async def list_communes(sort: str = "score", min_score: float = 0):
    """Liste toutes les communes classées par score BBD décroissant."""
    await _seed_if_empty()
    sort_field = "score_bbd" if sort == "score" else "nom"
    direction = -1 if sort == "score" else 1
    cursor = db.communes.find({"score_bbd": {"$gte": min_score}}).sort(sort_field, direction)
    items = [_clean(doc) async for doc in cursor]
    for i, item in enumerate(items):
        item["rank"] = i + 1
    return {"count": len(items), "items": items}


@api_router.get("/communes/{code_insee}")
async def get_commune(code_insee: str):
    await _seed_if_empty()
    doc = await db.communes.find_one({"code_insee": code_insee})
    if not doc:
        raise HTTPException(404, f"Commune {code_insee} introuvable")
    # compute rank by score
    higher = await db.communes.count_documents({"score_bbd": {"$gt": doc["score_bbd"]}})
    doc = _clean(doc)
    doc["rank"] = higher + 1
    return doc


@api_router.post("/communes/{code_insee}/ai-comment")
async def commune_ai_comment(code_insee: str):
    """Génère (ou renvoie depuis le cache) le commentaire IA."""
    await _seed_if_empty()
    doc = await db.communes.find_one({"code_insee": code_insee})
    if not doc:
        raise HTTPException(404, f"Commune {code_insee} introuvable")

    if doc.get("ai_comment"):
        return {"comment": doc["ai_comment"], "cached": True}

    try:
        comment = await generate_commune_comment(_clean(dict(doc)))
    except Exception as e:
        logging.exception("Erreur IA")
        raise HTTPException(502, f"Erreur génération IA : {e}")

    await db.communes.update_one(
        {"code_insee": code_insee},
        {"$set": {"ai_comment": comment, "ai_comment_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"comment": comment, "cached": False}


@api_router.get("/stats")
async def stats():
    """KPIs du tableau de bord."""
    await _seed_if_empty()
    items = [_clean(d) async for d in db.communes.find({})]
    if not items:
        return {"nb_communes": 0}
    scores = [c["score_bbd"] for c in items]
    total_maisons_detectees = await db.maisons.count_documents({})
    total_prospects_actifs = await db.maisons.count_documents(
        {"status": {"$in": ["a_contacter", "interesse", "rdv", "transmis_gael"]}}
    )
    return {
        "nb_communes": len(items),
        "nb_score_sup_70": sum(1 for s in scores if s >= 70),
        "nb_score_sup_80": sum(1 for s in scores if s >= 80),
        "score_moyen": round(sum(scores) / len(scores), 1),
        "score_max": max(scores),
        "total_maisons_individuelles": sum(c["nb_maisons_individuelles"] for c in items),
        "total_dossiers_estimes": sum(c["dossiers_bar_th_171_estimes"] for c in items),
        "top_commune": max(items, key=lambda c: c["score_bbd"])["nom"],
        "total_maisons_detectees": total_maisons_detectees,
        "total_prospects_actifs": total_prospects_actifs,
    }


# ---------- Module 2 : recensement des maisons ----------
@api_router.post("/communes/{code_insee}/discover")
async def discover_houses(code_insee: str, limit: int = 500):
    """Lance la détection des maisons individuelles via OpenStreetMap/cadastre."""
    await _seed_if_empty()
    commune = await db.communes.find_one({"code_insee": code_insee})
    if not commune:
        raise HTTPException(404, f"Commune {code_insee} introuvable")
    commune = _clean(dict(commune))

    try:
        buildings = await fetch_buildings(code_insee, limit=limit)
    except Exception as e:
        logging.exception("Overpass failed")
        raise HTTPException(502, f"Erreur détection : {e}")

    # Purge existing houses for this commune (re-runs are safe)
    await db.maisons.delete_many({"code_insee": code_insee})

    docs = []
    for b in buildings:
        scoring = score_maison(b, commune)
        doc = {
            **b,
            **scoring,
            "code_insee": code_insee,
            "commune_nom": commune["nom"],
            "status": "a_analyser",
            "notes": "",
            "contact_nom": None,
            "contact_tel": None,
            "contact_email": None,
            "discovered_at": datetime.now(timezone.utc).isoformat(),
            "id": f"{code_insee}-{b['osm_id']}",
        }
        docs.append(doc)

    if docs:
        await db.maisons.insert_many(docs)

    return {
        "code_insee": code_insee,
        "commune": commune["nom"],
        "maisons_detectees": len(docs),
        "top_score": max((d["score"] for d in docs), default=0),
    }


@api_router.get("/communes/{code_insee}/houses")
async def list_houses(code_insee: str, min_score: float = 0, status: str | None = None):
    query: dict = {"code_insee": code_insee, "score": {"$gte": min_score}}
    if status:
        query["status"] = status
    cursor = db.maisons.find(query).sort("score", -1)
    items = []
    async for d in cursor:
        d.pop("_id", None)
        items.append(d)
    for i, item in enumerate(items):
        item["rank"] = i + 1
    return {"count": len(items), "items": items}


@api_router.get("/houses/{house_id}")
async def get_house(house_id: str):
    doc = await db.maisons.find_one({"id": house_id})
    if not doc:
        raise HTTPException(404, "Maison introuvable")
    doc.pop("_id", None)
    return doc


# ---------- Module 7 : pipeline prospect ----------
@api_router.get("/pipeline/statuses")
async def get_statuses():
    return {"statuses": STATUSES, "labels": STATUS_LABELS}


class HouseStatusUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None
    contact_nom: str | None = None
    contact_tel: str | None = None
    contact_email: str | None = None


@api_router.patch("/houses/{house_id}")
async def update_house(house_id: str, payload: HouseStatusUpdate):
    if payload.status is not None and payload.status not in STATUSES:
        raise HTTPException(400, f"Statut inconnu. Valides: {STATUSES}")
    update = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update:
        raise HTTPException(400, "Aucun champ fourni")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.maisons.update_one({"id": house_id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(404, "Maison introuvable")
    doc = await db.maisons.find_one({"id": house_id})
    doc.pop("_id", None)
    return doc


@api_router.get("/pipeline")
async def pipeline_overview():
    """Résumé du pipeline : nb prospects par statut, par commune."""
    counts: dict = {s: 0 for s in STATUSES}
    cursor = db.maisons.aggregate([
        {"$group": {"_id": "$status", "n": {"$sum": 1}}}
    ])
    async for row in cursor:
        counts[row["_id"] or "a_analyser"] = row["n"]

    # Top prospects (score+status)
    hot_cursor = db.maisons.find(
        {"status": {"$in": ["a_contacter", "interesse", "rdv", "transmis_gael"]}}
    ).sort("score", -1).limit(20)
    hot = []
    async for d in hot_cursor:
        d.pop("_id", None)
        hot.append(d)

    return {
        "counts": counts,
        "labels": STATUS_LABELS,
        "hot_prospects": hot,
    }


# ---------- Module 8 : contacts locaux (mairie) ----------
@api_router.get("/communes/{code_insee}/mairie")
async def get_mairie(code_insee: str):
    """Retourne les coordonnées de la mairie (avec cache MongoDB)."""
    commune = await db.communes.find_one({"code_insee": code_insee})
    if not commune:
        raise HTTPException(404, "Commune introuvable")
    if commune.get("mairie"):
        return commune["mairie"]
    try:
        m = await fetch_mairie(code_insee)
    except Exception as e:  # noqa
        raise HTTPException(502, f"API annuaire indisponible : {e}")
    if m:
        await db.communes.update_one({"code_insee": code_insee}, {"$set": {"mairie": m}})
    return m or {}


# ---------- Discover all (Module 2 en masse) ----------
@api_router.post("/discovery/start")
async def trigger_discover_all():
    """Lance la détection en arrière-plan pour toutes les communes sans maisons."""
    if _discovery_state["running"]:
        return {"status": "already_running", "progress": _discovery_state}
    asyncio.create_task(_run_discover_all())
    await asyncio.sleep(0.2)
    return {"status": "started", "progress": _discovery_state}


@api_router.get("/discovery/status")
async def discovery_status():
    return _discovery_state


# ---------- Feuille de route PDF (Module 7 bis) ----------
class TourRequest(BaseModel):
    house_ids: List[str]
    date: str | None = None
    label: str | None = None
    max_per_day: int = 8
    max_km_per_day: float = 40.0
    include_photos: bool = True


@api_router.post("/tour/pdf")
async def tour_pdf(payload: TourRequest):
    """Génère un PDF de feuille de route pour Gaël à partir d'une liste de maisons."""
    if not payload.house_ids:
        raise HTTPException(400, "Aucune maison sélectionnée")
    if len(payload.house_ids) > 50:
        raise HTTPException(400, "Maximum 50 maisons par feuille de route")

    houses = []
    async for d in db.maisons.find({"id": {"$in": payload.house_ids}}):
        d.pop("_id", None)
        houses.append(d)
    if not houses:
        raise HTTPException(404, "Aucune maison trouvée pour ces IDs")

    # Load communes for revenu_median context
    codes = list({h["code_insee"] for h in houses})
    communes = []
    async for c in db.communes.find({"code_insee": {"$in": codes}}):
        c.pop("_id", None)
        communes.append(c)

    pdf_bytes = await build_tour_pdf_v2(
        houses, communes,
        {"date": payload.date or datetime.now().strftime("%d/%m/%Y"),
         "label": payload.label},
        max_per_day=payload.max_per_day,
        max_km_per_day=payload.max_km_per_day,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="feuille-de-route-BBD-{datetime.now().strftime("%Y%m%d")}.pdf"'
        },
    )


# ---------- Module 9 : écosystème local ----------
@api_router.get("/communes/{code_insee}/ecosysteme")
async def get_ecosysteme(code_insee: str, refresh: bool = False):
    """Retourne les acteurs locaux (SIRENE), avec cache MongoDB."""
    commune = await db.communes.find_one({"code_insee": code_insee})
    if not commune:
        raise HTTPException(404, "Commune introuvable")
    if not refresh and commune.get("ecosysteme"):
        return {"cached": True, **commune["ecosysteme"]}
    try:
        eco = await fetch_ecosysteme(code_insee)
    except Exception as e:  # noqa
        raise HTTPException(502, f"SIRENE indisponible : {e}")
    await db.communes.update_one({"code_insee": code_insee}, {"$set": {"ecosysteme": eco}})
    return {"cached": False, **eco}


# ---------- Enrichissement BD TOPO IGN (dates réelles) ----------
async def _enrich_commune_bdtopo(commune: dict) -> dict:
    houses = [h async for h in db.maisons.find({"code_insee": commune["code_insee"]})]
    if not houses:
        return {"code_insee": commune["code_insee"], "nom": commune["nom"],
                "matched": 0, "enriched_with_date": 0}
    bbox = compute_bbox(commune["lat"], commune["lon"], radius_km=4.0)
    bdtopo = await fetch_bdtopo(bbox, limit=5000)
    matches = match_houses_to_bdtopo(houses, bdtopo, tolerance_m=15.0)
    matched = 0
    with_date = 0
    for h, b in matches:
        if not b:
            continue
        matched += 1
        updates = {"bdtopo_matched": True}
        if b.get("year"):
            updates["start_date"] = str(b["year"])
            updates["bdtopo_year"] = b["year"]
            with_date += 1
        if b.get("logements") is not None:
            updates["bdtopo_logements"] = b["logements"]
        if b.get("etages") is not None:
            updates["bdtopo_etages"] = b["etages"]
            if not h.get("levels"):
                updates["levels"] = b["etages"]
        if b.get("hauteur_m") is not None:
            updates["bdtopo_hauteur_m"] = b["hauteur_m"]
        if b.get("usage"):
            updates["bdtopo_usage"] = b["usage"]

        # Re-compute score with the new data
        merged = {**h, **updates}
        new_score = score_maison(merged, commune)
        updates.update(new_score)

        await db.maisons.update_one({"id": h["id"]}, {"$set": updates})
    return {
        "code_insee": commune["code_insee"], "nom": commune["nom"],
        "houses": len(houses), "matched": matched, "enriched_with_date": with_date,
    }


# State for enrichment background job
_enrichment_state = {
    "running": False, "total": 0, "done": 0, "current": None,
    "results": [], "started_at": None, "finished_at": None,
}


async def _run_enrich_all():
    _enrichment_state["running"] = True
    _enrichment_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _enrichment_state["results"] = []
    todo = []
    async for c in db.communes.find({}):
        cnt = await db.maisons.count_documents({"code_insee": c["code_insee"]})
        if cnt > 0:
            todo.append(_clean(dict(c)))
    _enrichment_state["total"] = len(todo)
    _enrichment_state["done"] = 0
    for c in todo:
        _enrichment_state["current"] = c["nom"]
        try:
            res = await _enrich_commune_bdtopo(c)
            _enrichment_state["results"].append({**res, "ok": True})
        except Exception as e:  # noqa
            _enrichment_state["results"].append({
                "code_insee": c["code_insee"], "nom": c["nom"],
                "ok": False, "error": str(e)[:150],
            })
        _enrichment_state["done"] += 1
        await asyncio.sleep(0.3)
    _enrichment_state["current"] = None
    _enrichment_state["running"] = False
    _enrichment_state["finished_at"] = datetime.now(timezone.utc).isoformat()


@api_router.post("/enrichment/start")
async def trigger_enrich_all():
    if _enrichment_state["running"]:
        return {"status": "already_running", "progress": _enrichment_state}
    asyncio.create_task(_run_enrich_all())
    await asyncio.sleep(0.2)
    return {"status": "started", "progress": _enrichment_state}


@api_router.get("/enrichment/status")
async def enrich_status():
    return _enrichment_state


app.include_router(api_router)
_discovery_state = {
    "running": False,
    "total": 0,
    "done": 0,
    "current": None,
    "results": [],
    "started_at": None,
    "finished_at": None,
}


async def _run_discover_all():
    _discovery_state["running"] = True
    _discovery_state["started_at"] = datetime.now(timezone.utc).isoformat()
    _discovery_state["results"] = []
    to_do = [d async for d in db.communes.find({}, {"code_insee": 1, "nom": 1})]
    # Only communes without maisons yet
    todo_filtered = []
    for c in to_do:
        cnt = await db.maisons.count_documents({"code_insee": c["code_insee"]})
        if cnt == 0:
            todo_filtered.append(c)
    _discovery_state["total"] = len(todo_filtered)
    _discovery_state["done"] = 0

    for c in todo_filtered:
        _discovery_state["current"] = c["nom"]
        try:
            commune = await db.communes.find_one({"code_insee": c["code_insee"]})
            commune = _clean(dict(commune))
            buildings = await fetch_buildings(c["code_insee"], limit=500)
            docs = []
            for b in buildings:
                scoring_res = score_maison(b, commune)
                doc = {
                    **b, **scoring_res,
                    "code_insee": c["code_insee"],
                    "commune_nom": c["nom"],
                    "status": "a_analyser",
                    "notes": "",
                    "contact_nom": None,
                    "contact_tel": None,
                    "contact_email": None,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                    "id": f"{c['code_insee']}-{b['osm_id']}",
                }
                docs.append(doc)
            if docs:
                await db.maisons.insert_many(docs)
            _discovery_state["results"].append({
                "code_insee": c["code_insee"], "nom": c["nom"],
                "maisons": len(docs), "ok": True,
            })
        except Exception as e:  # noqa
            _discovery_state["results"].append({
                "code_insee": c["code_insee"], "nom": c["nom"],
                "maisons": 0, "ok": False, "error": str(e)[:150],
            })
        _discovery_state["done"] += 1
        await asyncio.sleep(0.5)  # be nice to Overpass

    _discovery_state["current"] = None
    _discovery_state["running"] = False
    _discovery_state["finished_at"] = datetime.now(timezone.utc).isoformat()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
