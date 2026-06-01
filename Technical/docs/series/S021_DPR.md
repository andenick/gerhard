# Data Provenance Record: S021

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S021 |
| Name | IMF WEO Panel |
| Description | IMF World Economic Outlook macroeconomic indicators and forecasts |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | IMF World Economic Outlook |
| Units | mixed |
| Year Range | 1980-2029 |
| Country Scope | global_221 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: IMF World Economic Outlook

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L95 | Technical/src/pipeline/L_load/L95_*.py |
| Processing | P105 | Technical/src/pipeline/P_process/P105_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L95** → Fetch data from IMF World Economic Outlook
2. **P105** → Clean, standardize, merge into panel format
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
