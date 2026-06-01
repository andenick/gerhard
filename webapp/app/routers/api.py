"""JSON + download API endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app import config as C
from app.services import data_service as D
from app.services import chart_service as CH
from app.services import download_service as DL

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/chart/{chart_key}")
def chart(chart_key: str, y0: int | None = None, y1: int | None = None,
          series: str | None = None, variable: str | None = None, countries: str | None = None):
    params = {"y0": y0, "y1": y1, "series": series, "variable": variable,
              "countries": countries.split(",") if countries else []}
    return JSONResponse(CH.build_chart(chart_key, params))


@router.get("/series/{series_id}")
def series(series_id: str, variable: str | None = None, countries: str | None = None, limit: int = 5000):
    df = D.load_dataset(series_id)
    if df.empty:
        raise HTTPException(404, f"No data for '{series_id}'")
    if countries and "country_code" in df.columns:
        df = df[df["country_code"].isin(countries.split(","))]
    if variable and variable in df.columns:
        keep = [c for c in ["country_code", "country_name", "year", "date"] if c in df.columns]
        df = df[keep + [variable]]
    return JSONResponse(json.loads(df.head(limit).to_json(orient="records")))


@router.get("/explorer/options")
def explorer_options():
    out = [{"id": sid, "name": e.get("name"), "module": e.get("module"),
            "metric_columns": e.get("metric_columns", []), "has_country": e.get("has_country", False)}
           for sid, e in D.list_series().items() if e.get("cached")]
    return JSONResponse(sorted(out, key=lambda x: x["id"]))


@router.get("/explorer/series/{series_id}/meta")
def series_meta(series_id: str):
    df = D.load_dataset(series_id)
    entry = D.dataset_entry(series_id) or {}
    countries = sorted(df["country_code"].dropna().unique().tolist()) if "country_code" in df.columns else []
    metrics = [c for c in df.columns if c not in ("country_code", "country_name", "year", "date")]
    return JSONResponse({"id": series_id, "name": entry.get("name"),
                         "metric_columns": metrics, "countries": countries})


@router.get("/download/{key}.{fmt}")
def download(key: str, fmt: str):
    return DL.stream(key, fmt)


@router.get("/freshness")
def freshness():
    log = json.loads(C.REFRESH_LOG.read_text(encoding="utf-8")) if C.REFRESH_LOG.exists() else {}
    return JSONResponse({"sources": log,
                         "series": {sid: e.get("freshness") for sid, e in D.list_series().items()}})
