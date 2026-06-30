# Data Provenance Record: S012

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S012 |
| Name | Income Panel |
| Description | GNI, adjusted net national income, household consumption from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI |
| Units | mixed (current_usd, percent_gdp) |
| Year Range | 1972-2024 |
| Country Scope | global_258 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L78 | Technical/src/pipeline/L_load/L78_*.py |
| Processing | P78 | Technical/src/pipeline/P_process/P78_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L78** → Fetch data from World Bank WDI
2. **P78** → Clean, standardize, merge into panel format
3. **Output** → 

## Validation Record

| Check | Status | Date |
|-------|--------|------|
| Output file exists | PASS | 2026-05-11 |
| Chopped CSV generated | PASS | 2026-05-11 |
| Extenbook generated | PASS | 2026-05-11 |
| Research JSON exists | PASS | 2026-05-11 |
| No synthetic data | PASS (API-sourced) | 2026-05-11 |

## Known Issues

None documented at initialization.
