# Data Provenance Record: S019

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S019 |
| Name | Aggregates Panel |
| Description | Regional and income-group aggregated fiscal indicators |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI (aggregated) |
| Units | mixed |
| Year Range | 1972-2024 |
| Country Scope | regional_aggregates |
| Construction | composite |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI (aggregated)

This panel is constructed by combining upstream panels: S006.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | N/A (composite) | N/A |
| Processing | P98 | Technical/src/pipeline/P_process/P98_*.py |

## Dependencies

S006

## Transformation Chain

1. **Upstream panels** → Read dependent panels
2. **P98** → Clean, standardize, merge into panel format
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
