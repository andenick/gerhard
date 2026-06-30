# Data Provenance Record: S011

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S011 |
| Name | Expenditure Functions Panel |
| Description | Government expenditure by functional category (COFOG-adjacent) from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | expenditure |
| Source | World Bank WDI |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_259 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L77 | Technical/src/pipeline/L_load/L77_*.py |
| Processing | P77 | Technical/src/pipeline/P_process/P77_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L77** → Fetch data from World Bank WDI
2. **P77** → Clean, standardize, merge into panel format
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
