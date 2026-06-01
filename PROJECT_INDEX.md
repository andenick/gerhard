# Gerhard -- Project Index

**Last Updated**: March 31, 2026

---

## Root Files

| File | Purpose |
|------|---------|
| `README.md` | Project overview and quick start |
| `HANDOFF_DOCUMENTATION.md` | Agent transfer guide with completion assessment |
| `PROJECT_INDEX.md` | This file -- complete inventory |
| `DATABASE_CATALOG.md` | Full 4.35 GB data inventory (70 KB) |
| `FISCAL_DATA_SOURCES.md` | 13 data sources documented |
| `EXECUTIVE_SUMMARY.md` | Global insights and key findings |
| `requirements.txt` | Python dependencies |

---

## Output/

User-facing deliverables.

| Path | Contents |
|------|----------|
| `Output/Data/` | 39+ Excel files (one sheet each) -- tax distribution, rankings, analysis |
| `Output/PDFs/` | 32+ visualizations (300 DPI PNG) and 2 LaTeX PDF reports |
| `Output/Visualization_Showcase/` | Curated visualization samples |
| `Output/README.md` | User guide for outputs |

---

## Countries/

202 country directories with consistent structure.

```
Countries/[CODE]/
├── Output/Data/          # Country-specific Excel data
├── Output/PDFs/          # Country report and charts
├── [CODE]_PROFILE.md     # Country metadata
└── [CODE]_SOURCES.md     # Data sources
```

Key files:
- `Countries/MASTER_INDEX.md` -- All 202 countries listed

---

## Technical/

Implementation details.

### Technical/src/ (49 production scripts)

**Core pipeline**:
- `run_pipeline.py` -- Pipeline orchestrator (--skip-download, --dry-run)
- `check_data.py` -- Data completeness checker
- `download_tax_data.py`, `fetch_us_tax_data.py` -- Data acquisition
- `process_tax_data.py` -- Data standardization
- `analyze_tax_burden.py` -- Analysis engine
- `visualize_tax_burden.py` -- Chart generation
- `generate_latex_reports.py` -- PDF report generation

**Country pipeline**:
- `build_country_infrastructure.py` -- Create 202 directories
- `collect_country_data.py` -- Gather country data
- `analyze_countries.py` -- Country-level analysis
- `generate_country_reports.py` -- 202 PDF reports

**Download scripts**:
- `download_worldbank_expenditure.py`, `download_eurostat_gfs.py` -- Working
- `download_wid_data.py`, `download_us_dina.py` -- Working
- `download_imf_gfs.py`, `download_oecd_revenue.py` -- Create guide files only

**Analysis scripts**:
- `analyze_expenditure_patterns.py`, `analyze_historical_trends.py`
- `analyze_public_debt.py`, `calculate_fiscal_balances.py`
- `create_integrated_fiscal_analysis.py`, `create_cross_country_comparisons.py`

**Integration scripts**:
- `integrate_expenditure_data.py`, `integrate_us_dina.py`
- `integrate_wid_data.py`, `integrate_with_countries.py`

### Technical/src/utils/ (5 modules)

- `config.py` -- Central configuration loader
- `paths.py` -- Path management
- `data_io.py` -- Data I/O utilities
- `logging_setup.py` -- Logging configuration
- `__init__.py`

### Technical/src/experimental/ (10 scripts, untested)

- `interactive_dashboard.py`, `fiscal_api.py`
- `ml_fiscal_forecasting.py`, `policy_simulation.py`
- `advanced_visualizations.py`, `subnational_analysis.py`
- `multilingual_mobile.py`
- `fiscal_regime_historical_collector.py`, `fiscal_regime_news_collector.py`
- `run_historical_collection.py`

### Technical/src/_archived/ (2 scripts)

- `download_imf_gfs.py`, `download_oecd_revenue_stats.py` (superseded)

### Technical/configs/

- `config.yaml` -- Central project configuration

### Technical/tests/ (pytest)

- `test_excel_compliance.py` -- One-sheet-per-file validation
- `test_country_structure.py` -- 202 directory structure checks
- `test_data_quality.py` -- Data quality assertions
- `test_no_hardcoded_paths.py` -- Path hygiene
- `test_pipeline_imports.py` -- Import validation
- `conftest.py` -- Shared fixtures

### Technical/docs/

- `us_tax_analysis_report.tex` + `.pdf` -- US tax analysis report
- `international_tax_analysis_report.tex` + `.pdf` -- International report
- `COFOG_TAXONOMY.md` -- Government spending classification
- `COFOG_MAPPING.md` -- COFOG code mapping
- `FISCAL_COMPARABILITY_GUIDE.md` -- Cross-country methodology
- `GLOBAL_EXPENDITURE_ANALYSIS.md` -- Expenditure analysis notes
- `METHODOLOGY_AND_LIMITATIONS_ANALYSIS.md` -- Methods documentation

### Technical/data/

- `raw/` -- Raw data by source (wid, us_dina, worldbank, eurostat, imf, oecd)
- `processed/` -- Cleaned and standardized data

---

## Analysis_Modules/

- `MSPD/` -- Multi-Source Public Debt analysis
- `NA_Income_Tax/` -- North American income tax analysis

---

## _archive/

- `docs/` -- 19 archived documentation files (session summaries, old handoffs, completion reports)
- 3 archived root-level documents

---

## Inputs/

Source data directory (see data/MANIFEST.md).

---

## Inputs/ (external data)

Backup system with SHA-256 checksums (4.319 GB cataloged).
