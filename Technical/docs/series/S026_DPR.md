# Data Provenance Record: S026

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S026 |
| Name | MSPD Panel |
| Description | Monthly Statement of the Public Debt — $30.6T outstanding, security-level detail |
| Content Type | time_series |
| Tier | 1 |
| Module | us_treasury |
| Source | US Treasury MSPD (TreasuryDirect) |
| Units | millions_usd |
| Year Range | 2001-2026 |
| Country Scope | US |
| Construction | direct |
| Created | 2026-05-11 |

## Data Source

**Primary Source**: US Treasury MSPD (TreasuryDirect)

This panel is constructed directly from API data.

## LEPAVR Pipeline

| Phase | Script | Path |
|-------|--------|------|
| Loading | L105 | Technical/src/pipeline/L_load/L105_*.py |
| Processing | P115 | Technical/src/pipeline/P_process/P115_*.py |

## Dependencies

None (primary data source)

## Transformation Chain

1. **L105** → Fetch data from US Treasury MSPD (TreasuryDirect)
2. **P115** → Clean, standardize, merge into panel format
3. **Output** → 

## Validation Record

| Check | Status | Date |
|-------|--------|------|
| Output file exists | FAIL (not generated) | 2026-05-11 |
| Chopped CSV generated | N/A | 2026-05-11 |
| Extenbook generated | N/A | 2026-05-11 |
| Research JSON exists | PASS | 2026-05-11 |
| No synthetic data | PASS (API-sourced) | 2026-05-11 |

## Known Issues

None documented at initialization.
