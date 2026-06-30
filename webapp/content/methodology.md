---
title: "Methodology &amp; Sources"
section: about
---

This site is a read-only window onto the Gerhard public-finance data platform. Every chart
is generated on the server from a normalized data cache, and every figure is downloadable
in CSV, Excel, and Parquet. Nothing shown here is hand-entered or estimated at the
website layer.

## Data sources

- **World Bank — World Development Indicators (WDI):** tax revenue, expenditure by
  function, debt, and GDP, for 190+ countries. Most cross-country panels derive from
  WDI.[cite:worldbank_wdi]
- **U.S. Treasury — Fiscal Data / Monthly Statement of the Public Debt (MSPD) and Monthly
  Treasury Statement (MTS):** the structure of the national debt, receipts and outlays, and
  the duration analyses in the Treasury section.[cite:treasury_mspd][cite:treasury_mts]
- **Federal Reserve (FRED, FRBNY SOMA):** interest rates, the yield curve, monetary
  aggregates, and the Fed's securities holdings used in the QE analysis.[cite:fred][cite:fed_soma]
- **Piketty–Saez–Zucman Distributional National Accounts (DINA):** the long-run U.S. income
  distribution and top-income-share series.[cite:piketty_saez_zucman_2018]
- **IRS Statistics of Income and the Congressional Budget Office:** the distribution of the
  tax burden.[cite:irs_soi][cite:cbo]

## How the data is built

The underlying data is constructed by the Gerhard data pipeline,
which enforces a single source of truth (a series registry), full provenance for every
series, and a strict no-synthetic-data rule: if a value cannot be traced to a published
source or a documented analytical method, it is left missing rather than fabricated. The
website reads the registry and the constructed panels; it never invents data.

## Live data

Series marked **live** in the [data catalog](/data) refresh automatically from their source
APIs (U.S. Treasury Fiscal Data, World Bank, and FRED) on a schedule. A refresh that fails
validation never overwrites good data with bad—the last verified snapshot is retained and
the failure is logged.

## Historical narratives and the knowledge base

The historical narratives are authored from the project's data and from established
economic history. Quotations and citations from primary sources (CBO long-term outlooks,
historical fiscal documents, and the works of Gerhard Colm) are being added as the
project's knowledge base is extracted from source documents; until then, claims that will
ultimately rest on those sources are written from secondary economic history and marked
where data coverage is thin. Continuous distributional and tax data begin in 1913; pre-1913
eras rely on Treasury historical records and economic history.

## Limitations

- Cross-country comparability is imperfect: tax and spending definitions vary, and
  functional (COFOG) detail is far richer for OECD/EU countries than elsewhere.
- Some U.S. series begin only in 1913 (distributional) or 1972 (World Bank); pre-modern
  eras are necessarily more qualitative.
- The Treasury duration analyses involve modeling choices documented in the MSPD module's
  technical reports, available with the data.
