# Data Provenance Record: S003

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S003 |
| Name | Disaggregated Expenditure Panel |
| Description | Government expenditure disaggregated by category from World Bank WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | expenditure |
| Source | World Bank WDI |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_205 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L55 | Technical/src/pipeline/L_load/L55_*.py |
| Processing | P45 | Technical/src/pipeline/P_process/P45_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L55** → Fetch data from World Bank WDI
2. **P45** → Clean, standardize, merge into panel format
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
