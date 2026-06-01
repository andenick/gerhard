"""
Download Eurostat Government Finance Statistics (GFS)
COFOG functional classification for EU countries

Project: Gerhard - Eurostat COFOG Data
"""

import requests
import pandas as pd
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, ensure_dir

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "eurostat" / "gfs")


class EurostatGFSDownloader:
    """Download Eurostat GFS COFOG data"""

    def __init__(self):
        self.base_url = "https://ec.europa.eu/eurostat"
        self.session = requests.Session()

    def attempt_bulk_download(self):
        """Try to download Eurostat COFOG data"""
        logger.info("=" * 60)
        logger.info("Attempting Eurostat GFS Download")
        logger.info("=" * 60)

        # Eurostat bulk download endpoints
        endpoints = [
            # Main GFS table
            "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/gov_10a_exp?format=TSV",
            "https://ec.europa.eu/eurostat/estat-navtree-portlet-prod/BulkDownloadListing?file=data/gov_10a_exp.tsv.gz",
            # Alternative formats
            "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/gov_10a_exp",
        ]

        for url in endpoints:
            try:
                logger.info(f"\nTrying: {url[:80]}...")

                response = self.session.get(url, timeout=180, stream=True)

                if response.status_code == 200 and len(response.content) > 10000:
                    # Determine file extension
                    if 'tsv.gz' in url:
                        ext = 'tsv.gz'
                    elif 'TSV' in url.upper():
                        ext = 'tsv'
                    else:
                        ext = 'xml'

                    output_file = RAW_DATA_DIR / f"eurostat_gov_10a_exp.{ext}"

                    with open(output_file, 'wb') as f:
                        f.write(response.content)

                    size_mb = len(response.content) / 1024 / 1024
                    logger.info(f"✅ Downloaded: {output_file.name} ({size_mb:.1f} MB)")

                    if size_mb > 0.1:
                        return True
                else:
                    logger.warning(f"Status code: {response.status_code}")

            except Exception as e:
                logger.error(f"Error: {e}")
                continue

        return False

    def create_manual_download_guide(self):
        """Create manual download guide for Eurostat"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Manual Download Guide")
        logger.info("=" * 60)

        guide = """# Eurostat Government Finance Statistics - Manual Download Guide

**Updated:** October 6, 2025
**Coverage:** 27 EU member states + some non-EU European countries
**Classification:** COFOG (most detailed Level II available)
**Time Span:** 1995+ (Level I), 2001+ (Level II)

---

## WHAT IS EUROSTAT GFS?

Eurostat collects detailed government finance statistics for EU countries based on ESA 2010 (European System of Accounts).

**Key Features:**
- Most detailed COFOG data available (Level II from 2001)
- Complete coverage of EU countries
- Annual data with 11-month lag
- Subsector breakdowns (central, state, local, social security)
- Both national currency and euros

**Table:** gov_10a_exp - General government expenditure by function (COFOG)

---

## DOWNLOAD METHOD 1: Eurostat Data Browser (Recommended)

### Step-by-Step Instructions

**URL:** https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp

1. **Navigate to Data Browser:**
   - Go to https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp
   - This is the direct link to COFOG expenditure table

2. **Select Data:**
   - **Countries:** Select all EU countries or specific ones
   - **Sector:** General government (or subsectors if needed)
   - **Function (COFOG):** Select divisions or groups
     - Level I: GF01 through GF10 (10 divisions)
     - Level II: Detailed groups (e.g., GF0701, GF0702, etc.)
   - **Unit:**
     - MIO_EUR (million euros) - recommended
     - MIO_NAC (million national currency)
     - PC_GDP (% of GDP)
     - PC_TOT (% of total expenditure)
   - **Time:** Select all years (1995-latest)

3. **Download:**
   - Click "Download" button
   - Choose format:
     - **TSV** (tab-separated) - recommended for large datasets
     - **CSV** (comma-separated)
     - **Excel** (smaller datasets only)
   - Save to: `Technical/data/raw/eurostat/gfs/`

**Recommended Downloads:**

**Download 1: Complete COFOG Level I (Divisions)**
- All 27 EU countries
- All 10 COFOG divisions (GF01-GF10)
- General government sector
- Million euros + % of GDP
- All years (1995-2023)
- Filename: `eurostat_cofog_level1_all_countries.tsv`

**Download 2: Detailed COFOG Level II (Groups)**
- All EU countries or major ones (DEU, FRA, ITA, ESP, NLD, etc.)
- All COFOG groups (detailed subcategories)
- Million euros
- 2001-2023
- Filename: `eurostat_cofog_level2_detailed.tsv`

---

## DOWNLOAD METHOD 2: Bulk Download

### Bulk Download Files

**URL:** https://ec.europa.eu/eurostat/estat-navtree-portlet-prod/BulkDownloadListing

**Steps:**
1. Navigate to bulk download page
2. Search for "gov_10a_exp"
3. Download compressed file:
   - `gov_10a_exp.tsv.gz` (complete dataset)
4. Extract with 7-Zip or gunzip
5. Save to: `Technical/data/raw/eurostat/gfs/`

**File Format:** Tab-separated values (TSV)
**Size:** Typically 5-20 MB compressed, 50-200 MB uncompressed

---

## DOWNLOAD METHOD 3: API Access

### Eurostat API

**Base URL:**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/gov_10a_exp
```

**Example Query (All countries, all COFOG, % GDP):**
```
https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/gov_10a_exp?format=TSV&na_item=TE&unit=PC_GDP&sector=S13
```

**Parameters:**
- `format`: TSV, JSON, XML
- `na_item`: TE (total expenditure)
- `unit`: PC_GDP (% GDP), MIO_EUR (million euros)
- `sector`: S13 (general government)
- `geo`: Country codes (e.g., DE, FR, IT)
- `cofog99`: COFOG codes

---

## DATA STRUCTURE

### COFOG Codes in Eurostat

**Level I (Divisions):**
```
GF01 = General public services
GF02 = Defence
GF03 = Public order and safety
GF04 = Economic affairs
GF05 = Environmental protection
GF06 = Housing and community amenities
GF07 = Health
GF08 = Recreation, culture and religion
GF09 = Education
GF10 = Social protection
```

**Level II (Groups - Examples):**
```
GF0701 = Medical products, appliances and equipment
GF0702 = Outpatient services
GF0703 = Hospital services
GF0704 = Public health services
GF0705 = R&D health
GF0706 = Health n.e.c.

GF0901 = Pre-primary and primary education
GF0902 = Secondary education
GF0903 = Post-secondary non-tertiary education
GF0904 = Tertiary education
...
```

### Typical TSV Format

```
unit,sector,na_item,cofog99,geo\\TIME_PERIOD\t2010\t2011\t2012...
PC_GDP,S13,TE,GF01,BE\t5.2\t5.3\t5.4...
PC_GDP,S13,TE,GF01,DE\t6.1\t6.0\t6.2...
```

---

## EU COUNTRIES COVERED (27)

Austria (AT), Belgium (BE), Bulgaria (BG), Croatia (HR), Cyprus (CY),
Czech Republic (CZ), Denmark (DK), Estonia (EE), Finland (FI), France (FR),
Germany (DE), Greece (EL), Hungary (HU), Ireland (IE), Italy (IT),
Latvia (LV), Lithuania (LT), Luxembourg (LU), Malta (MT), Netherlands (NL),
Poland (PL), Portugal (PT), Romania (RO), Slovakia (SK), Slovenia (SI),
Spain (ES), Sweden (SE)

**Non-EU European countries sometimes included:**
Iceland (IS), Norway (NO), Switzerland (CH), United Kingdom (GB - historical)

---

## DATA QUALITY

### Coverage
**Level I (Divisions):**
- All 27 EU countries
- Compulsory from 1995
- Nearly complete data

**Level II (Groups):**
- All 27 EU countries
- Compulsory from 2001
- Very complete data (most detailed available globally)

### Time Lag
- Data submitted 11 months after reference year
- 2023 data available in late 2024
- 2024 data expected in late 2025

### Quality
- Highest quality government expenditure data
- Standardized ESA 2010 methodology
- Strictly enforced reporting requirements
- Most detailed functional classification available

---

## FILE NAMING CONVENTION

When downloading, use:

```
eurostat_cofog_{level}_{coverage}_{unit}_{years}.tsv

Examples:
- eurostat_cofog_level1_all_eu_pc_gdp_1995_2023.tsv
- eurostat_cofog_level2_major_countries_mio_eur_2001_2023.tsv
- eurostat_gfs_complete_dataset.tsv.gz (bulk download)
```

Save to: `Technical/data/raw/eurostat/gfs/`

---

## INTEGRATION PLAN

Once downloaded, this data will provide:

1. **Most detailed functional classification** available
   - 10 COFOG divisions
   - 60+ COFOG groups
   - EU countries only but highest quality

2. **Subsector breakdowns:**
   - Central government
   - State government (for federal countries)
   - Local government
   - Social security funds

3. **Multiple metrics:**
   - Million euros
   - Million national currency
   - % of GDP
   - % of total expenditure
   - Per capita (can calculate)

4. **Enhanced EU country profiles:**
   - Add detailed functional breakdown
   - Show spending priorities
   - Track changes over time
   - Compare across EU countries

---

## COMPLEMENTARY TO OTHER SOURCES

**Eurostat vs OECD:**
- Eurostat: More detailed (Level II mandatory)
- OECD: Broader coverage (38 countries)
- Overlap: EU countries in both - Eurostat more detailed

**Eurostat vs IMF GFS:**
- Eurostat: EU only, very detailed
- IMF: Global, less detailed
- Use Eurostat for EU, IMF for others

**Recommendation:**
- Use Eurostat for EU countries (most detailed)
- Use OECD for other OECD countries
- Use IMF GFS for rest of world

---

## TROUBLESHOOTING

### If Data Browser doesn't work:

1. **Try bulk download** (Method 2)
   - Most reliable for complete dataset

2. **Try API** (Method 3)
   - Good for specific queries

3. **Contact Eurostat:**
   - estat-user-support@ec.europa.eu

### If file is too large:

- Download by country group (e.g., large EU countries separately)
- Download Level I and Level II separately
- Use compressed format (TSV.GZ)

---

## EXPECTED FILE SIZES

**Level I (all EU, all years):**
- TSV: 2-5 MB
- Compressed: 500 KB - 1 MB

**Level II (all EU, all years):**
- TSV: 20-50 MB
- Compressed: 3-8 MB

**Complete bulk dataset:**
- Compressed: 5-10 MB
- Uncompressed: 50-100 MB

---

## NEXT STEPS AFTER DOWNLOAD

1. Extract if compressed (`.gz` files)
2. Convert TSV to CSV if needed
3. Parse Eurostat format (pivoted by year)
4. Transform to long format (country-year-function-value)
5. Integrate into country directories (EU countries)
6. Create COFOG visualizations
7. Update country profiles

---

## SUPPORT

**Eurostat Help:**
- Email: estat-user-support@ec.europa.eu
- Documentation: https://ec.europa.eu/eurostat/web/government-finance-statistics
- Metadata: https://ec.europa.eu/eurostat/cache/metadata/en/gov_10a_exp_esms.htm

**Project Documentation:**
- See: COFOG_TAXONOMY.md (complete classification)
- See: FISCAL_DATA_SOURCES.md (all sources)

---

*Guide created: October 6, 2025*
*Project: Gerhard - Fiscal Analysis*
*Target: 27 EU countries with most detailed COFOG data available*
"""

        guide_file = RAW_DATA_DIR / "MANUAL_DOWNLOAD_GUIDE.md"
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write(guide)

        logger.info(f"✅ Guide created: {guide_file.name}")
        logger.info("")
        logger.info("📝 Manual download recommended:")
        logger.info("   See: Technical/data/raw/eurostat/gfs/MANUAL_DOWNLOAD_GUIDE.md")
        logger.info("")
        logger.info("Key URL:")
        logger.info("   - Data Browser: https://ec.europa.eu/eurostat/databrowser/view/gov_10a_exp")
        logger.info("")

    def run(self):
        """Run complete Eurostat download attempt"""
        logger.info("Eurostat Government Finance Statistics Downloader")
        logger.info("")

        # Try bulk download
        success = self.attempt_bulk_download()

        if not success:
            logger.info("")
            logger.info("⚠️  Automated download not successful")
            logger.info("Creating manual download guide...")
            self.create_manual_download_guide()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Eurostat GFS Download Process Complete")
        logger.info("=" * 60)


def main():
    downloader = EurostatGFSDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
