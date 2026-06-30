# Data Provenance Record: S028

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S028 |
| Name | Treasury Auction Panel |
| Description | US Treasury auction results — bid-to-cover, high yield, tail by security type |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | US Treasury Auction Results |
| Units | mixed (percent, ratio, billions_usd) |
| Year Range | 1979-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: US Treasury Auction Results

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L115 | Technical/src/pipeline/L_load/L115_*.py |
| Processing | P125 | Technical/src/pipeline/P_process/P125_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L115** → Fetch data from US Treasury Auction Results
2. **P125** → Clean, standardize, merge into panel format
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
