# Data Provenance Record: S007

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S007 |
| Name | Revenue Composition Panel |
| Description | Tax revenue decomposed by type: income, goods/services, trade, other |
| Content Type | time_series |
| Tier | 1 |
| Module | tax_revenue |
| Source | World Bank WDI (fiscal detail) |
| Units | percent_revenue |
| Year Range | 1972-2024 |
| Country Scope | global |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI (fiscal detail)

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L55 | Technical/src/pipeline/L_load/L55_*.py |
| Processing | P65 | Technical/src/pipeline/P_process/P65_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L55** → Fetch data from World Bank WDI (fiscal detail)
2. **P65** → Clean, standardize, merge into panel format
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
