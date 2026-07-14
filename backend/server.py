"""BBD Prospect Intelligence – Backend FastAPI."""
from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
from pydantic import BaseModel

from bauges_data import BAUGES_COMMUNES
from scoring import enrichir_commune
from ai_service import generate_commune_comment
from services.overpass import fetch_buildings
from services.house_scoring import score_maison, STATUSES, STATUS_LABELS

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="BBD Prospect Intelligence")
api_router = APIRouter(prefix="/api")


# ---------- Helpers ----------
async def _seed_if_empty():
    """Seed les communes des Bauges (idempotent)."""
    count = await db.communes.count_documents({})
    if count > 0:
        return count
    docs = []
    for c in BAUGES_COMMUNES:
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


app.include_router(api_router)

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
