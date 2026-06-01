# Decomposition: S019 — Aggregates Panel

## Quick Reference

| Field | Value |
|-------|-------|
| Series ID | S019 |
| Name | Aggregates Panel |
| Type | Composite (aggregated from S006) |
| Components | S006 (Master Fiscal Panel) |
| Coverage | Regional and income-group aggregates |

## Sub-Components

| Component | Source | Period | Units |
|-----------|--------|--------|-------|
| S006 (Master Fiscal Panel) | Composite | 1972-2024 | Mixed |

## Construction Steps

1. Load S006 (master_fiscal_panel.xlsx)
2. Group by World Bank region (East Asia, Europe, Latin America, MENA, South Asia, Sub-Saharan Africa, North America)
3. Group by income class (High, Upper-middle, Lower-middle, Low)
4. Compute mean, median, weighted_mean, min, max for each variable
5. Output to aggregates_panel.xlsx

## Construction Diagram

```mermaid
graph TD
    S006[S006: Master Fiscal Panel] --> P98[P98: Build Aggregates]
    P98 --> AGG_REGION[Regional Aggregates]
    P98 --> AGG_INCOME[Income-Group Aggregates]
    AGG_REGION --> S019[S019: Aggregates Panel]
    AGG_INCOME --> S019
    
    style S019 fill:#f9f,stroke:#333,stroke-width:3px
```

---

*Decomposition created 2026-05-12 during Anu Framework integration*
