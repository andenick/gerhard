# Comprehensive Fiscal Data Sources
## Government Revenues + Expenditures + Budgetary Analysis

**Project:** Gerhard (Expanded to Full Fiscal Analysis)
**Scope:** Complete government budget analysis - both revenue and expenditure sides
**Coverage:** Global (200+ countries)
**Updated:** October 6, 2025

---

## PROJECT EXPANSION

**Original Scope:** Tax revenue analysis ("Gerhard")
**Expanded Scope:** Comprehensive fiscal analysis - revenues + expenditures + distributional analysis
**Goal:** Detailed government budgetary analysis tool for 200+ countries

---

## REVENUE DATA SOURCES

### 1. World Inequality Database (WID.world) - Distributional
**Status:** ✅ Downloaded (4.1 GB)
**URL:** https://wid.world/
**Coverage:** 347 countries/entities
**Detail:** Income/wealth distribution by percentile
**Time Span:** Historical (1800-2024 for some countries)
**Download:** Bulk CSV files
**Location:** `Technical/data/raw/wid/`
**Use Case:** Distributional analysis - who bears tax burden

**Key Variables:**
- Top income shares (1%, 10%, etc.)
- Wealth concentration
- Income by percentile
- Pre-tax and post-tax measures

---

### 2. US Distributional National Accounts (DINA)
**Status:** ✅ Downloaded (20 MB) + Integrated
**URL:** https://gabriel-zucman.eu/usdina/
**Coverage:** United States only
**Detail:** Most detailed tax distribution data available
**Time Span:** 1913-2020 (108 years)
**Download:** Excel files
**Location:** `Technical/data/raw/us_dina/`
**Use Case:** US tax incidence analysis - gold standard

**Data Files:**
- PSZ2022_DistributionalSeries.xlsx (4.9 MB, 127 sheets)
- PSZ2022_MacroSeries.xlsx (13.1 MB)
- PSZ2018MainData.xlsx (1.9 MB)
- PSZ_Codebook.pdf

**Detail Level:**
- All percentiles (P0-P100, Top 0.01%)
- Pre-tax and post-tax income
- Factor income, fiscal income
- Wealth distribution
- Tax rates by income level
- Federal, state, local taxes

---

### 3. OECD Revenue Statistics
**Status:** ⏳ Manual download guide created
**URL:** https://stats.oecd.org/Index.aspx?DataSetCode=REV
**Coverage:** 38 OECD countries + partners
**Detail:** Tax structure by type
**Time Span:** 1965-present
**Download:** Manual or API (automated failed - 404)
**Location:** `Technical/data/raw/oecd/` (guide created)

**Tax Categories (OECD Classification):**
- 1000: Taxes on income, profits, and capital gains
  - 1100: Individuals
  - 1200: Corporations
- 2000: Social security contributions
- 3000: Taxes on payroll and workforce
- 4000: Taxes on property
- 5000: Taxes on goods and services
  - 5110: VAT
  - 5121: Excise
- 6000: Other taxes

**Metrics:**
- As % of GDP
- As % of total tax revenue
- Per capita
- National currency

---

### 4. IMF World Revenue Longitudinal Data (WoRLD)
**Status:** 🔜 To download
**URL:** https://data.imf.org/
**Coverage:** ~200 countries
**Detail:** Tax revenue by category
**Time Span:** Historical series
**Download:** API available

**Categories:**
- Direct taxes
- Indirect taxes
- Social contributions
- Other revenue

---

### 5. World Bank Tax Revenue Data
**Status:** ✅ Already in project (202 countries)
**URL:** https://data.worldbank.org/
**Coverage:** 202 countries
**Detail:** Tax revenue (% of GDP)
**Time Span:** Historical
**Download:** API or CSV
**Location:** Already integrated in country directories

---

## EXPENDITURE DATA SOURCES

### 6. IMF Government Finance Statistics (GFS)
**Status:** 🔜 To download - HIGH PRIORITY
**URL:** https://data.imf.org/
**New Platform:** Launched August 31, 2025 (replaced legacydata.imf.org)
**Coverage:** 190+ countries
**Detail:** Complete government operations
**Time Span:** Historical (varies by country)
**Download:** SDMX API (2.1 and 3.0)
**Format:** JSON, XML, CSV

**What GFS Includes:**

**Revenue Side:**
- Taxes
- Social contributions
- Grants
- Other revenue

**Expenditure Side:**
- Expense by economic classification
- Expense by functional classification (COFOG)
- Compensation of employees
- Use of goods and services
- Consumption of fixed capital
- Interest
- Subsidies
- Grants
- Social benefits
- Other expenses

**Additional:**
- Transactions in assets and liabilities
- Balance sheet (stocks)
- Cash flow statements
- Debt statistics

**Classification Systems:**
- GFSM 2014 (Government Finance Statistics Manual)
- Economic classification
- Functional classification (COFOG)
- Institutional sectors

**API Access:**
- SDMX 2.1: Standard queries
- SDMX 3.0: Enhanced features
- JSON, XML, CSV formats
- Swagger API explorer

**Contact:** datahelp@imf.org

---

### 7. OECD Government Expenditure by Function (COFOG)
**Status:** 🔜 To download - HIGH PRIORITY
**URL:** https://data-explorer.oecd.org/ (Table 11)
**Platform:** OECD Data Explorer (replaced OECD.Stat in May 2024)
**Coverage:** 38 OECD countries + partners
**Detail:** Functional classification of government spending
**Time Span:** 1995+ (varies by country)
**Download:** Data Explorer or API

**COFOG Divisions (Level I - 10 main categories):**
1. **General public services** (01)
   - Executive and legislative organs
   - Public debt transactions
   - Foreign economic aid
   - General services

2. **Defence** (02)
   - Military defence
   - Civil defence
   - Foreign military aid

3. **Public order and safety** (03)
   - Police services
   - Fire protection
   - Law courts
   - Prisons

4. **Economic affairs** (04)
   - General economic, commercial, and labor affairs
   - Agriculture, forestry, fishing, and hunting
   - Fuel and energy
   - Mining, manufacturing, and construction
   - Transport
   - Communication
   - Other industries
   - R&D economic affairs

5. **Environmental protection** (05)
   - Waste management
   - Waste water management
   - Pollution abatement
   - Protection of biodiversity and landscape
   - R&D environmental protection

6. **Housing and community amenities** (06)
   - Housing development
   - Community development
   - Water supply
   - Street lighting

7. **Health** (07)
   - Medical products, appliances and equipment
   - Outpatient services
   - Hospital services
   - Public health services
   - R&D health

8. **Recreation, culture and religion** (08)
   - Recreational and sporting services
   - Cultural services
   - Broadcasting and publishing services
   - Religious and other community services

9. **Education** (09)
   - Pre-primary and primary education
   - Secondary education
   - Post-secondary non-tertiary education
   - Tertiary education
   - Education not definable by level
   - Subsidiary services to education
   - R&D education

10. **Social protection** (10)
    - Sickness and disability
    - Old age
    - Survivors
    - Family and children
    - Unemployment
    - Housing
    - Social exclusion
    - R&D social protection
    - Social protection n.e.c.

**COFOG Groups (Level II):**
- Further breakdown of each division
- Compulsory from 2001 onwards for EU countries
- Example: Health (07) breaks down into:
  - 07.1 Medical products, appliances and equipment
  - 07.2 Outpatient services
  - 07.3 Hospital services
  - 07.4 Public health services
  - 07.5 R&D health
  - 07.6 Health n.e.c.

**Metrics:**
- National currency
- % of GDP
- % of total government expenditure
- Per capita

---

### 8. Eurostat Government Finance Statistics
**Status:** 🔜 To download - HIGH PRIORITY (EU countries)
**URL:** https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp
**Coverage:** 27 EU member states + some non-EU European countries
**Detail:** COFOG functional classification
**Time Span:** 1995+ (Level I), 2001+ (Level II)
**Download:** Eurostat Data Browser

**Data Collection:**
- Based on ESA 2010 (European System of Accounts)
- Table 1100: Expenditure by function
- Submitted 11 months after reference year
- Most recent: 2023 (as of March 2025)

**Classification:**
- COFOG Level I (divisions): Compulsory from 1995
- COFOG Level II (groups): Compulsory from 2001
- General government + subsectors

**Subsectors:**
- Central government
- State government (federal countries)
- Local government
- Social security funds

**Metrics:**
- Million euros
- Million national currency
- % of GDP
- % of total expenditure
- Per capita

---

### 9. World Bank Government Expenditure Data
**Status:** 🔜 To download
**URL:** https://data.worldbank.org/
**Coverage:** 200+ countries
**Detail:** Aggregate expenditure + sectoral
**Time Span:** Historical
**Download:** API or Bulk CSV

**Key Indicators:**
- General government final consumption expenditure (% of GDP)
- General government final consumption expenditure (current US$)
- Government expenditure on education (% of GDP)
- Military expenditure (% of GDP)
- Health expenditure (% of GDP)

**API Access:**
- Indicators API
- Country API
- Bulk downloads available
- Documentation: datahelpdesk.worldbank.org

---

### 10. OECD Social Expenditure Database (SOCX)
**Status:** 🔜 To download (specialized)
**URL:** https://www.oecd.org/social/expenditure.htm
**Coverage:** OECD countries
**Detail:** Social protection spending
**Time Span:** 1980-present
**Download:** OECD Data Explorer

**Categories:**
- Old age
- Survivors
- Incapacity-related benefits
- Health
- Family
- Active labor market programs
- Unemployment
- Housing
- Other social policy areas

**Metrics:**
- Public and private social expenditure
- % of GDP
- Per capita

---

### 11. Our World in Data - Government Spending
**Status:** 🔜 To explore (visualization + historical)
**URL:** https://ourworldindata.org/government-spending
**Coverage:** Historical + global
**Detail:** Long-run perspective
**Time Span:** 1800s-present (varies)
**Download:** GitHub or direct CSV

**Unique Value:**
- Very long historical series
- Visualization-ready
- Curated from multiple sources
- Comparative analysis

---

## ADDITIONAL SPECIALIZED SOURCES

### 12. National Budget Documents
**Status:** 🔜 To catalog (country-specific)
**Coverage:** Individual countries
**Detail:** Most detailed available
**Time Span:** Current + recent historical
**Download:** Manual (PDFs, Excel)

**Examples:**
- **US:** usaspending.gov, OMB, Treasury
- **UK:** gov.uk budget documents
- **France:** budget.gouv.fr
- **Germany:** bundeshaushalt.de
- **Japan:** MOF Japan
- **Canada:** budget.gc.ca

**Detail Level:**
- Line-item budgets
- Program-based budgeting
- Multi-year frameworks
- Performance budgets

---

### 13. Historical Fiscal Data Collections
**Status:** 🔜 To research
**Coverage:** Long-run historical
**Detail:** Varies
**Time Span:** Centuries for some countries

**Sources:**
- Mauro et al. "A Modern History of Fiscal Prudence and Profligacy" (IMF)
- Reinhart & Rogoff historical public debt database
- OECD long-term government debt statistics
- Academic compilations
- Central bank historical statistics

---

## DATA TAXONOMIES & CLASSIFICATIONS

### COFOG (Classification of Functions of Government)
**Official:** UN Classification
**Levels:** 2 (Divisions and Groups)
**Main Use:** Functional classification of expenditure
**Coverage:** 10 main divisions, 60+ groups

### GFS (Government Finance Statistics)
**Official:** IMF GFSM 2014
**Framework:** Flows and stocks
**Classifications:**
- Economic (by type of transaction)
- Functional (COFOG)
- Institutional (by sector)

### ESA 2010 (European System of Accounts)
**Official:** European Union
**Use:** EU government finance statistics
**Alignment:** Compatible with SNA 2008, GFSM 2014

### SNA 2008 (System of National Accounts)
**Official:** UN
**Scope:** Complete national accounts framework
**Government Sector:** Subsector of national accounts

---

## INTEGRATION PLAN

### Phase 1: Revenue Enhancement (In Progress)
- [x] WID.world distributional data
- [x] US DINA integration
- [x] OECD tax revenue (manual guide created)
- [ ] IMF WoRLD revenue data
- [ ] Complete OECD tax structure download

### Phase 2: Core Expenditure Data (Next)
- [ ] IMF GFS expenditure (economic + functional)
- [ ] OECD COFOG data
- [ ] Eurostat expenditure (EU countries)
- [ ] World Bank expenditure indicators

### Phase 3: Specialized Expenditure (Follow-up)
- [ ] OECD SOCX (social spending)
- [ ] Sectoral spending (education, health, defense)
- [ ] Subnational expenditure (where available)

### Phase 4: Integration & Analysis
- [ ] Create unified fiscal database (revenue + expenditure)
- [ ] Calculate fiscal balances
- [ ] Spending efficiency analysis
- [ ] Distributional incidence (revenue + expenditure)
- [ ] Fiscal sustainability indicators

### Phase 5: Reporting
- [ ] Update country profiles with expenditure
- [ ] Create expenditure visualizations
- [ ] Generate fiscal analysis reports
- [ ] Comparative fiscal analysis

---

## DATA ARCHITECTURE

### Directory Structure (Proposed)
```
Technical/data/raw/
├── wid/                    (✅ Downloaded, 4.1 GB)
├── us_dina/                (✅ Downloaded, 20 MB)
├── oecd/
│   ├── revenue/            (Guide created)
│   ├── expenditure_cofog/  (To download)
│   └── socx/               (To download)
├── imf/
│   ├── gfs/                (To download - priority)
│   └── world/              (To download)
├── worldbank/
│   ├── revenue/            (Already integrated)
│   └── expenditure/        (To download)
├── eurostat/
│   └── gfs/                (To download)
└── historical/             (To research)

Technical/data/processed/
├── revenue/
│   ├── tax_revenue/        (Existing)
│   ├── distributional/     (WID, DINA)
│   └── by_country/
├── expenditure/
│   ├── cofog/              (Functional)
│   ├── economic/           (Economic classification)
│   └── by_country/
└── fiscal/
    ├── balance/
    ├── sustainability/
    └── comparative/

Countries/{COUNTRY_CODE}/
├── Output/
│   └── Data/
│       ├── revenue/        (Existing + enhanced)
│       ├── expenditure/    (New)
│       └── fiscal/         (New - balance, ratios)
└── Technical/
```

---

## KEY METRICS TO CALCULATE

### Revenue Metrics (Existing + Enhanced)
- Tax revenue (% GDP)
- Tax structure (by type)
- Tax progressivity
- Distributional tax incidence

### Expenditure Metrics (New)
- Total expenditure (% GDP)
- Functional composition (COFOG)
- Economic composition
- Social spending
- Capital vs current
- Expenditure efficiency

### Fiscal Balance Metrics (New)
- Overall balance (% GDP)
- Primary balance (% GDP)
- Structural balance
- Cyclically-adjusted balance
- Debt-to-GDP ratio
- Deficit financing

### Distributional Fiscal Incidence (Advanced)
- Net fiscal incidence (taxes - transfers)
- Progressivity of total fiscal system
- Redistribution coefficient
- Who benefits from spending?

---

## PRIORITY SEQUENCE

### Immediate (Next 2-4 hours)
1. Download IMF GFS data (revenue + expenditure)
2. Download OECD COFOG data
3. Download Eurostat GFS (EU countries)
4. Create taxonomy documentation (COFOG detailed)

### Short-term (Today/Tomorrow)
5. Download World Bank expenditure data
6. Integrate expenditure into country directories
7. Create expenditure visualization scripts
8. Calculate fiscal balances

### Medium-term (This Week)
9. Download OECD SOCX
10. Add sectoral detail (health, education, defense)
11. Create fiscal analysis tools
12. Generate expenditure reports

### Long-term (Ongoing)
13. Historical data collection
14. Subnational expenditure
15. National budget integration
16. Advanced distributional analysis

---

## NOTES

**Platform Changes to Note:**
- IMF: New data.imf.org platform (Aug 31, 2025)
- OECD: Data Explorer replaced OECD.Stat (May 2024)
- World Bank: API v2 current
- Eurostat: 2023 data most recent (as of March 2025)

**API Access:**
- IMF: SDMX 2.1 and 3.0
- OECD: Data Explorer API
- World Bank: Indicators API v2
- Eurostat: Data Browser export

**Data Quality:**
- IMF GFS: Gold standard for government finance
- OECD: Highly detailed for member countries
- Eurostat: Most detailed for EU
- World Bank: Broadest coverage but less detail

**Challenges:**
- Different classifications (harmonization needed)
- Different country coverage
- Varying time spans
- Data lags (11+ months for official statistics)
- Subnational data limited

---

## CONTACT & SUPPORT

**IMF GFS:** datahelp@imf.org
**OECD:** stats.contact@oecd.org
**Eurostat:** estat-user-support@ec.europa.eu
**World Bank:** data@worldbank.org

---

**Document Created:** October 6, 2025
**Status:** Living document - updated as sources added
**Next Update:** After Phase 1 revenue enhancement complete
