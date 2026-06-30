# Data Provenance Record: S024

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S024 |
| Name | Governance Panel |
| Description | World Governance Indicators: voice, stability, effectiveness, regulation, rule of law, corruption |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WGI |
| Units | index (-2.5 to 2.5) |
| Year Range | 1996-2023 |
| Country Scope | global_205 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WGI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L100 | Technical/src/pipeline/L_load/L100_*.py |
| Processing | P110 | Technical/src/pipeline/P_process/P110_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L100** → Fetch data from World Bank WGI
2. **P110** → Clean, standardize, merge into panel format
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
| WGI index range | -2.5 to +2.5 standard scale | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.
