# Data Provenance Record: S020

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S020 |
| Name | WID Inequality Panel |
| Description | Top income shares, Gini, wealth distribution from World Inequality Database |
| Content Type | time_series |
| Tier | 1 |
| Module | global_comparative |
| Source | WID.world (4.1 GB) |
| Units | mixed (share, index) |
| Year Range | 1900-2024 |
| Country Scope | global_180 |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: WID.world (4.1 GB)

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L90 | Technical/src/pipeline/L_load/L90_*.py |
| Processing | P100 | Technical/src/pipeline/P_process/P100_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L90** → Fetch data from WID.world (4.1 GB)
2. **P100** → Clean, standardize, merge into panel format
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
| Top 1% income share mean | 0-50% range (decimal shares) | PASS | 2026-05-12 |

Verified via  — 15/15 tests pass.

## Known Issues

None documented at initialization.

---

*DPR generated 2026-05-11 during Anu Framework integration (Stage 3: Ingestion)*
