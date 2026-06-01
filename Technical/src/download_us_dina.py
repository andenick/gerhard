"""
Download US Distributional National Accounts (DINA) Data
Most detailed US tax and income distribution data from Saez-Zucman

Project: Gerhard - Enhanced with US DINA
Source: https://gabriel-zucman.eu/usdina/
"""

import requests
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, ensure_dir

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "us_dina")

# US DINA download URLs (from gabriel-zucman.eu/usdina/)
US_DINA_URLS = {
    'main_data': {
        'url': 'https://gabriel-zucman.eu/files/PSZ2018MainData.xlsx',
        'filename': 'PSZ2018MainData.xlsx',
        'description': 'Main DINA data file (2018)'
    },
    'macro_series': {
        'url': 'https://gabriel-zucman.eu/files/PSZ2022AppendixTablesI(Aggreg).xlsx',
        'filename': 'PSZ2022_MacroSeries.xlsx',
        'description': 'Macroeconomic series (2022 update)'
    },
    'distributional_series': {
        'url': 'https://gabriel-zucman.eu/files/PSZ2022AppendixTablesII(Distrib).xlsx',
        'filename': 'PSZ2022_DistributionalSeries.xlsx',
        'description': 'Distributional series by percentile (2022 update)'
    },
    'codebook': {
        'url': 'https://gabriel-zucman.eu/files/PSZCodebook.pdf',
        'filename': 'PSZ_Codebook.pdf',
        'description': 'DINA codebook and documentation'
    }
}

# Note: Micro-files are on Dropbox and require manual download or special handling
# URL: https://www.dropbox.com/s/ynboa2i235v6qaw/PSZ2022Dinafiles.zip?dl=0


def download_file(url, filename, description):
    """Download a single file"""
    output_path = RAW_DATA_DIR / filename

    if output_path.exists():
        logger.info(f"✓ Already downloaded: {filename}")
        return True

    try:
        logger.info(f"Downloading: {description}")
        logger.info(f"  URL: {url}")
        logger.info(f"  Destination: {filename}")

        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024) == 0:  # Log every MB
                            logger.info(f"  Progress: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB)")

        logger.info(f"✅ Downloaded: {filename} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download {filename}: {e}")
        if output_path.exists():
            output_path.unlink()
        return False


def main():
    logger.info("=" * 60)
    logger.info("US DINA Data Download")
    logger.info("Piketty-Saez-Zucman Distributional National Accounts")
    logger.info("=" * 60)
    logger.info("")

    success_count = 0
    total_count = len(US_DINA_URLS)

    for key, info in US_DINA_URLS.items():
        logger.info("")
        if download_file(info['url'], info['filename'], info['description']):
            success_count += 1

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Download Summary: {success_count}/{total_count} files")
    logger.info("=" * 60)
    logger.info(f"Data location: {RAW_DATA_DIR}")
    logger.info("")

    if success_count == total_count:
        logger.info("✅ All US DINA files downloaded successfully!")
    else:
        logger.warning(f"⚠️  {total_count - success_count} file(s) failed to download")

    logger.info("")
    logger.info("📝 NOTE: DINA micro-files require manual download from Dropbox:")
    logger.info("   https://www.dropbox.com/s/ynboa2i235v6qaw/PSZ2022Dinafiles.zip?dl=0")
    logger.info("")


if __name__ == "__main__":
    main()
