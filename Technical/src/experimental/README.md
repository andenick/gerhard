# Experimental Scripts

These scripts are untested prototypes from "Phase 5" development (October 2025).
They have not been validated against real data and require additional dependencies.

## Promoted to Production (2026-03-31)

The following scripts were fixed, tested, and promoted to `Technical/src/`:

| Script | Fixes Applied | Status |
|--------|--------------|--------|
| ml_fiscal_forecasting.py | Fixed XGGBoost typo, logger-before-definition bug, joblib.save->dump, slice bug, hardcoded paths, emoji encoding | Promoted |
| interactive_dashboard.py | Fixed hardcoded paths, added get_country_count/get_year_span helpers, run_server->run (Dash 3.x) | Promoted |
| fiscal_api.py | Fixed hardcoded paths, missing closing paren syntax error, emoji encoding | Promoted |

## Remaining Experimental Scripts

| Script | Purpose | Extra Dependencies |
|--------|---------|-------------------|
| policy_simulation.py | What-if fiscal policy simulator | scipy, scikit-learn |
| subnational_analysis.py | State/provincial fiscal analysis | (standard) |
| multilingual_mobile.py | i18n/l10n mobile web app | flask, babel, iso639, iso3166 |
| advanced_visualizations.py | 3D charts, geographic maps | plotly, folium, geopandas |
| fiscal_regime_news_collector.py | News event collector | requires API keys (NewsAPI) |
| fiscal_regime_historical_collector.py | Historical event collection plans | (standard) |
| run_historical_collection.py | NYT Archive API runner | requires API key |

## Known Issues (remaining scripts)

- multilingual_mobile.py imports flask twice (lines 27 and 1753)
- Remaining scripts still contain hardcoded paths

## To Promote a Script

1. Fix hardcoded paths (use utils.config.project_root())
2. Add input validation and error handling
3. Test with real data
4. Move to parent src/ directory
