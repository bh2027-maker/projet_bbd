"""Phase 2 backend tests – Module 2 (houses discovery) + Module 7 (pipeline)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bbd-detection.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SEEDED_COMMUNE = "74099"  # Gruffy - already seeded per agent notes


@pytest.fixture(scope="session")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Module 7 : /pipeline/statuses ----------
def test_pipeline_statuses(sess):
    r = sess.get(f"{API}/pipeline/statuses", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert set(d["statuses"]) == {"a_analyser", "a_contacter", "interesse", "rdv", "transmis_gael", "vendu", "perdu"}
    assert d["labels"]["a_contacter"] == "À contacter"
    assert d["labels"]["transmis_gael"] == "Transmis à Gaël"
    assert d["labels"]["rdv"] == "Rendez-vous"


# ---------- Module 2 : GET /communes/{code}/houses ----------
def test_list_houses_seeded_commune(sess):
    r = sess.get(f"{API}/communes/{SEEDED_COMMUNE}/houses", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["count"] >= 100, f"expected ≥100 houses, got {d['count']}"
    items = d["items"]
    top = items[0]
    # required fields
    for k in ["score", "rank", "breakdown", "type_label", "age_label",
              "surface_habitable_estimee_m2", "footprint", "status", "id", "commune_nom", "osm_id"]:
        assert k in top, f"missing field {k} in house"
    assert isinstance(top["footprint"], list) and len(top["footprint"]) >= 3
    # footprint entries are [lat, lon]
    assert isinstance(top["footprint"][0], list) and len(top["footprint"][0]) == 2
    # scoring
    assert top["score"] > 60, f"top score should be >60, got {top['score']}"
    # sorted desc
    scores = [h["score"] for h in items]
    assert scores == sorted(scores, reverse=True)
    # default status
    assert top["status"] in ("a_analyser", "a_contacter", "interesse", "rdv", "transmis_gael", "vendu", "perdu")


def test_list_houses_min_score_filter(sess):
    r = sess.get(f"{API}/communes/{SEEDED_COMMUNE}/houses", params={"min_score": 70}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for h in d["items"]:
        assert h["score"] >= 70


# ---------- GET /houses/{id} ----------
def test_get_single_house(sess):
    r = sess.get(f"{API}/communes/{SEEDED_COMMUNE}/houses", timeout=30)
    hid = r.json()["items"][0]["id"]
    r2 = sess.get(f"{API}/houses/{hid}", timeout=30)
    assert r2.status_code == 200
    assert r2.json()["id"] == hid


def test_get_house_unknown(sess):
    r = sess.get(f"{API}/houses/NOT-EXISTS-123", timeout=30)
    assert r.status_code == 404


# ---------- PATCH /houses/{id} ----------
def test_patch_house_full(sess):
    r = sess.get(f"{API}/communes/{SEEDED_COMMUNE}/houses", timeout=30)
    # pick a house that is NOT the pre-set 74099-157666273 to avoid disturbing seed data
    items = r.json()["items"]
    target = next(h for h in items if h["id"] != "74099-157666273" and h["status"] == "a_analyser")
    hid = target["id"]
    original_status = target["status"]

    patch = {
        "status": "interesse",
        "notes": "TEST_pytest note",
        "contact_nom": "TEST_M. Dupont",
        "contact_tel": "0601020304",
        "contact_email": "test@example.com",
    }
    r2 = sess.patch(f"{API}/houses/{hid}", json=patch, timeout=30)
    assert r2.status_code == 200, r2.text
    upd = r2.json()
    assert upd["status"] == "interesse"
    assert upd["contact_nom"] == "TEST_M. Dupont"
    assert upd["contact_tel"] == "0601020304"
    assert upd["notes"] == "TEST_pytest note"

    # GET verify persistence
    r3 = sess.get(f"{API}/houses/{hid}", timeout=30)
    assert r3.json()["status"] == "interesse"
    assert r3.json()["contact_email"] == "test@example.com"

    # cleanup - restore
    sess.patch(f"{API}/houses/{hid}", json={"status": original_status, "notes": "", "contact_nom": "", "contact_tel": "", "contact_email": ""}, timeout=30)


def test_patch_house_invalid_status(sess):
    r = sess.get(f"{API}/communes/{SEEDED_COMMUNE}/houses", timeout=30)
    hid = r.json()["items"][0]["id"]
    r2 = sess.patch(f"{API}/houses/{hid}", json={"status": "bogus_status"}, timeout=30)
    assert r2.status_code == 400


def test_patch_house_unknown(sess):
    r = sess.patch(f"{API}/houses/UNKNOWN-XYZ", json={"status": "interesse"}, timeout=30)
    assert r.status_code == 404


# ---------- Module 7 : /pipeline ----------
def test_pipeline_overview(sess):
    r = sess.get(f"{API}/pipeline", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "counts" in d and "labels" in d and "hot_prospects" in d
    for k in ["a_analyser", "a_contacter", "interesse", "rdv", "transmis_gael", "vendu", "perdu"]:
        assert k in d["counts"]
    # hot prospects only active statuses
    for h in d["hot_prospects"]:
        assert h["status"] in ("a_contacter", "interesse", "rdv", "transmis_gael")
    # sorted score desc
    scores = [h["score"] for h in d["hot_prospects"]]
    assert scores == sorted(scores, reverse=True)


# ---------- /stats new fields ----------
def test_stats_new_fields(sess):
    r = sess.get(f"{API}/stats", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "total_maisons_detectees" in d
    assert "total_prospects_actifs" in d
    assert d["total_maisons_detectees"] >= 1000  # 3 communes discovered ~1273
    assert isinstance(d["total_prospects_actifs"], int)


# ---------- Idempotent discover (optional / slow) ----------
@pytest.mark.slow
def test_discover_idempotent_small(sess):
    """Run discover twice on Doucy-en-Bauges (73101). Marked slow – runs only with --run-slow."""
    r = sess.post(f"{API}/communes/73101/discover", timeout=120)
    if r.status_code == 502:
        pytest.skip("Overpass external dep down (502)")
    assert r.status_code == 200
    d1 = r.json()
    assert d1["maisons_detectees"] >= 1
    # second call
    r2 = sess.post(f"{API}/communes/73101/discover", timeout=120)
    if r2.status_code == 502:
        pytest.skip("Overpass external dep down (502) on 2nd call")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["maisons_detectees"] == d1["maisons_detectees"]
