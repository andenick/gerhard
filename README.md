# Gerhard: Global Public Finance Analysis Platform

Named after **Gerhard Colm** (1897-1968), pioneering public finance economist.

## Overview

Comprehensive fiscal analysis platform covering:
- **Tax Revenue Analysis** -- Who pays what share of taxes (US + 202 countries)
- **Government Expenditure Analysis** -- What governments spend and how (COFOG classification)
- **Public Debt Analysis** -- Fiscal sustainability and debt dynamics
- **Integrated Fiscal Analysis** -- Unified budget constraint framework (T - G = -dDebt)

**Coverage**: 202 countries, 5,565 country-years of data (1972-2024)

### Key Findings (US, 2021)
- Top 1% pay 40.4% of all federal income taxes (earning 24.5% of income)
- Bottom 50% pay 2.3% of all federal income taxes
- US tax-to-GDP: 10.9% (below global average of 15.3%)

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Point DATA_ROOT at your external source-data folder (where bulk
#    downloads live), and OUTPUT_ROOT at where outputs should be written.
#    See data/MANIFEST.md for what to download and the expected layout.
export DATA_ROOT=/path/to/your/source-data      # e.g. contains WorldBank/WDI_CSV/, IMF/
export OUTPUT_ROOT=/path/to/your/outputs        # optional; defaults to repo-relative paths
#    (Windows PowerShell: $env:DATA_ROOT = "D:\path\to\source-data")

# 3. Provide your own API key(s) — see "API keys" below.
export FRED_API_KEY=your_free_fred_key
```

`DATA_ROOT` (default `data`) is where the pipeline READS bulk source data
(World Bank WDI CSV, IMF WEO, etc.). `OUTPUT_ROOT` (default `outputs`) is where
the project may write its own outputs. Copy `.env.example` to `.env` and fill it
in, or export the variables in your shell.

### API keys — bring your own

All keys below are free. The code reads them from environment variables; nothing
is hardcoded.

| Service | Used by | Get a free key | Env var |
|---------|---------|----------------|---------|
| FRED (St. Louis Fed) | yield-curve & monetary pipeline (L110/L111), webapp FRED adapter | <https://fred.stlouisfed.org/docs/api/api_key.html> | `FRED_API_KEY` |
| News API (optional) | experimental fiscal-news collector | <https://newsapi.org/register> | `NEWS_API_KEY` |
| NYT (optional) | experimental fiscal-news collector | <https://developer.nytimes.com/get-started> | `NYT_API_KEY` |
| The Guardian (optional) | experimental fiscal-news collector | <https://open-platform.theguardian.com/access/> | `GUARDIAN_API_KEY` |
| Congress.gov (optional) | experimental fiscal-news collector | <https://api.congress.gov/sign-up/> | `CONGRESS_GOV_API_KEY` |

Other public data sources used by the pipeline and webapp require **no key**:
**US Treasury Fiscal Data** (<https://fiscaldata.treasury.gov/api-documentation/>),
the **World Bank** indicators API, and **OECD** SDMX endpoints.

## Quick Start

```bash
# Check data completeness
python Technical/src/check_data.py

# Run pipeline (using existing raw data)
python Technical/src/run_pipeline.py --skip-download

# Run full pipeline including downloads
python Technical/src/run_pipeline.py

# Run tests
python -m pytest Technical/tests/ -v
```

## Project Structure

> **Note:** This is a **code-only** release. The data directories below (`Output/`,
> `Countries/`, `Inputs/`, and `data/raw`–`data/processed`) and the generated
> `MASTER_INDEX.md` are **not** included in this repository — they are produced by
> running the pipeline against your own `DATA_ROOT`/`OUTPUT_ROOT` (see `data/MANIFEST.md`).
> The tree below documents the full pipeline layout for reference.

```
Gerhard/
├── Output/                     # Deliverables
│   ├── Data/                   # 39+ Excel files (one sheet each)
│   └── PDFs/                   # Visualizations and reports
├── Countries/                  # 202 country directories
│   ├── [CODE]/                 # e.g., US/, GB/, DE/
│   │   ├── Output/Data/        # Country-specific Excel data
│   │   ├── Output/PDFs/        # Country report and charts
│   │   ├── [CODE]_PROFILE.md   # Country metadata
│   │   └── [CODE]_SOURCES.md   # Data sources
│   └── MASTER_INDEX.md         # All 202 countries listed
├── Technical/                  # Implementation
│   ├── src/                    # 49 production Python scripts
│   │   ├── utils/              # Shared utilities (config, paths, I/O)
│   │   └── experimental/       # 10 untested prototypes
│   ├── data/raw/               # Raw data by source
│   ├── data/processed/         # Cleaned data
│   ├── configs/config.yaml     # Central configuration
│   ├── tests/                  # Test suite
│   └── docs/                   # LaTeX sources and references
├── Inputs/                     # Source data (see data/MANIFEST.md)
├── Analysis_Modules/           # Specialized analysis modules
│   ├── MSPD/                   # Multi-Source Public Debt
│   └── NA_Income_Tax/          # North American income tax analysis
├── requirements.txt            # Python dependencies
├── DATABASE_CATALOG.md         # Complete data inventory (70 KB)
├── FISCAL_DATA_SOURCES.md      # 13 source catalog
├── EXECUTIVE_SUMMARY.md        # Global insights
└── README.md                   # This file
```

## Data Sources

| Source | Coverage | Status |
|--------|----------|--------|
| World Bank | 200+ countries, tax revenue % GDP | Available |
| WID.world | 70+ countries, distributional data | Available (4.1 GB) |
| Eurostat | 27 EU countries, COFOG expenditure | Available (211 MB) |
| US DINA | US distributional accounts (1913-2022) | Available |
| IRS/CBO | US tax distribution by percentile | Available |
| IMF GFS | 190+ countries, government finance | Needs manual download |
| OECD | 38 countries, detailed revenue | Needs manual download |

## Pipeline

```
download_tax_data.py -> fetch_us_tax_data.py -> process_tax_data.py
    -> analyze_tax_burden.py -> visualize_tax_burden.py -> generate_latex_reports.py
```

Country pipeline: `build_country_infrastructure.py -> collect_country_data.py -> analyze_countries.py -> generate_country_reports.py`

Use `run_pipeline.py` to orchestrate. Use `check_data.py` to verify data availability.

## Status

**Core analysis**: Complete -- tax distribution, expenditure patterns, debt sustainability
**Country infrastructure**: Complete -- 202 countries with consistent structure
**Pipeline**: Functional with existing data. IMF and OECD downloads need API updates.
**Testing**: Basic test suite covering Excel compliance, country structure, data quality
**Experimental**: Dashboard, API, ML forecasting, multilingual -- in `Technical/src/experimental/`, untested

## Technology

Python 3.8+ with pandas, numpy, matplotlib, seaborn, openpyxl, requests, scipy, beautifulsoup4.
LaTeX (MiKTeX or TeX Live) for PDF report compilation.

See `requirements.txt` for full dependency list.

## References

- `DATABASE_CATALOG.md` -- Complete 4.35 GB data inventory
- `FISCAL_DATA_SOURCES.md` -- Detailed source documentation
- `EXECUTIVE_SUMMARY.md` -- Global insights and findings
- `Technical/docs/COFOG_TAXONOMY.md` -- Government spending classification
- `Technical/docs/FISCAL_COMPARABILITY_GUIDE.md` -- Cross-country methodology

---

*Reproducible data pipeline with provenance tracking.*
