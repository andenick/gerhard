# Data Provenance Record: S005

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S005 |
| Name | Enriched Tax Panel (GDP-integrated) |
| Description | Tax panel enriched with World Bank WDI GDP data for per-capita and level calculations |
| Content Type | time_series |
| Tier | 1 |
| Module | tax_revenue |
| Source | World Bank WDI GDP |
| Units | mixed (percent_gdp, usd_per_capita, billions_usd) |
| Year Range | 1972-2024 |
| Country Scope | global_192 |
| Construction | formula |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI GDP

This panel is constructed via transformation: S002 merged with World Bank WDI GDP; tax_revenue_usd = tax_pct_gdp × GDP.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L50 | Technical/src/pipeline/L_load/L50_*.py |
| Processing | P55 | Technical/src/pipeline/P_process/P55_*.py |

## Dependencies

S002

## Transformation Chain

1. **L50** → Fetch data from World Bank WDI GDP
2. **P55** → Clean, standardize, merge into panel format
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
