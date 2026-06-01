# Data Manifest

Gerhard ships **code only** — no data is committed. To run the pipeline you
supply the source data yourself from the public sources below, and point the
`DATA_ROOT` environment variable at the folder that holds them.

All sources are free and public.

## Required / primary sources

| Dataset | Used by | Where to get it | Expected location under `DATA_ROOT` |
|---------|---------|-----------------|--------------------------------------|
| World Bank **WDI** (bulk CSV) | L50, L55–L100 (GDP, population, trade, fiscal, social, WGI) | <https://datatopics.worldbank.org/world-development-indicators/> → "Download CSV" | `WorldBank/WDI_CSV/[YYYY.MM.DD] WDICSV.csv` and `WorldBank/WDI_CSV/[YYYY.MM.DD] WDICountry.csv` |
| IMF **WEO** | L95 (`L95_extract_imf_weo.py`) | <https://www.imf.org/en/Publications/WEO/weo-database> | `IMF/` |

> The code references a specific WDI vintage filename (`[2025.10.10] WDICSV.csv`).
> If you download a different vintage, update the filename in the L-stage scripts
> or rename your file to match.

## Live / API sources (fetched at runtime, no manual download)

| Source | Used by | Key needed? | Docs |
|--------|---------|-------------|------|
| **FRED** (St. Louis Fed) | L110/L111, webapp FRED adapter | Yes (`FRED_API_KEY`, free) | <https://fred.stlouisfed.org/docs/api/> |
| **US Treasury Fiscal Data** | webapp Treasury adapter | No | <https://fiscaldata.treasury.gov/api-documentation/> |
| **World Bank** indicators API | webapp World Bank adapter | No | <https://datahelpdesk.worldbank.org/knowledgebase/articles/889392> |
| **OECD** Revenue Statistics (SDMX) | `download_oecd_revenue.py` | No | <https://data-explorer.oecd.org/> |
| **BLS** | (referenced; optional) | Free token (`BLS_API_KEY`) | <https://www.bls.gov/developers/> |

## Optional inputs (manual downloads)

Some integrated-fiscal parsers read manually-downloaded workbooks placed under
`Inputs/` in the repo tree (gitignored):

- `Inputs/2026,05,05 requests/UNU GRD/UNUWIDERGRD_2025_Full.xlsx` — UNU-WIDER Government Revenue Dataset (<https://www.wider.unu.edu/project/grd-government-revenue-dataset>)
- `Inputs/2026,05,05 requests/UNU GRD/Tax Effort scores_2021.xlsx`
- `Inputs/2026,05,05 requests/world-imf2026.xlsx` — IMF world fiscal workbook
- `Inputs/2026,05,05 requests/europa-webgate/` — Eurostat / EU Taxation Trends extracts

WID.world distributional data, if used, goes under `Technical/data/raw/wid/`
(<https://wid.world/data/>).
