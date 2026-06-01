# Data Provenance Record: S022

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S022 |
| Name | US Monthly Treasury Statement Panel |
| Description | US federal receipts and outlays by category from Treasury MTS |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | US Treasury MTS |
| Units | millions_usd |
| Year Range | 1998-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: US Treasury MTS

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L106 | Technical/src/pipeline/L_load/L106_*.py |
| Processing | P106 | Technical/src/pipeline/P_process/P106_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L106** → Fetch data from US Treasury MTS
2. **P106** → Clean, standardize, merge into panel format
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
