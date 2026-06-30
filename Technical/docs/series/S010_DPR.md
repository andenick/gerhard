# Data Provenance Record: S010

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S010 |
| Name | Financial Sector Panel |
| Description | Bank credit, M2, stock market cap, insurance from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_243 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L76 | Technical/src/pipeline/L_load/L76_*.py |
| Processing | P76 | Technical/src/pipeline/P_process/P76_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L76** → Fetch data from World Bank WDI
2. **P76** → Clean, standardize, merge into panel format
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
