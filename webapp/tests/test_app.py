"""Integration tests for the Gerhard website.

Run:  cd webapp && python -m pytest -q
Assumes build_cache.py has been run (cache + manifest present).
"""
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import data_service as D
from data_pipeline import validators

client = TestClient(app)

PAGES = ["/", "/history", "/history/founding", "/history/new-deal-wwii", "/history/modern",
         "/modern", "/modern/revenue", "/modern/spending", "/modern/deficits-debt",
         "/modern/state-local", "/treasury", "/treasury/duration", "/treasury/qe",
         "/treasury/yield-curve", "/treasury/debt-structure", "/treasury/regulation",
         "/explore", "/data", "/methodology", "/about"]

CHARTS = ["us_top_income_shares", "us_tax_composition", "us_spending_by_function",
          "us_spending_treemap", "us_debt_to_gdp", "us_fiscal_balance", "us_tax_revenue",
          "treasury_duration_evolution", "qe_duration_extraction", "yield_curve_history",
          "us_state_tax_choropleth", "regulation_timeline"]


@pytest.mark.parametrize("url", PAGES)
def test_pages_render(url):
    r = client.get(url)
    assert r.status_code == 200, url
    assert len(r.content) > 200


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["series_cached"] >= 25


@pytest.mark.parametrize("key", CHARTS)
def test_charts_have_data(key):
    r = client.get(f"/api/chart/{key}")
    assert r.status_code == 200
    assert r.json().get("figure", {}).get("data"), f"{key} produced no traces"


def test_explorer_options():
    r = client.get("/api/explorer/options")
    assert r.status_code == 200
    assert len(r.json()) >= 25


def test_generic_chart_multicountry():
    r = client.get("/api/chart/generic?series=S006&variable=debt_pct_gdp&countries=US,GB,DE")
    assert r.status_code == 200
    assert r.json()["figure"]["data"]


@pytest.mark.parametrize("fmt", ["csv", "xlsx", "json", "parquet"])
def test_downloads(fmt):
    r = client.get(f"/api/download/us_top_income_shares.{fmt}")
    assert r.status_code == 200
    assert len(r.content) > 100


def test_download_slice_matches_cache():
    df_cache = D.load_dataset("us_top_income_shares")
    r = client.get("/api/download/us_top_income_shares.csv")
    body = r.content.decode("utf-8").split("\n", 1)[1]  # skip provenance comment
    df_dl = pd.read_csv(io.StringIO(body))
    assert len(df_dl) == len(df_cache)


def test_download_unknown_404():
    assert client.get("/api/download/nope_nonexistent.csv").status_code == 404


def test_validator_rejects_empty():
    ok, _ = validators.validate_fetch(pd.DataFrame(), None)
    assert not ok


def test_validator_rejects_shrink():
    old = pd.DataFrame({"date": range(100), "v": range(100)})
    new = pd.DataFrame({"date": range(10), "v": range(10)})
    assert not validators.validate_fetch(new, old)[0]


def test_validator_accepts_growth():
    old = pd.DataFrame({"date": range(100), "v": range(100)})
    new = pd.DataFrame({"date": range(110), "v": range(110)})
    assert validators.validate_fetch(new, old)[0]
