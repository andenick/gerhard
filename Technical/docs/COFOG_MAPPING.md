# World Bank Indicators to COFOG Framework Mapping

**Created**: October 10, 2025
**Project**: Gerhard - Fiscal Analysis
**Purpose**: Map World Bank expenditure indicators to COFOG (Classification of the Functions of Government) framework

---

## Overview

The COFOG framework provides a standardized classification of government expenditure by function. This document maps World Bank Open Data indicators to COFOG divisions to enable cross-country comparative analysis.

---

## COFOG Framework Structure

### 10 Main Divisions

1. **General Public Services** (01)
2. **Defence** (02)
3. **Public Order and Safety** (03)
4. **Economic Affairs** (04)
5. **Environmental Protection** (05)
6. **Housing and Community Amenities** (06)
7. **Health** (07)
8. **Recreation, Culture and Religion** (08)
9. **Education** (09)
10. **Social Protection** (10)

---

## World Bank to COFOG Mapping

### Available Indicators in Dataset

| World Bank Indicator | WB Code | COFOG Division | COFOG Code | Coverage | Mapping Quality |
|---------------------|---------|----------------|------------|----------|-----------------|
| **Total Government Expenditure** | `NE.CON.GOVT.ZS` | *Aggregate* | N/A | 10,894 obs | ⭐⭐⭐⭐⭐ Exact |
| **Education Expenditure** | `SE.XPD.TOTL.GD.ZS` | Education | 09 | 6,378 obs | ⭐⭐⭐⭐⭐ Exact |
| **Health Expenditure** | `SH.XPD.GHED.GD.ZS` | Health | 07 | 5,450 obs | ⭐⭐⭐⭐⭐ Exact |
| **Military Expenditure** | `MS.MIL.XPND.GD.ZS` | Defence | 02 | 10,382 obs | ⭐⭐⭐⭐⭐ Exact |
| **R&D Expenditure** | `GB.XPD.RSDV.GD.ZS` | Economic Affairs | 04 | 3,062 obs | ⭐⭐⭐⭐ Good |
| **Social Safety Net Adequacy** | `per_sa_allsa.adq_pop_tot` | Social Protection | 10 | 479 obs | ⭐⭐⭐ Fair |

---

## Detailed Mapping

### 1. Total Government Expenditure → Aggregate (All COFOG)

**World Bank Indicator**: `NE.CON.GOVT.ZS`
**Full Name**: General government final consumption expenditure (% of GDP)
**COFOG Mapping**: Sum of all 10 divisions
**Coverage**: 227 countries, 1960-2024

**Definition**: Total government consumption expenditure including:
- Compensation of employees
- Intermediate consumption
- Social transfers in kind
- Depreciation
- Minus: market output and payments for non-market output

**Note**: This is **not** total government spending (which includes transfers, interest, subsidies). This is government **consumption** only.

---

### 2. Education Expenditure → COFOG Division 09

**World Bank Indicator**: `SE.XPD.TOTL.GD.ZS`
**Full Name**: Government expenditure on education, total (% of GDP)
**COFOG Mapping**: Division 09 - Education
**Coverage**: 247 countries, 1970-2024

**Includes**:
- Pre-primary and primary education (09.1)
- Secondary education (09.2)
- Post-secondary non-tertiary education (09.3)
- Tertiary education (09.4)
- Education not definable by level (09.5)
- Subsidiary services to education (09.6)
- R&D Education (09.7)
- Education n.e.c. (09.8)

**Mapping Quality**: ⭐⭐⭐⭐⭐ **Exact match**
World Bank definition aligns perfectly with COFOG Division 09.

**Available Metrics**:
- `education_expenditure` - % of GDP
- `education_expenditure_govt` - % of total government expenditure

---

### 3. Health Expenditure → COFOG Division 07

**World Bank Indicator**: `SH.XPD.GHED.GD.ZS`
**Full Name**: Domestic general government health expenditure (% of GDP)
**COFOG Mapping**: Division 07 - Health
**Coverage**: 237 countries, 2000-2023

**Includes**:
- Medical products, appliances and equipment (07.1)
- Outpatient services (07.2)
- Hospital services (07.3)
- Public health services (07.4)
- R&D Health (07.5)
- Health n.e.c. (07.6)

**Mapping Quality**: ⭐⭐⭐⭐⭐ **Exact match**
WHO/World Bank definition aligns with COFOG Division 07.

**Available Metrics**:
- `health_expenditure` - % of GDP
- `health_expenditure_govt` - % of total government expenditure

---

### 4. Military Expenditure → COFOG Division 02

**World Bank Indicator**: `MS.MIL.XPND.GD.ZS`
**Full Name**: Military expenditure (% of GDP)
**COFOG Mapping**: Division 02 - Defence
**Coverage**: 208 countries, 1960-2023
**Source**: Stockholm International Peace Research Institute (SIPRI)

**Includes**:
- Military defence (02.1)
- Civil defence (02.2)
- Foreign military aid (02.3)
- R&D Defence (02.4)
- Defence n.e.c. (02.5)

**SIPRI Definition**: All expenditure on:
- Armed forces (army, navy, air force, space force)
- Defence ministries and agencies
- Paramilitary forces (when trained for military operations)
- Military R&D, procurement, and operations

**Mapping Quality**: ⭐⭐⭐⭐⭐ **Exact match**
SIPRI definition aligns with COFOG Division 02.

---

### 5. R&D Expenditure → COFOG Division 04 (Partial)

**World Bank Indicator**: `GB.XPD.RSDV.GD.ZS`
**Full Name**: Research and development expenditure (% of GDP)
**COFOG Mapping**: Division 04 - Economic Affairs (partial)
**Coverage**: 191 countries, 1996-2023

**COFOG Placement**:
- Economic Affairs R&D (04.7) - **Primary mapping**
- Also appears in: Defence (02.4), Health (07.5), Education (09.7)

**Includes**:
- Government-funded R&D
- University research
- National laboratories
- Innovation programs

**Mapping Quality**: ⭐⭐⭐⭐ **Good match**
R&D spending spans multiple COFOG divisions. World Bank aggregate maps primarily to Economic Affairs R&D (04.7), but may include R&D from other divisions.

**Limitation**: Cannot disaggregate by COFOG division without additional data.

---

### 6. Social Protection → COFOG Division 10 (Partial)

**World Bank Indicator**: `per_sa_allsa.adq_pop_tot`
**Full Name**: Adequacy of social safety net programs (% of total welfare of beneficiary households)
**COFOG Mapping**: Division 10 - Social Protection (indicator, not expenditure)
**Coverage**: 107 countries, 2000-2023

**COFOG Division 10 Includes**:
- Sickness and disability (10.1)
- Old age (10.2)
- Survivors (10.3)
- Family and children (10.4)
- Unemployment (10.5)
- Housing (10.6)
- Social exclusion n.e.c. (10.7)
- R&D Social protection (10.8)
- Social protection n.e.c. (10.9)

**Mapping Quality**: ⭐⭐⭐ **Fair match**
This is an **adequacy indicator**, not expenditure. Measures effectiveness, not spending levels.

**Limitation**: Does not provide total social protection expenditure as % GDP.

---

## Missing COFOG Divisions in World Bank Data

The following COFOG divisions are **NOT directly available** in the World Bank Open Data indicators:

### Division 01: General Public Services
- Executive and legislative organs
- Financial and fiscal affairs
- Foreign affairs
- Public debt transactions
- **Alternative**: Can be estimated as residual (Total - Sum of other divisions)

### Division 03: Public Order and Safety
- Police services
- Fire protection
- Law courts
- Prisons
- **No World Bank equivalent**

### Division 05: Environmental Protection
- Waste management
- Pollution abatement
- Protection of biodiversity
- **Limited World Bank coverage** (project-specific data only)

### Division 06: Housing and Community Amenities
- Housing development
- Water supply
- Street lighting
- **Limited World Bank coverage** (urbanization data separate)

### Division 08: Recreation, Culture and Religion
- Recreational and sporting services
- Cultural services
- Broadcasting and publishing services
- Religious and other community services
- **No World Bank equivalent**

---

## Data Availability by Country

### Tier 1: Complete Coverage (4+ indicators)
**Countries**: 150+ countries with education, health, military, and total expenditure

**Available COFOG Divisions**:
- ✅ Total (Aggregate)
- ✅ Education (09)
- ✅ Health (07)
- ✅ Defence (02)

### Tier 2: Partial Coverage (2-3 indicators)
**Countries**: 50+ countries with total, education, or health only

**Typical Pattern**: Developing countries with limited reporting

### Tier 3: Minimal Coverage (1 indicator)
**Countries**: 20+ countries with total expenditure only

---

## Using COFOG Mapping for Analysis

### Sectoral Expenditure Analysis

For countries with complete data, you can analyze spending priorities:

```python
import pandas as pd

# Load country expenditure data
df = pd.read_excel('Countries/US/Output/Data/us_government_expenditure.xlsx')

# Calculate sectoral shares
df['education_share'] = df['Education_Expenditure_GDP'] / df['Total_Govt_Expenditure_GDP'] * 100
df['health_share'] = df['Health_Expenditure_GDP'] / df['Total_Govt_Expenditure_GDP'] * 100
df['military_share'] = df['Military_Expenditure_GDP'] / df['Total_Govt_Expenditure_GDP'] * 100

# Remaining (General Public Services + others)
df['other_share'] = 100 - df['education_share'] - df['health_share'] - df['military_share']
```

### Cross-Country Comparison

Compare functional spending priorities:

```python
# Get latest year for all countries
latest_year = 2023

countries_to_compare = ['US', 'GB', 'FR', 'DE', 'JP']

comparison = []
for code in countries_to_compare:
    data = pd.read_excel(f'Countries/{code}/Output/Data/{code.lower()}_government_expenditure.xlsx')
    latest = data[data['Year'] == latest_year].iloc[0]
    comparison.append({
        'Country': latest['Country'],
        'Education': latest['Education_Expenditure_GDP'],
        'Health': latest['Health_Expenditure_GDP'],
        'Military': latest['Military_Expenditure_GDP']
    })

comparison_df = pd.DataFrame(comparison)
```

---

## Completeness Assessment

### What We Have
✅ **5 COFOG divisions** directly mapped (02, 04, 07, 09, 10)
✅ **Total expenditure** for comparison
✅ **164 countries** with integrated data
✅ **65-year time series** (1960-2024) for many countries

### What's Missing
❌ **5 COFOG divisions** not available (01, 03, 05, 06, 08)
❌ Represents ~40-50% of total government expenditure
❌ Includes critical functions: public administration, police, courts

### Gap Filling Strategies

1. **IMF GFS Database**: Download COFOG data for OECD+ countries
2. **Eurostat**: Full 10-division COFOG for EU countries
3. **OECD Statistics**: Complete COFOG for 38 member countries
4. **Residual Calculation**: Other = Total - (Education + Health + Military + R&D)

---

## Next Steps

### Immediate
1. ✅ Document World Bank → COFOG mapping (this file)
2. ⏳ Download IMF COFOG database for missing divisions
3. ⏳ Download Eurostat full COFOG for EU countries
4. ⏳ Create combined dataset with all available indicators

### Short-term
5. Map sectoral budget data from fiscal event countries (Nigeria, Kenya, Pakistan)
6. Create COFOG equivalence tables for non-standard classifications
7. Generate cross-country spending priority analysis

### Long-term
8. Build complete 10-division COFOG dataset for Tier 1 countries
9. Estimate missing divisions using statistical methods
10. Create functional expenditure database (1990-2024)

---

## References

### COFOG Framework
- **UN Statistics Division**: https://unstats.un.org/unsd/classifications/Family/Detail/4
- **IMF GFS Manual 2014**: Chapter 6 - Classification of Functions of Government
- **Eurostat COFOG**: https://ec.europa.eu/eurostat/web/government-finance-statistics/methodology

### Data Sources
- **World Bank Open Data**: https://data.worldbank.org/
- **IMF GFS**: https://data.imf.org/
- **OECD Statistics**: https://stats.oecd.org/
- **Eurostat**: https://ec.europa.eu/eurostat/

---

## Appendix: COFOG Complete Structure

### Division 01: General Public Services
- 01.1 Executive and legislative organs, financial and fiscal affairs, external affairs
- 01.2 Foreign economic aid
- 01.3 General services
- 01.4 Basic research
- 01.5 R&D General public services
- 01.6 General public services n.e.c.
- 01.7 Public debt transactions
- 01.8 Transfers of a general character between different levels of government

### Division 02: Defence
- 02.1 Military defence
- 02.2 Civil defence
- 02.3 Foreign military aid
- 02.4 R&D Defence
- 02.5 Defence n.e.c.

### Division 03: Public Order and Safety
- 03.1 Police services
- 03.2 Fire-protection services
- 03.3 Law courts
- 03.4 Prisons
- 03.5 R&D Public order and safety
- 03.6 Public order and safety n.e.c.

### Division 04: Economic Affairs
- 04.1 General economic, commercial and labour affairs
- 04.2 Agriculture, forestry, fishing and hunting
- 04.3 Fuel and energy
- 04.4 Mining, manufacturing and construction
- 04.5 Transport
- 04.6 Communication
- 04.7 Other industries
- 04.8 R&D Economic affairs
- 04.9 Economic affairs n.e.c.

### Division 05: Environmental Protection
- 05.1 Waste management
- 05.2 Waste water management
- 05.3 Pollution abatement
- 05.4 Protection of biodiversity and landscape
- 05.5 R&D Environmental protection
- 05.6 Environmental protection n.e.c.

### Division 06: Housing and Community Amenities
- 06.1 Housing development
- 06.2 Community development
- 06.3 Water supply
- 06.4 Street lighting
- 06.5 R&D Housing and community amenities
- 06.6 Housing and community amenities n.e.c.

### Division 07: Health
- 07.1 Medical products, appliances and equipment
- 07.2 Outpatient services
- 07.3 Hospital services
- 07.4 Public health services
- 07.5 R&D Health
- 07.6 Health n.e.c.

### Division 08: Recreation, Culture and Religion
- 08.1 Recreational and sporting services
- 08.2 Cultural services
- 08.3 Broadcasting and publishing services
- 08.4 Religious and other community services
- 08.5 R&D Recreation, culture and religion
- 08.6 Recreation, culture and religion n.e.c.

### Division 09: Education
- 09.1 Pre-primary and primary education
- 09.2 Secondary education
- 09.3 Post-secondary non-tertiary education
- 09.4 Tertiary education
- 09.5 Education not definable by level
- 09.6 Subsidiary services to education
- 09.7 R&D Education
- 09.8 Education n.e.c.

### Division 10: Social Protection
- 10.1 Sickness and disability
- 10.2 Old age
- 10.3 Survivors
- 10.4 Family and children
- 10.5 Unemployment
- 10.6 Housing
- 10.7 Social exclusion n.e.c.
- 10.8 R&D Social protection
- 10.9 Social protection n.e.c.

---

**Document Status**: ✅ Complete
**Last Updated**: October 10, 2025
**Next Review**: When IMF/OECD/Eurostat data integrated
