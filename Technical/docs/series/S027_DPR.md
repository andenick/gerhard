# Data Provenance Record: S027

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S027 |
| Name | Yield Curve Panel |
| Description | Daily US Treasury yield curves (19 maturities, 1954-present) |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | US Treasury / FRED |
| Units | percent |
| Year Range | 1954-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: US Treasury / FRED

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L110 | Technical/src/pipeline/L_load/L110_*.py |
| Processing | P120 | Technical/src/pipeline/P_process/P120_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L110** → Fetch data from US Treasury / FRED
2. **P120** → Clean, standardize, merge into panel format
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
| Yield curve values | -2% to 25% for modern era | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.
