# Data Provenance Record: S002

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S002 |
| Name | Clean Tax Panel |
| Description | Cleaned tax panel with outlier removal, balanced country coverage, Sudan 638% correction |
| Content Type | time_series |
| Tier | 1 |
| Module | tax_revenue |
| Source | World Bank WDI (cleaned) |
| Units | percent_gdp |
| Year Range | 1972-2024 |
| Country Scope | global_192 |
| Construction | formula |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI (cleaned)

This panel is constructed via transformation: Cleaned S001 with gap handling and outlier removal.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L00 | Technical/src/pipeline/L_load/L00_*.py |
| Processing | P40 | Technical/src/pipeline/P_process/P40_*.py |

## Dependencies

S001

## Transformation Chain

1. **L00** → Fetch data from World Bank WDI (cleaned)
2. **P40** → Clean, standardize, merge into panel format
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
| US (USA) tax/GDP 2015-2023 mean | 8-15% range (WDI central govt only) | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.

---

*DPR generated 2026-05-11 during Anu Framework integration (Stage 3: Ingestion)*
