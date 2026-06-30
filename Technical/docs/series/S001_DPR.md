# Data Provenance Record: S001

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S001 |
| Name | Standardized Tax Data |
| Description | World Bank tax revenue indicators standardized with country codes and year alignment |
| Content Type | time_series |
| Tier | 2 |
| Module | tax_revenue |
| Source | World Bank WDI |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_193 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L00 | Technical/src/pipeline/L_load/L00_*.py |
| Processing | P00 | Technical/src/pipeline/P_process/P00_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L00** → Fetch data from World Bank WDI
2. **P00** → Clean, standardize, merge into panel format
3. **Output** → 

## Validation Record

| Check | Status | Date |
|-------|--------|------|
| Output file exists | FAIL (not generated) | 2026-05-11 |
| Chopped CSV generated | N/A | 2026-05-11 |
| Extenbook generated | N/A | 2026-05-11 |
| Research JSON exists | PASS | 2026-05-11 |
| No synthetic data | PASS (API-sourced) | 2026-05-11 |

## Known Issues

None documented at initialization.
