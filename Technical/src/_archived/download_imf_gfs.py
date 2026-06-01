"""
Download IMF Government Finance Statistics (GFS)
Complete government revenue and expenditure data for 190+ countries

Project: Gerhard - Expenditure Data Collection
"""

import requests
import pandas as pd
from pathlib import Path
import logging
import time
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DATA_DIR = BASE_DIR / "Technical" / "data" / "raw" / "imf" / "gfs"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


class IMFGFSDownloader:
    """Download IMF Government Finance Statistics"""

    def __init__(self):
        self.base_url = "https://data.imf.org"
        self.api_url = "https://www.imf.org/external/datamapper/api/v1"
        self.session = requests.Session()

    def attempt_datamapper_download(self):
        """Try to download from IMF DataMapper"""
        logger.info("=" * 60)
        logger.info("Attempting IMF DataMapper Download")
        logger.info("=" * 60)

        # IMF DataMapper endpoints for fiscal data
        endpoints = {
            'government_revenue': f"{self.api_url}/REVENUE",
            'government_expenditure': f"{self.api_url}/exp@FPP",
            'fiscal_balance': f"{self.api_url}/BALANCE",
        }

        for name, url in endpoints.items():
            try:
                logger.info(f"\nTrying: {name}")
                logger.info(f"URL: {url}")

                response = self.session.get(url, timeout=60)

                if response.status_code == 200:
                    # Try to parse as JSON
                    try:
                        data = response.json()
                        output_file = RAW_DATA_DIR / f"imf_{name}.json"
                        with open(output_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        logger.info(f"✅ Downloaded: {output_file.name}")
                        return True
                    except:
                        # If not JSON, save as text
                        output_file = RAW_DATA_DIR / f"imf_{name}.txt"
                        with open(output_file, 'wb') as f:
                            f.write(response.content)
                        logger.info(f"✅ Downloaded (text): {output_file.name}")
                else:
                    logger.warning(f"Status code: {response.status_code}")

            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        return False

    def attempt_bulk_csv_download(self):
        """Try various CSV download endpoints"""
        logger.info("\n" + "=" * 60)
        logger.info("Attempting Bulk CSV Download")
        logger.info("=" * 60)

        # Possible CSV endpoints
        csv_urls = [
            "https://data.imf.org/api/dataset/GFS",
            "https://data.imf.org/api/download/GFS",
            "https://www.imf.org/external/datamapper/datasets/GFS",
        ]

        for url in csv_urls:
            try:
                logger.info(f"\nTrying: {url}")
                response = self.session.get(url, timeout=60)

                if response.status_code == 200 and len(response.content) > 1000:
                    output_file = RAW_DATA_DIR / "imf_gfs_bulk.csv"
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"✅ Downloaded: {output_file.name}")
                    logger.info(f"   Size: {len(response.content) / 1024 / 1024:.1f} MB")
                    return True
                else:
                    logger.warning(f"Status code: {response.status_code}")

            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        return False

    def create_manual_download_guide(self):
        """Create comprehensive guide for manual IMF GFS download"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Manual Download Guide")
        logger.info("=" * 60)

        guide = """# IMF Government Finance Statistics (GFS) - Manual Download Guide

**Updated:** October 6, 2025
**New Platform:** data.imf.org (launched August 31, 2025)

---

## WHAT IS GFS?

IMF Government Finance Statistics provides comprehensive government fiscal data:
- **Revenue** (taxes, social contributions, grants, other)
- **Expenditure** (by economic classification and COFOG functional classification)
- **Assets and Liabilities** (balance sheets)
- **Cash flow statements**
- **Debt statistics**

**Coverage:** 190+ countries
**Time Span:** Historical series (varies by country)
**Update Frequency:** Annual, with some quarterly data
**Classification:** GFSM 2014 (Government Finance Statistics Manual 2014)

---

## DOWNLOAD METHODS

### Option 1: IMF Data Portal (Recommended)

**URL:** https://data.imf.org/

**Steps:**
1. Navigate to https://data.imf.org/
2. Search for "Government Finance Statistics" or "GFS"
3. Select the dataset:
   - "Government Finance Statistics" (main dataset)
   - Filter by country, indicator, time period
4. Click "Export" or "Download"
5. Choose format: CSV, Excel, SDMX
6. Save to: `Technical/data/raw/imf/gfs/`

**What to Download:**

For each country, try to get:
- **Revenue**
  - Total revenue (% GDP)
  - Tax revenue
  - Social contributions
  - Grants
  - Other revenue

- **Expenditure**
  - Total expenditure (% GDP)
  - Expense by economic classification:
    * Compensation of employees
    * Use of goods and services
    * Interest
    * Subsidies
    * Grants
    * Social benefits
    * Other expenses
  - Expense by functional classification (COFOG):
    * General public services
    * Defence
    * Public order and safety
    * Economic affairs
    * Environmental protection
    * Housing and community amenities
    * Health
    * Recreation, culture, religion
    * Education
    * Social protection

- **Balance**
  - Net operating balance
  - Net lending/borrowing
  - Primary balance

- **Assets and Liabilities**
  - Debt securities
  - Loans
  - Currency and deposits

### Option 2: IMF API (For Developers)

**URL:** https://data.imf.org/en/Resource-Pages/IMF-API
**Swagger Documentation:** https://portal.api.imf.org/apis

**Requirements:**
- Beta portal account (sign up at portal.api.imf.org)
- API supports SDMX 2.1 and SDMX 3.0

**Formats:**
- JSON
- XML
- CSV (via conversion)

**Example API Call:**
```
https://data.imf.org/api/v1/data/GFS/{country_code}/{indicator}?time_period={year}
```

**Programming Languages Supported:**
- Python
- R
- MATLAB
- Stata

**Contact for API Help:** datahelp@imf.org

### Option 3: IMF DataMapper

**URL:** https://www.imf.org/external/datamapper/

**Available Datasets:**
- Government Revenue
- Government Expenditure
- Fiscal Balance
- General Government Gross Debt

**Steps:**
1. Visit IMF DataMapper
2. Select fiscal indicators
3. Choose countries and time period
4. Download as Excel or CSV

**Note:** DataMapper has subset of GFS, not complete database

### Option 4: IMF Publications

**GFS Yearbook:**
- Published annually
- Contains detailed tables for all countries
- Available as PDF
- URL: https://www.imf.org/en/Publications/GFSY

**How to use:**
1. Download latest GFS Yearbook PDF
2. Extract tables (manually or using PDF parser)
3. Country tables contain complete fiscal accounts

---

## DATA STRUCTURE

### Economic Classification of Expenditure

**Main Categories:**
- **2** = Expense (current spending)
  - **21** = Compensation of employees
  - **22** = Use of goods and services
  - **24** = Interest
  - **25** = Subsidies
  - **26** = Grants
  - **27** = Social benefits
  - **28** = Other expense
- **31** = Net acquisition of nonfinancial assets (capital spending)

### Functional Classification (COFOG)

**Divisions:**
- **701** = General public services
- **702** = Defence
- **703** = Public order and safety
- **704** = Economic affairs
- **705** = Environmental protection
- **706** = Housing and community amenities
- **707** = Health
- **708** = Recreation, culture and religion
- **709** = Education
- **710** = Social protection

### Revenue Classification

**Main Categories:**
- **11** = Taxes
  - **111** = Taxes on income, profits, and capital gains
  - **114** = Taxes on property
  - **115** = Taxes on goods and services
  - **116** = Taxes on international trade
- **12** = Social contributions
- **13** = Grants
- **14** = Other revenue

---

## PRIORITY COUNTRIES

**Tier 1 (Highest Detail Available):**
- OECD countries (38 countries)
- EU member states (27 countries)
- Large emerging markets (China, India, Brazil, Russia, etc.)

**Tier 2:**
- Other G20 countries
- Large developing economies

**Tier 3:**
- All other reporting countries

---

## FILE NAMING CONVENTION

When downloading manually, use this naming:

```
imf_gfs_{country_iso3}_{category}_{year_start}_{year_end}.csv

Examples:
- imf_gfs_USA_revenue_1990_2024.csv
- imf_gfs_USA_expenditure_cofog_1990_2024.csv
- imf_gfs_DEU_balance_1990_2024.csv
- imf_gfs_all_countries_revenue_2024.csv (if bulk)
```

Save to: `Technical/data/raw/imf/gfs/`

---

## DATA QUALITY NOTES

**Strengths:**
- Most comprehensive government finance data
- Standardized methodology (GFSM 2014)
- Long time series
- Internationally comparable

**Limitations:**
- Data lags (6-18 months)
- Not all countries report COFOG (functional classification)
- Some countries missing subsector breakdowns
- Varying levels of detail by country

**Best Coverage:**
- OECD countries: Excellent
- EU countries: Excellent (Eurostat also available)
- G20 countries: Good to Excellent
- Other countries: Varies

---

## INTEGRATION WITH PROJECT

Once downloaded, data will be integrated into:

**Revenue Side:**
- Enhance existing tax revenue data
- Add non-tax revenue
- Government grants

**Expenditure Side:**
- Total expenditure (% GDP)
- Functional classification (COFOG)
- Economic classification
- Capital vs current

**Fiscal Analysis:**
- Calculate fiscal balances
- Debt sustainability
- Expenditure efficiency
- Revenue adequacy

---

## AUTOMATION POTENTIAL

**Python Script to Create:**
```python
# Download GFS data using IMF API
# Parse SDMX format
# Extract revenue and expenditure
# Organize by country
# Save as CSV
```

**Challenges:**
- API requires account
- SDMX format complex
- May need manual downloads for some countries

**Recommendation:**
- Automated download for countries with good API access
- Manual download for others
- Combine with OECD and Eurostat for OECD/EU countries

---

## ALTERNATIVE SOURCES (If IMF Not Available)

1. **OECD National Accounts** (for OECD countries)
   - Government expenditure by function
   - URL: data-explorer.oecd.org

2. **Eurostat** (for EU countries)
   - Most detailed for EU
   - URL: ec.europa.eu/eurostat

3. **World Bank** (aggregate data)
   - Government expenditure (% GDP)
   - URL: data.worldbank.org

4. **National Sources** (most detailed)
   - Ministry of Finance websites
   - National budget documents
   - Central bank statistical databases

---

## NEXT STEPS

1. **Try automated download first:**
   - Run: `python download_imf_gfs.py`
   - Check if any data downloaded

2. **If automated fails:**
   - Visit https://data.imf.org/
   - Search "Government Finance Statistics"
   - Download manually for priority countries

3. **Priority order:**
   - Start with largest economies (US, China, EU, Japan, etc.)
   - Then OECD countries
   - Then others as time permits

4. **Complement with:**
   - OECD COFOG data (more detailed for OECD countries)
   - Eurostat (more detailed for EU)
   - National sources (most detailed)

---

## SUPPORT

**IMF Data Help:** datahelp@imf.org
**Phone:** +1 (202) 623-7000
**Documentation:** https://data.imf.org/

---

*Guide created: October 6, 2025*
*Project: Gerhard - Fiscal Expansion*
"""

        guide_file = RAW_DATA_DIR / "MANUAL_DOWNLOAD_GUIDE.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide)

        logger.info(f"✅ Guide created: {guide_file.name}")
        logger.info("")
        logger.info("📝 Manual download may be required:")
        logger.info("   See: Technical/data/raw/imf/gfs/MANUAL_DOWNLOAD_GUIDE.md")
        logger.info("")
        logger.info("Key URLs:")
        logger.info("   - Data Portal: https://data.imf.org/")
        logger.info("   - API Docs: https://data.imf.org/en/Resource-Pages/IMF-API")
        logger.info("   - DataMapper: https://www.imf.org/external/datamapper/")
        logger.info("")

    def run(self):
        """Run complete IMF GFS download attempt"""
        logger.info("IMF Government Finance Statistics Downloader")
        logger.info("")

        # Try DataMapper
        success1 = self.attempt_datamapper_download()

        # Try bulk CSV
        success2 = self.attempt_bulk_csv_download()

        if not (success1 or success2):
            logger.info("")
            logger.info("⚠️  Automated download not successful")
            logger.info("Creating manual download guide...")
            self.create_manual_download_guide()

        logger.info("")
        logger.info("=" * 60)
        logger.info("IMF GFS Download Process Complete")
        logger.info("=" * 60)


def main():
    downloader = IMFGFSDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
