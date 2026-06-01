"""
Download OECD Government Expenditure by Function (COFOG)
Detailed functional classification for OECD countries

Project: Gerhard - COFOG Functional Classification
"""

import requests
import pandas as pd
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, ensure_dir

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "oecd" / "cofog")


class OECDCOFOGDownloader:
    """Download OECD COFOG expenditure data"""

    def __init__(self):
        self.base_url = "https://sdmx.oecd.org/public/rest/data"
        self.session = requests.Session()

    def attempt_sdmx_download(self):
        """Try to download via OECD SDMX API"""
        logger.info("=" * 60)
        logger.info("Attempting OECD SDMX API Download")
        logger.info("=" * 60)

        # OECD SDMX endpoint for government expenditure by function
        # Based on Table 11 (DSD_NASEC10@DF_TABLE11) — stats.oecd.org retired May 2024
        endpoints = [
            f"{self.base_url}/OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11,/all?dimensionAtObservation=AllDimensions",
        ]

        # Request CSV format for easier processing
        headers = {'Accept': 'application/vnd.sdmx.data+csv;file=true;labels=both'}

        for endpoint in endpoints:
            try:
                logger.info(f"\nTrying endpoint: {endpoint[:80]}...")

                response = self.session.get(
                    endpoint,
                    headers=headers,
                    timeout=120
                )

                # Reject HTML error pages
                content_type = response.headers.get('Content-Type', '')
                if 'html' in content_type.lower():
                    logger.warning("Received HTML error page instead of data")
                    continue

                if response.status_code == 200:
                    # Reject suspiciously small responses
                    if len(response.content) < 1024:
                        logger.warning(f"Response too small ({len(response.content)} bytes)")
                        continue

                    output_file = RAW_DATA_DIR / "oecd_cofog_sdmx.csv"
                    with open(output_file, 'wb') as f:
                        f.write(response.content)

                    size_mb = len(response.content) / 1024 / 1024
                    logger.info(f"Downloaded: {output_file.name} ({size_mb:.1f} MB)")

                    if size_mb > 0.1:  # If meaningful data
                        return True
                else:
                    logger.warning(f"Status code: {response.status_code}")

            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        return False

    def attempt_csv_download(self):
        """Try to download CSV directly"""
        logger.info("\n" + "=" * 60)
        logger.info("Attempting Direct CSV Download")
        logger.info("=" * 60)

        # CSV endpoint via OECD SDMX API with CSV Accept header
        url = f"{self.base_url}/OECD.SDD.NAD,DSD_NASEC10@DF_TABLE11,/all"
        headers = {'Accept': 'application/vnd.sdmx.data+csv;file=true;labels=both'}

        try:
            logger.info(f"\nTrying CSV download: {url[:80]}...")
            response = self.session.get(url, headers=headers, timeout=120)

            # Reject HTML error pages
            content_type = response.headers.get('Content-Type', '')
            if 'html' in content_type.lower():
                logger.warning("Received HTML error page instead of CSV data")
                return False

            if response.status_code == 200 and len(response.content) > 1000:
                output_file = RAW_DATA_DIR / "oecd_cofog_table11.csv"
                with open(output_file, 'wb') as f:
                    f.write(response.content)

                size_mb = len(response.content) / 1024 / 1024
                logger.info(f"Downloaded: {output_file.name} ({size_mb:.1f} MB)")
                return True
            else:
                logger.warning(f"Status code: {response.status_code}, size: {len(response.content)} bytes")

        except Exception as e:
            logger.error(f"Error: {e}")

        return False

    def create_manual_download_guide(self):
        """Create comprehensive manual download guide"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Manual Download Guide")
        logger.info("=" * 60)

        guide = """# OECD Government Expenditure by Function (COFOG) - Manual Download Guide

**Updated:** October 6, 2025
**Platform:** OECD Data Explorer (replaced OECD.Stat in May 2024)
**Coverage:** 38 OECD countries + partners
**Classification:** COFOG (Classification of Functions of Government)

---

## WHAT IS THIS DATA?

OECD Table 11: Annual government expenditure by function (COFOG)

**Contains:**
- 10 COFOG divisions (Level I)
- 60+ COFOG groups (Level II, varies by country)
- General government + subsectors (central, state, local, social security)
- Time series: 1995+ (varies by country)
- Metrics: National currency, % of GDP, % of total expenditure

**COFOG 10 Main Categories:**
1. General public services
2. Defence
3. Public order and safety
4. Economic affairs
5. Environmental protection
6. Housing and community amenities
7. Health
8. Recreation, culture and religion
9. Education
10. Social protection

---

## DOWNLOAD METHOD 1: OECD Data Explorer (Recommended)

### Step-by-Step Instructions

**URL:** https://data-explorer.oecd.org/

1. **Navigate to Data Explorer:**
   - Go to https://data-explorer.oecd.org/
   - Or search for "OECD Table 11" or "COFOG"

2. **Find the Dataset:**
   - Search for "Annual government expenditure by function COFOG"
   - Or navigate to: National Accounts → Government Finance → Table 11

3. **Direct Link (if available):**
   ```
   https://data-explorer.oecd.org/vis?df[ds]=DisseminateFinalDMZ&df[id]=DSD_NASEC10@DF_TABLE11&df[ag]=OECD.SDD.NAD
   ```

4. **Select Data:**
   - **Countries:** Select all OECD countries (or specific ones)
   - **Functions (COFOG):** Select all divisions (01-10) or specific ones
   - **Sector:** General government (or subsectors if needed)
   - **Time Period:** Select all years (1995-latest)
   - **Measure:** % of GDP (recommended) or national currency

5. **Export Data:**
   - Click "Export" or "Download" button
   - Choose format: **CSV** (recommended) or Excel
   - Save to: `Technical/data/raw/oecd/cofog/`

### Recommended Exports

**Export 1: Complete Dataset**
- All countries
- All COFOG divisions (01-10)
- All years
- % of GDP
- Filename: `oecd_cofog_all_countries_pct_gdp.csv`

**Export 2: National Currency (for absolute values)**
- All countries
- All COFOG divisions
- All years
- National currency
- Filename: `oecd_cofog_all_countries_currency.csv`

**Export 3: Detailed (Level II - if available)**
- All countries
- All COFOG groups (detailed subcategories)
- All years
- % of GDP
- Filename: `oecd_cofog_detailed_level2.csv`

---

## DOWNLOAD METHOD 2: Old OECD.Stat (Legacy, if still accessible)

**Note:** OECD.Stat was switched off in May 2024, but may still have archived data.

**URL:** https://stats.oecd.org/Index.aspx?DataSetCode=SNA_TABLE11

**If accessible:**
1. Select countries, years, indicators
2. Click "Export" → CSV
3. Save to: `Technical/data/raw/oecd/cofog/`

---

## DOWNLOAD METHOD 3: OECD SDMX API (For Developers)

### API Endpoint

**Base URL:**
```
https://sdmx.oecd.org/public/rest/data/OECD,SNA_TABLE11/{country}/{function}/{year}
```

**Example:**
```
https://sdmx.oecd.org/public/rest/data/OECD,SNA_TABLE11/USA+GBR+DEU/01+02+03+04+05+06+07+08+09+10/2010-2023
```

**Parameters:**
- `{country}`: Three-letter country codes (USA, GBR, DEU, etc.)
- `{function}`: COFOG codes (01-10 for divisions)
- `{year}`: Time period

**Response Format:** SDMX-JSON or SDMX-XML

**Headers:**
```
Accept: application/vnd.sdmx.data+json;version=1.0.0
```

### Python Example

```python
import requests
import pandas as pd

url = "https://sdmx.oecd.org/public/rest/data/OECD,SNA_TABLE11/all"
headers = {'Accept': 'application/vnd.sdmx.data+json;version=1.0.0'}

response = requests.get(url, headers=headers, timeout=120)

if response.status_code == 200:
    data = response.json()
    # Parse SDMX format
    # Convert to DataFrame
```

---

## DATA STRUCTURE

### COFOG Codes (Level I - Divisions)

```
01 = General public services
02 = Defence
03 = Public order and safety
04 = Economic affairs
05 = Environmental protection
06 = Housing and community amenities
07 = Health
08 = Recreation, culture and religion
09 = Education
10 = Social protection
```

### COFOG Codes (Level II - Groups, example)

```
01.1 = Executive and legislative organs
01.2 = Foreign economic aid
01.3 = General services
...
07.1 = Medical products
07.2 = Outpatient services
07.3 = Hospital services
...
10.1 = Sickness and disability
10.2 = Old age
10.3 = Survivors
10.4 = Family and children
```

### Typical CSV Format

```csv
Country,Function,Year,Value,Unit
USA,01,2020,5.2,% of GDP
USA,02,2020,3.4,% of GDP
USA,07,2020,8.5,% of GDP
...
```

---

## WHAT TO DOWNLOAD

### Priority 1: All OECD Countries, Level I

**Countries (38 OECD members):**
Australia, Austria, Belgium, Canada, Chile, Colombia, Costa Rica, Czech Republic, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Iceland, Ireland, Israel, Italy, Japan, Korea, Latvia, Lithuania, Luxembourg, Mexico, Netherlands, New Zealand, Norway, Poland, Portugal, Slovak Republic, Slovenia, Spain, Sweden, Switzerland, Turkey, United Kingdom, United States

**COFOG Divisions:** All 10 (01-10)
**Years:** 1995-latest (varies by country)
**Measure:** % of GDP (primary), National currency (secondary)

### Priority 2: Detailed (Level II) for Select Countries

**Countries with good Level II data:**
- United States
- United Kingdom
- Germany
- France
- Japan
- Canada

**COFOG Groups:** All 60+ subcategories
**Years:** 2000-latest
**Measure:** % of GDP

### Priority 3: Subsector Breakdowns (if needed)

**Sectors:**
- General government (total)
- Central government
- State government (for federal countries)
- Local government
- Social security funds

---

## FILE NAMING CONVENTION

When downloading manually, use:

```
oecd_cofog_{coverage}_{measure}_{level}.csv

Examples:
- oecd_cofog_all_countries_pct_gdp_level1.csv
- oecd_cofog_all_countries_currency_level1.csv
- oecd_cofog_usa_detailed_level2.csv
- oecd_cofog_eu_countries_pct_gdp.csv
```

Save to: `Technical/data/raw/oecd/cofog/`

---

## DATA QUALITY

### Coverage by Country (Typical)

**Excellent (1995+ for Level I, 2000+ for Level II):**
- Most EU countries
- United States
- Canada
- Japan
- Australia

**Good (1995+ for Level I, limited Level II):**
- Most other OECD countries

**Limited:**
- Newest OECD members (Colombia, Costa Rica)
- Some countries missing earlier years

### Time Series

- **Level I (divisions):** Usually from 1995 onwards
- **Level II (groups):** Usually from 2000 onwards
- **Latest data:** Typically 2-3 year lag (2022-2023 as of Oct 2025)

---

## COMPLEMENTARY DATA SOURCES

### For EU Countries (More Detail)

**Eurostat** has more detailed COFOG for EU countries:
- URL: https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp
- Coverage: 27 EU member states
- Detail: Level I from 1995, Level II from 2001
- Often more complete than OECD for EU countries

### For Non-OECD Countries

**IMF Government Finance Statistics:**
- URL: https://data.imf.org/
- Coverage: 190+ countries
- COFOG: When reported (not all countries)

---

## INTEGRATION PLAN

Once downloaded, this data will be used for:

1. **Country Profiles:**
   - Add COFOG breakdown to each country
   - Show spending priorities

2. **Cross-Country Analysis:**
   - Compare spending priorities
   - Identify outliers (high/low spending in categories)

3. **Efficiency Analysis:**
   - Spending per capita by function
   - Outcomes per dollar (education, health)

4. **Trend Analysis:**
   - How priorities have shifted over time
   - Impact of crises (financial crisis, COVID)

5. **Fiscal Analysis:**
   - Combine with revenue data
   - Complete fiscal picture

---

## TROUBLESHOOTING

### If Data Explorer doesn't work:

1. **Try legacy OECD.Stat:**
   - https://stats.oecd.org/ (may still have archives)

2. **Contact OECD:**
   - stats.contact@oecd.org
   - Ask for Table 11 bulk download

3. **Use Eurostat for EU countries:**
   - More detailed for EU anyway

4. **Use IMF GFS:**
   - Has COFOG for many countries

### If download is too large:

- Download by country group (e.g., EU countries, G7)
- Download one COFOG division at a time
- Use % of GDP only (skip national currency)

---

## EXPECTED FILE SIZE

**Complete dataset (all countries, all years, Level I):**
- CSV: 1-5 MB (manageable)
- Excel: 2-10 MB

**With Level II (detailed):**
- CSV: 10-50 MB
- Excel: 20-100 MB

---

## NEXT STEPS AFTER DOWNLOAD

1. Save downloaded file to `Technical/data/raw/oecd/cofog/`
2. Run data validation script (to be created)
3. Transform to standard format (country-year-function-value)
4. Integrate into country directories
5. Create visualizations
6. Add to country profiles

---

## SUPPORT

**OECD Data Help:**
- Email: stats.contact@oecd.org
- Documentation: https://www.oecd.org/sdd/fin-stats/

**Project-Specific Questions:**
- See: COFOG_TAXONOMY.md (complete classification guide)
- See: FISCAL_DATA_SOURCES.md (all fiscal data sources)

---

*Guide created: October 6, 2025*
*Project: Gerhard - Fiscal Analysis*
*Status: Manual download recommended (automated attempts unsuccessful)*
"""

        guide_file = RAW_DATA_DIR / "MANUAL_DOWNLOAD_GUIDE.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide)

        logger.info(f"✅ Guide created: {guide_file.name}")
        logger.info("")
        logger.info("📝 Manual download recommended:")
        logger.info("   See: Technical/data/raw/oecd/cofog/MANUAL_DOWNLOAD_GUIDE.md")
        logger.info("")
        logger.info("Key URL:")
        logger.info("   - OECD Data Explorer: https://data-explorer.oecd.org/")
        logger.info("   - Search for: 'Table 11' or 'COFOG'")
        logger.info("")

    def run(self):
        """Run complete OECD COFOG download attempt"""
        logger.info("OECD COFOG Functional Expenditure Downloader")
        logger.info("")

        # Try SDMX API
        success1 = self.attempt_sdmx_download()

        # Try CSV
        success2 = self.attempt_csv_download()

        if not (success1 or success2):
            logger.info("")
            logger.info("⚠️  Automated download not successful")
            logger.info("Creating comprehensive manual download guide...")
            self.create_manual_download_guide()

        logger.info("")
        logger.info("=" * 60)
        logger.info("OECD COFOG Download Process Complete")
        logger.info("=" * 60)


def main():
    downloader = OECDCOFOGDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
