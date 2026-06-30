# Data Provenance Record: S004

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S004 |
| Name | Disaggregated Debt Panel |
| Description | Public debt disaggregated by instrument type from World Bank WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | public_debt |
| Source | World Bank WDI |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_163 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L75 | Technical/src/pipeline/L_load/L75_*.py |
| Processing | P50 | Technical/src/pipeline/P_process/P50_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L75** → Fetch data from World Bank WDI
2. **P50** → Clean, standardize, merge into panel format
3. **Output** → 

## Validation Record

| Check | Status | Date |
|-------|--------|------|
| Output file exists | PASS | 2026-05-11 |
| Chopped CSV generated | PASS | 2026-05-11 |
| Extenbook generated | PASS | 2026-05-11 |
| Research JSON exists | PASS | 2026-05-11 |
| No synthetic data | PASS (API-sourced) | 2026-05-11 |


## Reference Value Spot-Checks

| Check | Expected | Status | Date |
|-------|----------|--------|------|
| US (USA) debt/GDP 2015+ | 50-200% range | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.
