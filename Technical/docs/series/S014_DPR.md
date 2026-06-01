# Data Provenance Record: S014

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S014 |
| Name | Exchange Rate Panel |
| Description | Official exchange rate, real effective exchange rate, PPP from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI |
| Units | mixed (lcu_per_usd, index) |
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
| Loading | L70 | Technical/src/pipeline/L_load/L70_*.py |
| Processing | P80 | Technical/src/pipeline/P_process/P80_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L70** → Fetch data from World Bank WDI
2. **P80** → Clean, standardize, merge into panel format
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
