# Data Provenance Record: S006

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S006 |
| Name | Master Fiscal Panel |
| Description | Unified fiscal panel merging tax + expenditure + debt + GDP (29 columns) |
| Content Type | time_series |
| Tier | 1 |
| Module | tax_revenue |
| Source | Composite (WDI tax, expenditure, debt, GDP) |
| Units | mixed |
| Year Range | 1972-2024 |
| Country Scope | global_238 |
| Construction | composite |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: Composite (WDI tax, expenditure, debt, GDP)

This panel is constructed by combining upstream panels: S005, S003, S004.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | N/A (composite) | N/A |
| Processing | P60 | Technical/src/pipeline/P_process/P60_*.py |

## Dependencies

S005, S003, S004

## Transformation Chain

1. **Upstream panels** → Read dependent panels
2. **P60** → Clean, standardize, merge into panel format
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
| Global tax/GDP mean 2018-2022 | 10-25% range; 238 countries | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.
