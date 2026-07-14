"""Phase 5 tests: CEE estimation, IGN tiles, multi-day tour PDF."""
import os
import sys
import io
import asyncio
import pytest
import requests

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
sys.path.insert(0, "/app/backend")

from services.cee_estimator import estimate_aides, estimate_household_profile  # noqa
from services.pdf_tour_v2 import split_days, _haversine_km  # noqa
from services.ign_tiles import fetch_ortho_image  # noqa


# ---------- cee_estimator ----------
class TestCEEEstimator:
    def test_profile_modeste(self):
        assert estimate_household_profile(20000) == "modeste"

    def test_profile_intermediaire(self):
        assert estimate_household_profile(27000) == "intermediaire"

    def test_profile_superieur(self):
        assert estimate_household_profile(35000) == "superieur"

    def test_estimate_aides_keys(self):
        r = estimate_aides(120, 22000)
        for k in ["profile", "coup_de_pouce", "mpr_low", "mpr_high",
                  "tva_savings", "aides_low", "aides_high", "argument"]:
            assert k in r, f"missing {k}"
        assert r["profile"] == "modeste"
        assert r["coup_de_pouce"] == 5000
        assert r["aides_low"] > 0 and r["aides_high"] >= r["aides_low"]

    def test_estimate_aides_large_bump(self):
        base = estimate_aides(100, 27000)
        big = estimate_aides(200, 27000)
        assert big["aides_low"] == base["aides_low"] + 500


# ---------- ign_tiles ----------
class TestIGNTiles:
    def test_fetch_ortho_image(self):
        # Bellecombe-en-Bauges approx coordinates
        data = asyncio.run(fetch_ortho_image(45.6640, 6.1580, zoom=18, grid=3))
        assert isinstance(data, bytes)
        assert len(data) > 5000, f"image too small: {len(data)}"
        # JPEG magic bytes
        assert data[:3] == b"\xff\xd8\xff"


# ---------- split_days ----------
def _mk(i, lat, lon, score=80):
    return {"id": f"h{i}", "lat": lat, "lon": lon, "score": score,
            "code_insee": "73036", "commune_nom": "Test",
            "surface_habitable_estimee_m2": 120}


class TestSplitDays:
    def test_split_by_max_per_day(self):
        # 10 co-located houses, max=3 => 4 days
        houses = [_mk(i, 45.66, 6.15 + i * 0.00001) for i in range(10)]
        days = split_days(houses, max_per_day=3, max_km_per_day=1000)
        assert len(days) == 4
        assert sum(len(d) for d in days) == 10

    def test_split_by_km(self):
        # Spread out houses ~10km apart, max_km=5 => multiple days
        houses = [_mk(i, 45.60 + i * 0.1, 6.10) for i in range(5)]
        days = split_days(houses, max_per_day=100, max_km_per_day=5)
        assert len(days) > 1

    def test_empty(self):
        assert split_days([], 8, 40) == []


# ---------- API integration ----------
@pytest.fixture(scope="module")
def house_ids_bellecombe():
    r = requests.get(f"{BASE_URL}/api/communes/73036/houses", timeout=30)
    assert r.status_code == 200, r.text
    items = r.json().get("items", [])
    if len(items) < 8:
        pytest.skip(f"Only {len(items)} houses in 73036")
    return [h["id"] for h in items[:8]]


class TestTourPdfAPI:
    def test_pdf_generation_multi_day(self, house_ids_bellecombe):
        payload = {"house_ids": house_ids_bellecombe,
                   "max_per_day": 4, "max_km_per_day": 40.0,
                   "include_photos": True}
        r = requests.post(f"{BASE_URL}/api/tour/pdf", json=payload, timeout=180)
        assert r.status_code == 200, r.text[:500]
        assert r.headers["content-type"] == "application/pdf"
        assert r.content[:4] == b"%PDF"
        # Photos IGN embedded => sizeable
        assert len(r.content) > 200_000, f"PDF only {len(r.content)} bytes"
        # Cover + 8 house pages
        # verify page count via text extraction is optional; just check bytes

    def test_pdf_over_limit(self):
        ids = [f"fake-{i}" for i in range(51)]
        r = requests.post(f"{BASE_URL}/api/tour/pdf",
                          json={"house_ids": ids}, timeout=30)
        assert r.status_code == 400

    def test_pdf_empty(self):
        r = requests.post(f"{BASE_URL}/api/tour/pdf",
                          json={"house_ids": []}, timeout=30)
        assert r.status_code == 400


# ---------- Regression sanity check ----------
class TestRegression:
    def test_communes_list(self):
        r = requests.get(f"{BASE_URL}/api/communes", timeout=30)
        assert r.status_code == 200
        assert r.json()["count"] > 0

    def test_stats(self):
        r = requests.get(f"{BASE_URL}/api/stats", timeout=30)
        assert r.status_code == 200
        assert "nb_communes" in r.json()

    def test_pipeline(self):
        r = requests.get(f"{BASE_URL}/api/pipeline", timeout=30)
        assert r.status_code == 200
        assert "counts" in r.json()

    def test_houses(self):
        r = requests.get(f"{BASE_URL}/api/communes/73036/houses", timeout=30)
        assert r.status_code == 200
