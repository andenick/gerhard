# Data Provenance Record: S013

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S013 |
| Name | Labor Panel |
| Description | Employment, unemployment, labor force participation from WDI |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | World Bank WDI |
| Units | mixed (percent, ratio) |
| Year Range | 1972-2024 |
| Country Scope | global_235 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: World Bank WDI

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L79 | Technical/src/pipeline/L_load/L79_*.py |
| Processing | P79 | Technical/src/pipeline/P_process/P79_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L79** → Fetch data from World Bank WDI
2. **P79** → Clean, standardize, merge into panel format
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
