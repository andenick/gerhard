# Data Provenance Record: S023

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S023 |
| Name | Treasury Interest Rates Panel |
| Description | Average interest rates on US Treasury securities by maturity |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | US Treasury / TreasuryDirect |
| Units | percent |
| Year Range | 2001-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: US Treasury / TreasuryDirect

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L108 | Technical/src/pipeline/L_load/L108_*.py |
| Processing | P108 | Technical/src/pipeline/P_process/P108_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L108** → Fetch data from US Treasury / TreasuryDirect
2. **P108** → Clean, standardize, merge into panel format
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
