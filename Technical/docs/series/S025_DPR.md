# Data Provenance Record: S025

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S025 |
| Name | US Monetary Panel |
| Description | FRED monetary aggregates: M1, M2, monetary base, velocity |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | FRED (St. Louis Fed) |
| Units | mixed (billions_usd, ratio) |
| Year Range | 1954-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: FRED (St. Louis Fed)

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L111 | Technical/src/pipeline/L_load/L111_*.py |
| Processing | P111 | Technical/src/pipeline/P_process/P111_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L111** → Fetch data from FRED (St. Louis Fed)
2. **P111** → Clean, standardize, merge into panel format
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
