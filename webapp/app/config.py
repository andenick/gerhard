"""Central configuration for the Gerhard website.

Resolves project paths and API keys. API keys are read from environment
variables (e.g. FRED_API_KEY); see the project README and .env.example.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# webapp/app/config.py -> webapp/ -> Gerhard/
WEBAPP_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = WEBAPP_ROOT.parent

TECHNICAL = PROJECT_ROOT / "Technical"
REGISTRY_PATH = TECHNICAL / "series_registry.json"
RESEARCH_DIR = TECHNICAL / "research"
DPR_DIR = TECHNICAL / "docs" / "series"
PROCESSED_DIR = TECHNICAL / "data" / "processed"
COUNTRIES_US = PROJECT_ROOT / "Countries" / "US"
MSPD_OUT = PROJECT_ROOT / "Analysis_Modules" / "MSPD" / "Output" / "Data"
MSPD_RAW = PROJECT_ROOT / "Analysis_Modules" / "MSPD" / "Technical" / "data" / "raw_mspd_data"

SITE_DATA = WEBAPP_ROOT / "site_data"
CACHE_DIR = SITE_DATA / "cache"
MANIFEST_PATH = SITE_DATA / "site_manifest.json"
REFRESH_LOG = SITE_DATA / "refresh_log.json"
DOWNLOADS_DIR = SITE_DATA / "downloads"

CONTENT_DIR = WEBAPP_ROOT / "content"
TEMPLATES_DIR = WEBAPP_ROOT / "app" / "templates"
STATIC_DIR = WEBAPP_ROOT / "app" / "static"

SITE_TITLE = "Gerhard"
SITE_TAGLINE = "The History and Present of American Public Finance"
SITE_HOST = os.environ.get("GERHARD_HOST", "gerhard.local")


def get_api_key(name: str) -> str | None:
    """Resolve an API key from the environment.

    name 'fred' -> env var FRED_API_KEY. Returns None if unset.
    """
    return os.environ.get(f"{name.upper()}_API_KEY")


def ensure_dirs() -> None:
    for d in (SITE_DATA, CACHE_DIR, DOWNLOADS_DIR):
        d.mkdir(parents=True, exist_ok=True)
