# Data Provenance Record: S009

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S009 |
| Name | Balance of Payments Panel |
| Description | Current account, financial account, trade balance, FDI from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI |
| Units | mixed (percent_gdp, billions_usd) |
| Year Range | 1972-2024 |
| Country Scope | global |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L60 | Technical/src/pipeline/L_load/L60_*.py |
| Processing | P75 | Technical/src/pipeline/P_process/P75_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L60** → Fetch data from World Bank WDI
2. **P75** → Clean, standardize, merge into panel format
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
