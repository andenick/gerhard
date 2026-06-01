"""
Download OECD Detailed Revenue Statistics
Tax structure by type (income, VAT, corporate, social security)

Project: Gerhard - OECD Tax Structure Data
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

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "oecd")

# OECD data URLs — using new OECD Data Explorer SDMX API (stats.oecd.org retired May 2024)
OECD_URLS = {
    'revenue_stats': {
        'url': 'https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV@DF_REV,/all?dimensionAtObservation=AllDimensions',
        'filename': 'oecd_tax_revenue.csv',
        'description': 'OECD Tax Revenue Statistics',
        'headers': {'Accept': 'application/vnd.sdmx.data+csv;file=true;labels=both'}
    }
}


def download_oecd_bulk():
    """Attempt to download OECD bulk data"""
    logger.info("=" * 60)
    logger.info("OECD Revenue Statistics Download")
    logger.info("=" * 60)
    logger.info("")

    # Try OECD Data Explorer SDMX API (stats.oecd.org retired May 2024)
    logger.info("Attempting OECD SDMX API download...")

    try:
        url = "https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV@DF_REV,/all?dimensionAtObservation=AllDimensions"
        headers = {'Accept': 'application/vnd.sdmx.data+csv;file=true;labels=both'}

        logger.info(f"Trying: {url}")

        response = requests.get(url, headers=headers, timeout=60)

        # Reject HTML error pages
        content_type = response.headers.get('Content-Type', '')
        if 'html' in content_type.lower():
            logger.warning("Received HTML error page instead of data")
            return False

        if response.status_code == 200:
            # Reject suspiciously small responses
            if len(response.content) < 1024:
                logger.warning(f"Response too small ({len(response.content)} bytes), likely an error page")
                return False

            output_file = RAW_DATA_DIR / "oecd_tax_data.csv"
            with open(output_file, 'wb') as f:
                f.write(response.content)

            size_kb = len(response.content) / 1024
            logger.info(f"Downloaded: {output_file} ({size_kb:.1f} KB)")
            return True
        else:
            logger.warning(f"Status code: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def create_manual_download_guide():
    """Create guide for manual OECD download"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Manual Download Guide")
    logger.info("=" * 60)

    guide = """# OECD Revenue Statistics - Manual Download Guide

## Option 1: OECD Data Explorer (Recommended)

1. Visit: https://data-explorer.oecd.org/
2. Search for "Revenue Statistics" or navigate to Tax → Revenue Statistics
3. Choose:
   - All countries
   - All tax categories (1000-6000 series)
   - All available years
4. Export as CSV or Excel
5. Save to: `Technical/data/raw/oecd/oecd_revenue_detailed.csv`

## Option 2: OECD Data Portal

1. Visit: https://data.oecd.org/tax/tax-revenue.htm
2. Click "Export" → "Full data set"
3. Download CSV
4. Save to: `Technical/data/raw/oecd/`

## Option 3: Global Revenue Statistics Database

1. Visit: https://www.oecd.org/en/data/datasets/global-revenue-statistics-database.html
2. Download complete database
3. Extract relevant files

## What to Download

**Tax Categories to Include:**
- 1000: Taxes on income, profits, and capital gains
- 2000: Social security contributions
- 3000: Taxes on payroll and workforce
- 4000: Taxes on property
- 5000: Taxes on goods and services (VAT, excise)
- 6000: Other taxes

**Coverage:**
- All OECD countries (38+ countries)
- Time series: 1965-present
- As % of GDP and as % of total tax revenue

## After Download

Place downloaded file in:
`Technical/data/raw/oecd/`

Then run: `python process_oecd_revenue.py`

---

*Generated: October 6, 2025*
"""

    guide_file = RAW_DATA_DIR / "MANUAL_DOWNLOAD_GUIDE.md"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)

    logger.info(f"✅ Guide created: {guide_file}")
    logger.info("")
    logger.info("📝 Manual download required:")
    logger.info("   See: Technical/data/raw/oecd/MANUAL_DOWNLOAD_GUIDE.md")
    logger.info("")
    logger.info("Key URLs:")
    logger.info("   - OECD Data Explorer: https://data-explorer.oecd.org/")
    logger.info("   - Data Portal: https://data.oecd.org/tax/tax-revenue.htm")
    logger.info("")


def main():
    logger.info("OECD Revenue Statistics Downloader")
    logger.info("")

    # Try automated download
    success = download_oecd_bulk()

    if not success:
        logger.info("")
        logger.info("⚠️  Automated download not available")
        logger.info("Creating manual download guide...")

        # Create guide for manual download
        create_manual_download_guide()

    logger.info("=" * 60)
    logger.info("OECD Download Process Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
