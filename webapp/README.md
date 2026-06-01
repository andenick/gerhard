# Gerhard — The History and Present of American Public Finance

A self-hosted, dynamic website over the Gerhard public-finance data platform:
historical narratives, interactive Plotly charts, data-download buttons, a modern
fiscal section, and a deep Treasury-market / duration section. Built with
FastAPI + Jinja2 + server-side Plotly (vendored, no runtime CDN).

## Layout

```
webapp/
  app/            FastAPI app: config, routers (pages/api), services
                  (data/chart/download/narrative), templates, static (css/js/vendor)
  content/        Authored narrative markdown (history/, modern/, treasury/) + citations.json
  data_pipeline/  build_cache.py (registry+panels -> Parquet cache + manifest),
                  vendor.py (plotly.min.js), refresh.py + adapters/ (live API refresh),
                  validators.py
  site_data/      Generated: cache/*.parquet, site_manifest.json, refresh_log.json
  tests/          pytest integration + validator tests
  deploy/         Dockerfile, docker-compose.yml, nginx/Caddy, systemd units
```

The site **reads** from the project's `Technical/series_registry.json`, the
constructed panels, the US `Countries/US/` outputs, and the `Analysis_Modules/MSPD`
Treasury data. It never writes to them (single source of truth).

## Run locally (Windows / dev)

```bash
cd <project-root>
python -m venv webapp/.venv            # optional
pip install -r webapp/requirements.txt
python webapp/data_pipeline/vendor.py        # vendor plotly.min.js
python webapp/data_pipeline/build_cache.py   # build the cache + manifest
set PYTHONPATH=webapp && python -m uvicorn app.main:app --app-dir webapp --port 8080
# open http://127.0.0.1:8080
```

## Tests

```bash
cd webapp && python -m pytest -q
```

## Live data refresh

```bash
python webapp/data_pipeline/refresh.py --dry-run        # show what would refresh
python webapp/data_pipeline/refresh.py --only treasury  # refresh Treasury series
```

API keys (e.g. FRED) are read from environment variables (set `FRED_API_KEY`); Treasury and World
Bank need no key. A fetch that fails validation keeps the last-good data.

## Deploy (headless Linux)

**Docker (recommended):**
```bash
docker compose -f webapp/deploy/docker-compose.yml up -d --build
# app behind nginx on :80 ; refresh container loops every 6h
```

**systemd (non-Docker):** copy `deploy/gerhard-web.service`,
`deploy/gerhard-refresh.{service,timer}` to `/etc/systemd/system/`, point paths at
`/opt/gerhard`, and `systemctl enable --now`. Use `deploy/nginx.gerhard.conf` or
`deploy/Caddyfile` (auto-HTTPS) for the reverse proxy.

See `Technical/docs/WEBSITE_PLAN.md` for the full design.
