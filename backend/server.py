"""BBD Prospect Intelligence – Backend FastAPI."""
from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from datetime import datetime, timezone

from bauges_data import BAUGES_COMMUNES
from scoring import enrichir_commune
from ai_service import generate_commune_comment

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
    return _clean(doc)


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
    return {
        "nb_communes": len(items),
        "nb_score_sup_70": sum(1 for s in scores if s >= 70),
        "nb_score_sup_80": sum(1 for s in scores if s >= 80),
        "score_moyen": round(sum(scores) / len(scores), 1),
        "score_max": max(scores),
        "total_maisons_individuelles": sum(c["nb_maisons_individuelles"] for c in items),
        "total_dossiers_estimes": sum(c["dossiers_bar_th_171_estimes"] for c in items),
        "top_commune": max(items, key=lambda c: c["score_bbd"])["nom"],
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
