"""
Pipeline: Download World Bank & International Tax Data
Downloads international taxation data from multiple sources for analysis.
Project: Gerhard
"""

import pandas as pd
import requests
from pathlib import Path
import time
import sys
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir, processed_data_dir, ensure_dir

logger = setup_logging(__name__)

MANIFEST = {
    "id": "L00",
    "name": "Download World Bank & International Tax Data",
    "stage": "L",
    "description": "Downloads international taxation data from World Bank, OECD, and IMF APIs.",
    "depends_on": [],
    "inputs": [],
    "outputs": [
        {"path": "Technical/data/raw/worldbank_tax_revenue.csv", "description": "World Bank tax revenue data"},
        {"path": "Technical/data/raw/oecd_revenue_stats.csv", "description": "OECD revenue statistics"},
        {"path": "Technical/data/raw/imf_world_revenue.csv", "description": "IMF WoRLD revenue data"},
        {"path": "Technical/data/raw/data_inventory.csv", "description": "Inventory of downloaded files"},
    ],
    "timeout": 300,
    "parallel_safe": True,
}

# Define paths
RAW_DATA_DIR = ensure_dir(raw_data_dir())
PROCESSED_DATA_DIR = ensure_dir(processed_data_dir())
OUTPUT_DIR = output_data_dir()


class TaxDataDownloader:
    """Downloads tax data from various international sources"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download_oecd_revenue_stats(self):
        """Download OECD Revenue Statistics data"""
        logger.info("Downloading OECD Revenue Statistics...")

        # OECD Data Explorer SDMX API (stats.oecd.org retired May 2024)
        url = "https://sdmx.oecd.org/public/rest/data/OECD.CTP.TPS,DSD_REV@DF_REV,/all?dimensionAtObservation=AllDimensions"
        headers = {'Accept': 'application/vnd.sdmx.data+csv;file=true;labels=both'}

        try:
            response = self.session.get(url, headers=headers, timeout=60)

            # Reject HTML error pages
            content_type = response.headers.get('Content-Type', '')
            if 'html' in content_type.lower():
                logger.warning("Received HTML error page instead of data")
                return False

            if response.status_code == 200:
                if len(response.content) < 1024:
                    logger.warning(f"Response too small ({len(response.content)} bytes)")
                    return False

                output_file = RAW_DATA_DIR / "oecd_revenue_stats.csv"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                size_kb = len(response.content) / 1024
                logger.info(f"OECD data saved to {output_file} ({size_kb:.1f} KB)")
                return True
        except Exception as e:
            logger.warning(f"OECD API download failed: {e}")
            logger.info("Will use alternative download method...")

        return False

    def download_world_bank_tax_data(self):
        """Download World Bank tax revenue data"""
        logger.info("Downloading World Bank tax revenue data...")

        # World Bank API for tax revenue (% of GDP)
        indicator = "GC.TAX.TOTL.GD.ZS"
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
        params = {
            'format': 'json',
            'per_page': 20000,
            'date': '1990:2024'
        }

        try:
            response = self.session.get(url, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    df = pd.DataFrame(data[1])
                    output_file = RAW_DATA_DIR / "worldbank_tax_revenue.csv"
                    df.to_csv(output_file, index=False)
                    logger.info(f"World Bank data saved to {output_file}")
                    logger.info(f"Downloaded {len(df)} records")
                    return True
        except Exception as e:
            logger.error(f"World Bank download failed: {e}")

        return False

    def download_imf_world_data(self):
        """Download IMF World Revenue Longitudinal Database"""
        logger.info("Downloading IMF WoRLD data...")

        urls = [
            "https://data.imf.org/api/v1/data/WoRLD",
            "https://www.imf.org/~/media/Files/Publications/WP/WoRLD-Database.ashx"
        ]

        for url in urls:
            try:
                response = self.session.get(url, timeout=60)
                if response.status_code == 200:
                    output_file = RAW_DATA_DIR / "imf_world_revenue.csv"
                    with open(output_file, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"IMF data saved to {output_file}")
                    return True
            except Exception as e:
                logger.warning(f"IMF download attempt failed for {url}: {e}")

        logger.info("IMF data may require manual download from:")
        logger.info("https://data.imf.org/en?sk=77413f1d-1525-450a-a23a-47aeed40fe78")
        return False

    def create_data_inventory(self) -> pd.DataFrame:
        """Create inventory of downloaded data files"""
        inventory = []

        for file_path in RAW_DATA_DIR.glob("*"):
            if file_path.is_file():
                inventory.append({
                    'filename': file_path.name,
                    'size_kb': file_path.stat().st_size / 1024,
                    'source': self._identify_source(file_path.name),
                    'download_date': time.strftime('%Y-%m-%d'),
                    'status': 'downloaded'
                })

        df = pd.DataFrame(inventory)
        output_file = RAW_DATA_DIR / "data_inventory.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"Data inventory saved to {output_file}")

        return df

    def _identify_source(self, filename: str) -> str:
        """Identify data source from filename"""
        if 'oecd' in filename.lower():
            return 'OECD'
        elif 'worldbank' in filename.lower() or 'wb' in filename.lower():
            return 'World Bank'
        elif 'imf' in filename.lower():
            return 'IMF'
        elif 'irs' in filename.lower() or 'soi' in filename.lower():
            return 'IRS SOI'
        elif 'cbo' in filename.lower():
            return 'CBO'
        elif 'eurostat' in filename.lower():
            return 'Eurostat'
        else:
            return 'Unknown'

    def download_all(self):
        """Download all available data sources"""
        logger.info("=" * 60)
        logger.info("Starting comprehensive tax data download...")
        logger.info("=" * 60)

        results = {}

        # Download from each source
        results['OECD'] = self.download_oecd_revenue_stats()
        time.sleep(2)  # Rate limiting

        results['World Bank'] = self.download_world_bank_tax_data()
        time.sleep(2)

        results['IMF'] = self.download_imf_world_data()

        # Create inventory
        inventory = self.create_data_inventory()

        # Summary
        logger.info("=" * 60)
        logger.info("Download Summary:")
        logger.info("=" * 60)
        for source, success in results.items():
            status = "Success" if success else "Failed/Manual Required"
            logger.info(f"{source:20s}: {status}")

        logger.info("\nData inventory:")
        logger.info(f"\n{inventory.to_string()}")

        return results, inventory


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")
    logger.info(f"Raw data directory: {RAW_DATA_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    downloader = TaxDataDownloader()
    results, inventory = downloader.download_all()

    logger.info("\n" + "=" * 60)
    logger.info("Next Steps:")
    logger.info("=" * 60)
    logger.info("1. For sources requiring manual download:")
    logger.info("   - IRS SOI: https://www.irs.gov/statistics/soi-tax-stats-individual-statistical-tables-by-tax-rate-and-income-percentile")
    logger.info("   - CBO: https://www.cbo.gov/publication/60706")
    logger.info("   - Treasury: https://home.treasury.gov/system/files/131/Distribution-of-Tax-Burden-Current-Law-2024.pdf")
    logger.info("   - Eurostat: https://ec.europa.eu/eurostat/databrowser/")
    logger.info(f"\n2. Place downloaded files in: {RAW_DATA_DIR}")
    logger.info("\n3. Run data processing script to standardize formats")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
