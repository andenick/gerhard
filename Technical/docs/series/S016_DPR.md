# Data Provenance Record: S016

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S016 |
| Name | Debt Composition Panel |
| Description | External vs domestic debt, short vs long term, debt service ratios |
| Content Type | time_series |
| Tier | 1 |
| Module | public_debt |
| Source | World Bank WDI |
| Units | mixed (percent_gdp, percent_gni, percent_exports) |
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
| Loading | L75 | Technical/src/pipeline/L_load/L75_*.py |
| Processing | P90 | Technical/src/pipeline/P_process/P90_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L75** → Fetch data from World Bank WDI
2. **P90** → Clean, standardize, merge into panel format
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

---

*DPR generated 2026-05-11 during Anu Framework integration (Stage 3: Ingestion)*
