"""Build the canonical Parquet cache + site manifest for the Gerhard website.

Reads series_registry.json (single source of truth) plus the US-history and
MSPD datasets, normalizes them to a canonical schema, writes one Parquet per
dataset under site_data/cache/, and emits site_manifest.json which drives the
Explorer, Catalog, downloads, and freshness badges.

Run:  python webapp/data_pipeline/build_cache.py
Per WEBSITE_PLAN.md Phase 0.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config as C  # noqa: E402

ID_COLS = {"country_code", "country_name", "year", "date", "Year", "Date",
           "record_date", "month", "Unnamed: 0"}

# series eligible for live refresh -> adapter mapping (Phase 6)
LIVE_ADAPTERS = {
    "S001": "worldbank", "S002": "worldbank", "S003": "worldbank", "S004": "worldbank",
    "S005": "worldbank", "S006": "worldbank", "S022": "treasury", "S023": "treasury",
    "S025": "fred", "S026": "treasury", "S027": "fred", "S028": "treasury",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        if path.suffix.lower() in (".xlsx", ".xls"):
            return pd.read_excel(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            first = f.readline()
        skip = 1 if ("," not in first and first.strip().lower().endswith(".csv")) else 0
        return pd.read_csv(path, skiprows=skip, low_memory=False)
    except Exception as e:  # noqa: BLE001
        print(f"  ! read error {path.name}: {e}")
        return pd.DataFrame()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.loc[:, ~df.columns.astype(str).str.match(r"Unnamed: ?\d+")]
    rename = {}
    for c in df.columns:
        cl = str(c).strip()
        if cl == "Year":
            rename[c] = "year"
        elif cl == "Date":
            rename[c] = "date"
    df = df.rename(columns=rename)
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return df


def resolve_series_file(rel: str) -> Path | None:
    if not rel:
        return None
    cands = [rel, rel.replace("Output/", "Outputs/", 1), rel.replace("Outputs/", "Output/", 1)]
    for c in cands:
        p = C.PROJECT_ROOT / c
        if p.exists():
            return p
    return None


def metric_cols(df: pd.DataFrame) -> list[str]:
    return [str(c) for c in df.columns if c not in ID_COLS and c not in ("year", "date")]


def coverage(df: pd.DataFrame) -> dict:
    info: dict = {"rows": int(len(df))}
    if "year" in df.columns and df["year"].notna().any():
        info["year_range"] = [int(df["year"].min()), int(df["year"].max())]
    if "country_code" in df.columns:
        info["n_countries"] = int(df["country_code"].nunique())
    return info


def write_cache(key: str, df: pd.DataFrame) -> str:
    df.to_parquet(C.CACHE_DIR / f"{key}.parquet", index=False)
    return f"cache/{key}.parquet"


def download_links(key: str) -> dict:
    return {fmt: f"/api/download/{key}.{fmt}" for fmt in ("csv", "xlsx", "json", "parquet")}


def _provenance(sid: str, e: dict) -> dict:
    research = C.RESEARCH_DIR / f"{sid}_research.json"
    dpr = C.DPR_DIR / f"{sid}_DPR.md"
    return {
        "source": e.get("source"),
        "research": str(research.relative_to(C.PROJECT_ROOT)) if research.exists() else None,
        "dpr": str(dpr.relative_to(C.PROJECT_ROOT)) if dpr.exists() else None,
    }


def _freshness(e: dict) -> dict:
    adapter = LIVE_ADAPTERS.get(e.get("id"))
    cadence = {"treasury": "daily", "fred": "weekly", "worldbank": "weekly"}.get(adapter)
    return {"live": adapter is not None, "adapter": adapter, "cadence": cadence}


def build() -> dict:
    C.ensure_dirs()
    reg = json.loads(C.REGISTRY_PATH.read_text(encoding="utf-8"))
    manifest: dict = {"generated": _now(),
                      "framework": reg.get("_metadata", {}).get("framework"),
                      "series": {}, "us_history": {}, "treasury": {}, "pending": []}

    print("== Anu series ==")
    for sid, e in reg["series"].items():
        path = resolve_series_file(e.get("output_file", ""))
        if path is None:
            manifest["pending"].append(sid)
            manifest["series"][sid] = {
                "name": e.get("name"), "module": e.get("module"), "status": "pending_build",
                "cached": False, "source": e.get("source"), "units": e.get("units"),
                "country_scope": e.get("country_scope"), "year_range": e.get("year_range"),
                "provenance": _provenance(sid, e), "freshness": _freshness(e)}
            print(f"  {sid} PENDING: {e.get('output_file')}")
            continue
        df = normalize(read_panel(path))
        cache_file = write_cache(sid, df)
        manifest["series"][sid] = {
            "name": e.get("name"), "module": e.get("module"), "status": "cached", "cached": True,
            "source": e.get("source"), "units": e.get("units"), "construction": e.get("construction"),
            "country_scope": e.get("country_scope"), "year_range": e.get("year_range"),
            "columns": [str(c) for c in df.columns], "metric_columns": metric_cols(df),
            "has_country": "country_code" in df.columns, "cache_file": cache_file,
            **coverage(df), "downloads": download_links(sid),
            "provenance": _provenance(sid, e), "freshness": _freshness(e)}
        print(f"  {sid} OK {df.shape[0]}x{df.shape[1]} <- {path.name}")

    print("== US history ==")
    us_sets = {
        "us_tax_1913_2024": C.COUNTRIES_US / "Output/Enhanced_Analysis/us_historical_tax_trends_1913_2024.xlsx",
        "us_top_income_shares": C.COUNTRIES_US / "Output/Data/us_top_income_shares.xlsx",
        "us_government_expenditure": C.COUNTRIES_US / "Output/Data/us_government_expenditure.xlsx",
        "us_dina_distributional": C.COUNTRIES_US / "Output/Data/us_dina_distributional_data.xlsx",
        "us_federal_state_tax": C.COUNTRIES_US / "Output/Enhanced_Analysis/us_federal_state_tax_analysis.xlsx",
        "us_state_tax_estimates": C.COUNTRIES_US / "Output/Enhanced_Analysis/us_state_tax_estimates.xlsx",
        "us_tax_dist_2024": C.COUNTRIES_US / "Output/Enhanced_Analysis/us_tax_distribution_extended_2024.xlsx",
        "us_vs_oecd": C.COUNTRIES_US / "Output/Enhanced_Analysis/us_vs_oecd_tax_comparison.xlsx",
    }
    for key, p in us_sets.items():
        df = normalize(read_panel(p))
        if df.empty:
            print(f"  {key} MISSING {p}"); continue
        cache_file = write_cache(key, df)
        manifest["us_history"][key] = {
            "name": key.replace("_", " ").title(), "cache_file": cache_file,
            "columns": [str(c) for c in df.columns], "metric_columns": metric_cols(df),
            **coverage(df), "downloads": download_links(key),
            "provenance": {"source": "Gerhard US module (DINA/IRS/WB)"}}
        print(f"  {key} OK {df.shape[0]}x{df.shape[1]}")

    print("== Treasury / MSPD ==")
    tre_sets = {
        "treasury_comprehensive_ts": C.MSPD_OUT / "treasury_comprehensive_time_series.csv",
        "duration_comparison": C.MSPD_OUT / "duration_comparison.csv",
        "duration_metrics_diff": C.MSPD_OUT / "duration_metrics_with_differences.csv",
        "qe_duration_timeline": C.MSPD_OUT / "qe_duration_extraction_timeline.csv",
        "qe_program_impact": C.MSPD_OUT / "qe_program_impact_summary.csv",
        "treasury_monthly": C.MSPD_OUT / "treasury_monthly_summary.csv",
        "treasury_annual": C.MSPD_OUT / "treasury_annual_summary.csv",
        "regulatory_timeline": C.MSPD_OUT / "regulatory_timeline_treasury_market.csv",
        "duration_outstanding": C.MSPD_OUT / "duration_outstanding_comprehensive_analysis.csv",
    }
    for key, p in tre_sets.items():
        df = normalize(read_panel(p))
        if df.empty:
            print(f"  {key} MISSING {p}"); continue
        cache_file = write_cache(key, df)
        manifest["treasury"][key] = {
            "name": key.replace("_", " ").title(), "cache_file": cache_file,
            "columns": [str(c) for c in df.columns], "metric_columns": metric_cols(df),
            **coverage(df), "downloads": download_links(key),
            "provenance": {"source": "US Treasury MSPD / Fiscal Data; MSPD analysis module"}}
        print(f"  {key} OK {df.shape[0]}x{df.shape[1]}")

    C.MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    n = sum(1 for s in manifest["series"].values() if s.get("cached"))
    print(f"\nManifest: {C.MANIFEST_PATH}")
    print(f"  series cached: {n}/{len(manifest['series'])}  pending: {manifest['pending']}")
    print(f"  us_history: {len(manifest['us_history'])}  treasury: {len(manifest['treasury'])}")
    return manifest


if __name__ == "__main__":
    build()
