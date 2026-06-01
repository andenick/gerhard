"""
Download World Inequality Database (WID.world) Data
Downloads the complete Saez-Piketty-Zucman distributional database

Project: Gerhard - Enhanced with Distributional Data
Data Source: WID.world (World Inequality Database)
Researchers: Piketty, Saez, Zucman + 100+ international researchers
"""

import requests
import pandas as pd
import zipfile
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir, ensure_dir

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "wid")
OUTPUT_DIR = output_data_dir()

# WID.world bulk download URL
WID_BULK_DOWNLOAD_URL = "https://wid.world/bulk_download/wid_all_data.zip"


class WIDDownloader:
    """Downloads and processes WID.world data"""

    def __init__(self):
        self.zip_file = RAW_DATA_DIR / "wid_all_data.zip"
        self.extracted_dir = RAW_DATA_DIR

    def download_wid_bulk_data(self):
        """Download the complete WID.world dataset"""
        logger.info("=" * 60)
        logger.info("Downloading World Inequality Database (WID.world)")
        logger.info("=" * 60)
        logger.info(f"Source: {WID_BULK_DOWNLOAD_URL}")
        logger.info(f"Destination: {self.zip_file}")
        logger.info("")
        logger.info("This is the Saez-Piketty-Zucman distributional database")
        logger.info("Contains: Top income shares, wealth distribution, tax data")
        logger.info("Coverage: 70+ countries with detailed data")
        logger.info("")

        if self.zip_file.exists():
            logger.info("⚠️  WID data already downloaded. Delete to re-download.")
            logger.info(f"File: {self.zip_file}")
            logger.info("")
            return True

        try:
            logger.info("Starting download (this may take several minutes)...")
            response = requests.get(WID_BULK_DOWNLOAD_URL, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0

            with open(self.zip_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            logger.info(f"Progress: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB)")

            logger.info("✅ Download complete!")
            logger.info(f"File size: {self.zip_file.stat().st_size / 1024 / 1024:.1f} MB")
            return True

        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            if self.zip_file.exists():
                self.zip_file.unlink()
            return False

    def extract_wid_data(self):
        """Extract the WID.world ZIP file"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Extracting WID.world data")
        logger.info("=" * 60)

        if not self.zip_file.exists():
            logger.error("❌ ZIP file not found. Run download first.")
            return False

        try:
            logger.info(f"Extracting to: {self.extracted_dir}")
            with zipfile.ZipFile(self.zip_file, 'r') as zip_ref:
                zip_ref.extractall(self.extracted_dir)

            logger.info("✅ Extraction complete!")
            logger.info("")
            logger.info("Files extracted:")
            for file in self.extracted_dir.glob("*.*"):
                if file.suffix in ['.csv', '.dta', '.xlsx', '.txt']:
                    logger.info(f"  - {file.name}")

            return True

        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            return False

    def analyze_wid_structure(self):
        """Analyze the structure of WID.world data"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Analyzing WID.world data structure")
        logger.info("=" * 60)

        # Look for main data file
        csv_files = list(self.extracted_dir.glob("*.csv"))

        if not csv_files:
            logger.warning("⚠️  No CSV files found in extracted data")
            return

        logger.info(f"Found {len(csv_files)} CSV file(s)")
        logger.info("")

        for csv_file in csv_files:
            logger.info(f"Analyzing: {csv_file.name}")
            try:
                # Read first few rows to understand structure
                df = pd.read_csv(csv_file, nrows=100)

                logger.info(f"  Columns: {len(df.columns)}")
                logger.info(f"  Column names: {', '.join(df.columns.tolist()[:10])}...")
                logger.info(f"  Rows (sample): {len(df)}")
                logger.info("")

                # Check for key columns
                if 'country' in df.columns or 'Country' in df.columns:
                    countries = df['country'].unique() if 'country' in df.columns else df['Country'].unique()
                    logger.info(f"  Countries in sample: {len(countries)}")
                    logger.info(f"  Sample countries: {', '.join(str(c) for c in countries[:10])}")

                if 'variable' in df.columns or 'Variable' in df.columns:
                    variables = df['variable'].unique() if 'variable' in df.columns else df['Variable'].unique()
                    logger.info(f"  Variables in sample: {len(variables)}")
                    logger.info(f"  Sample variables: {', '.join(str(v) for v in variables[:10])}")

                logger.info("")

            except Exception as e:
                logger.error(f"  ❌ Error analyzing {csv_file.name}: {e}")

    def create_wid_summary(self):
        """Create summary of available WID.world data"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Creating WID.world Data Summary")
        logger.info("=" * 60)

        csv_files = list(self.extracted_dir.glob("*.csv"))

        if not csv_files:
            logger.warning("⚠️  No CSV files found")
            return

        main_file = csv_files[0]
        logger.info(f"Processing main data file: {main_file.name}")

        try:
            # Read full dataset
            logger.info("Loading full dataset (this may take a minute)...")
            df = pd.read_csv(main_file)

            logger.info(f"✅ Loaded {len(df):,} rows")
            logger.info(f"Columns: {len(df.columns)}")
            logger.info("")

            # Create summary
            summary = {
                'total_rows': len(df),
                'columns': df.columns.tolist(),
                'file_size_mb': main_file.stat().st_size / 1024 / 1024
            }

            # Analyze by country if column exists
            country_col = None
            for col in ['country', 'Country', 'alpha2']:
                if col in df.columns:
                    country_col = col
                    break

            if country_col:
                countries = df[country_col].unique()
                logger.info(f"Countries: {len(countries)}")
                logger.info(f"Sample: {', '.join(str(c) for c in countries[:20])}")
                summary['countries'] = len(countries)

            # Analyze by variable if column exists
            var_col = None
            for col in ['variable', 'Variable', 'var']:
                if col in df.columns:
                    var_col = col
                    break

            if var_col:
                variables = df[var_col].unique()
                logger.info(f"")
                logger.info(f"Variables: {len(variables)}")
                logger.info(f"Sample: {', '.join(str(v) for v in variables[:20])}")
                summary['variables'] = len(variables)

            # Save summary
            summary_file = RAW_DATA_DIR / "wid_data_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("WID.world Data Summary\n")
                f.write("=" * 60 + "\n\n")
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")

            logger.info("")
            logger.info(f"✅ Summary saved to: {summary_file}")

            return df

        except Exception as e:
            logger.error(f"❌ Error creating summary: {e}")
            return None

    def run_full_download(self):
        """Run complete WID.world download and analysis"""
        logger.info("🌍 WID.world Data Download Pipeline")
        logger.info("Saez-Piketty-Zucman Distributional Database")
        logger.info("")

        # Step 1: Download
        if not self.download_wid_bulk_data():
            logger.error("❌ Download failed. Aborting.")
            return False

        # Step 2: Extract
        if not self.extract_wid_data():
            logger.error("❌ Extraction failed. Aborting.")
            return False

        # Step 3: Analyze structure
        self.analyze_wid_structure()

        # Step 4: Create summary
        df = self.create_wid_summary()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ WID.world Download Complete!")
        logger.info("=" * 60)
        logger.info(f"Data location: {RAW_DATA_DIR}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review wid_data_summary.txt for data structure")
        logger.info("2. Run integration script to add to country directories")
        logger.info("3. Update analyses with distributional data")
        logger.info("")

        return True


def main():
    logger.info("World Inequality Database (WID.world) Downloader")
    logger.info("Saez-Piketty-Zucman Distributional Tax Data")
    logger.info("")

    downloader = WIDDownloader()
    success = downloader.run_full_download()

    if success:
        logger.info("🎉 Successfully downloaded WID.world data!")
    else:
        logger.error("❌ Download process failed")

    return success


if __name__ == "__main__":
    main()
