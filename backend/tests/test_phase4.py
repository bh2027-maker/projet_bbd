"""Phase 4 tests: BD TOPO enrichment + SIRENE ecosysteme + Pipeline CSV/filters."""
import os
import time
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- Module 9 : Ecosysteme SIRENE ----------
class TestEcosysteme:
    def test_gruffy_ecosysteme_shape(self, s):
        r = s.get(f"{BASE}/api/communes/74138/ecosysteme", timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "total" in d and "categories" in d
        expected = {"artisans_btp", "commerces_proximite", "restauration",
                    "auto_moto", "bricolage_agri", "sante", "associations_sport_culture"}
        assert expected.issubset(d["categories"].keys())
        # total > 0 for Gruffy (already cached per handoff)
        assert d["total"] > 0
        for k, cat in d["categories"].items():
            assert "label" in cat and "count" in cat and "entities" in cat
            for e in cat["entities"]:
                assert "nom" in e and "siret" in e
                assert "naf" in e and "activite_libelle" in e

    def test_gruffy_ecosysteme_cached_second_call(self, s):
        # First ensure it is set (safe – idempotent)
        s.get(f"{BASE}/api/communes/74138/ecosysteme", timeout=60)
        r = s.get(f"{BASE}/api/communes/74138/ecosysteme", timeout=60)
        assert r.status_code == 200
        assert r.json().get("cached") is True

    def test_ecosysteme_unknown_commune_404(self, s):
        r = s.get(f"{BASE}/api/communes/00000/ecosysteme", timeout=30)
        assert r.status_code == 404


# ---------- Enrichment endpoints ----------
class TestEnrichment:
    def test_enrichment_status_shape(self, s):
        r = s.get(f"{BASE}/api/enrichment/status", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("running", "total", "done", "current", "results",
                  "started_at", "finished_at"):
            assert k in d
        assert isinstance(d["results"], list)

    def test_enrichment_start_returns_started_or_already(self, s):
        r = s.post(f"{BASE}/api/enrichment/start", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] in ("started", "already_running")
        assert "progress" in d

    def test_enrichment_start_second_call_already_running(self, s):
        # If not currently running, first call above may have started it.
        # Wait a bit then call again.
        time.sleep(1)
        r = s.post(f"{BASE}/api/enrichment/start", timeout=15)
        assert r.status_code == 200
        # If the job already finished quickly, we still expect valid response.
        assert r.json()["status"] in ("started", "already_running")


# ---------- Houses enriched with BD TOPO ----------
class TestHousesEnriched:
    def test_some_houses_have_bdtopo_match(self, s):
        # Ask several known communes for houses; verify at least one enriched.
        found_matched = False
        found_year = False
        old_year_house = None
        for code in ("73036", "73013", "73003", "73056", "73178", "73101"):
            r = s.get(f"{BASE}/api/communes/{code}/houses", params={"min_score": 0}, timeout=30)
            if r.status_code != 200:
                continue
            items = r.json().get("items", [])
            for h in items[:200]:
                if h.get("bdtopo_matched"):
                    found_matched = True
                if h.get("bdtopo_year"):
                    found_year = True
                    if h["bdtopo_year"] < 1948 and old_year_house is None:
                        old_year_house = h
            if found_matched and found_year and old_year_house:
                break
        assert found_matched, "No house has bdtopo_matched=True across sampled communes"
        assert found_year, "No house has bdtopo_year across sampled communes"
        # Old house should score >= 80
        if old_year_house:
            assert old_year_house["score"] >= 80, (
                f"Old bdtopo_year={old_year_house['bdtopo_year']} but score={old_year_house['score']}"
            )

    def test_get_single_enriched_house(self, s):
        # find one and GET it individually
        for code in ("73036", "73013", "73003"):
            r = s.get(f"{BASE}/api/communes/{code}/houses", timeout=30)
            if r.status_code != 200:
                continue
            for h in r.json().get("items", [])[:100]:
                if h.get("bdtopo_matched") and h.get("bdtopo_year"):
                    r2 = s.get(f"{BASE}/api/houses/{h['id']}", timeout=15)
                    assert r2.status_code == 200
                    d = r2.json()
                    assert d.get("bdtopo_matched") is True
                    assert d.get("bdtopo_year")
                    assert d.get("start_date")
                    return
        pytest.skip("No enriched house found in sampled communes")
