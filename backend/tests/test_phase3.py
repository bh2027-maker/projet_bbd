"""Phase 3 backend tests: seed INSEE codes, mairie, discovery, tour PDF."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://bbd-detection.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


# ----- Communes / INSEE seed -----
class TestCommunes:
    def test_list_returns_25(self):
        r = requests.get(f"{API}/communes", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 25, f"Expected 25, got {data['count']}"
        codes = {c["code_insee"] for c in data["items"]}
        # Vrais codes attendus
        expected = {"74138", "73036", "74097", "73178", "73101"}
        assert expected.issubset(codes), f"Missing: {expected - codes}"
        # Verify old wrong codes absent
        assert "74099" not in codes, "Old wrong Gruffy code still present"
        assert "74069" not in codes, "Old wrong Cusy code still present"

    def test_gruffy_details(self):
        r = requests.get(f"{API}/communes/74138", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["nom"].lower().startswith("gruffy")
        assert d["population"] == 1504
        assert d["code_postal"] == "74540"
        assert 45.7 < d["lat"] < 45.85
        assert 6.0 < d["lon"] < 6.15


# ----- Mairie -----
class TestMairie:
    def test_mairie_gruffy(self):
        r = requests.get(f"{API}/communes/74138/mairie", timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Should have some fields
        assert isinstance(d, dict)
        if d:  # some communes may have no result
            keys = {"nom", "adresse", "telephone", "email", "site_web", "url_annuaire"}
            assert keys.issubset(d.keys()), f"Missing keys: {keys - set(d.keys())}"

    def test_mairie_cache(self):
        r1 = requests.get(f"{API}/communes/74138/mairie", timeout=30)
        r2 = requests.get(f"{API}/communes/74138/mairie", timeout=10)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json() == r2.json()

    def test_mairie_404(self):
        r = requests.get(f"{API}/communes/00000/mairie", timeout=10)
        assert r.status_code == 404


# ----- Discovery -----
class TestDiscovery:
    def test_status_shape(self):
        r = requests.get(f"{API}/discovery/status", timeout=10)
        assert r.status_code == 200
        d = r.json()
        for k in ("running", "total", "done", "current", "results", "started_at", "finished_at"):
            assert k in d
        assert isinstance(d["results"], list)
        for entry in d["results"]:
            assert "code_insee" in entry and "ok" in entry

    def test_start_idempotent_if_running(self):
        # Only assert double-call behavior; do not force a re-run.
        status = requests.get(f"{API}/discovery/status", timeout=10).json()
        r1 = requests.post(f"{API}/discovery/start", timeout=10)
        assert r1.status_code == 200
        s1 = r1.json()["status"]
        assert s1 in ("started", "already_running")
        r2 = requests.post(f"{API}/discovery/start", timeout=10)
        assert r2.json()["status"] == "already_running"


# ----- Tour PDF -----
def _get_house_ids(n=3):
    """Get n house IDs from any commune."""
    r = requests.get(f"{API}/communes", timeout=15).json()
    for c in r["items"]:
        rr = requests.get(f"{API}/communes/{c['code_insee']}/houses", timeout=15).json()
        if rr["count"] >= n:
            return [h["id"] for h in rr["items"][:n]], rr["items"][:n]
    return [], []


class TestTourPdf:
    def test_pdf_generation(self):
        ids, _ = _get_house_ids(3)
        if not ids:
            pytest.skip("Not enough houses in DB")
        r = requests.post(f"{API}/tour/pdf", json={"house_ids": ids}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 5000

    def test_pdf_empty_400(self):
        r = requests.post(f"{API}/tour/pdf", json={"house_ids": []}, timeout=10)
        assert r.status_code == 400

    def test_pdf_too_many_400(self):
        r = requests.post(f"{API}/tour/pdf", json={"house_ids": [f"x-{i}" for i in range(30)]}, timeout=10)
        assert r.status_code == 400

    def test_pdf_unknown_ids_404(self):
        r = requests.post(f"{API}/tour/pdf", json={"house_ids": ["ZZ-1", "ZZ-2"]}, timeout=10)
        assert r.status_code == 404

    def test_pdf_route_starts_with_best_score(self):
        """Nearest-neighbor: 1st house of route must be the highest-scoring one."""
        from services.pdf_tour import optimize_route  # type: ignore
        ids, houses = _get_house_ids(3)
        if len(houses) < 3:
            pytest.skip("Not enough houses")
        route = optimize_route(list(houses))
        best = max(houses, key=lambda h: h["score"])
        assert route[0]["id"] == best["id"]
