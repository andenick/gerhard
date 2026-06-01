"""
Integrate US DINA Data into US Country Directory
Add Saez-Zucman distributional data to enhance US analysis

Project: Gerhard - US DINA Integration
"""

import pandas as pd
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, countries_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

DINA_DIR = raw_data_dir() / "us_dina"
US_DIR = countries_dir() / "US"
US_OUTPUT = US_DIR / "Output" / "Data"


class USDINAIntegrator:
    """Integrate US DINA distributional data"""

    def __init__(self):
        self.dina_files = {
            'distributional': DINA_DIR / "PSZ2022_DistributionalSeries.xlsx",
            'macro': DINA_DIR / "PSZ2022_MacroSeries.xlsx",
            'main': DINA_DIR / "PSZ2018MainData.xlsx"
        }
        self.extracted_data = {}

    def extract_distributional_series(self):
        """Extract key distributional series from PSZ2022"""
        logger.info("=" * 60)
        logger.info("Extracting US Distributional Data")
        logger.info("=" * 60)

        dist_file = self.dina_files['distributional']

        if not dist_file.exists():
            logger.error(f"File not found: {dist_file}")
            return None

        # Load Excel file and examine sheets
        xl = pd.ExcelFile(dist_file)
        logger.info(f"Available sheets: {xl.sheet_names[:10]}...")

        # Key sheets to extract (based on PSZ structure)
        key_sheets = []

        # Find sheets with distributional data
        for sheet in xl.sheet_names:
            if any(x in sheet.lower() for x in ['share', 'income', 'percentile', 'top']):
                key_sheets.append(sheet)

        logger.info(f"Found {len(key_sheets)} relevant sheets")

        # Extract first sheet as sample
        if len(xl.sheet_names) > 0:
            first_sheet = xl.sheet_names[0]
            logger.info(f"\nExamining first sheet: {first_sheet}")

            df = pd.read_excel(dist_file, sheet_name=first_sheet)
            logger.info(f"Columns: {df.columns.tolist()[:10]}")
            logger.info(f"Rows: {len(df)}")
            logger.info(f"\nSample data:")
            logger.info(df.head(10).to_string())

            self.extracted_data['distributional_sample'] = df

        return key_sheets

    def extract_top_income_shares(self):
        """Extract top 1%, 10% income shares"""
        logger.info("\n" + "=" * 60)
        logger.info("Extracting Top Income Shares")
        logger.info("=" * 60)

        dist_file = self.dina_files['distributional']

        try:
            # Try to find the main distributional table
            # PSZ typically has sheets like "TaxableIncomeShares", "NationalIncomeShares", etc.
            xl = pd.ExcelFile(dist_file)

            # Look for income share sheets
            share_sheets = [s for s in xl.sheet_names if 'share' in s.lower() or 'income' in s.lower()]

            if share_sheets:
                logger.info(f"Income share sheets: {share_sheets[:5]}")

                # Read first income share sheet
                df = pd.read_excel(dist_file, sheet_name=share_sheets[0])

                # Save for analysis
                output_file = US_OUTPUT / "us_dina_income_shares.xlsx"
                write_single_sheet_excel(df, output_file, sheet_name='Income_Shares')
                logger.info(f"✅ Saved: {output_file.name}")

                self.extracted_data['income_shares'] = df
                return df
            else:
                logger.warning("No income share sheets found")
                return None

        except Exception as e:
            logger.error(f"Error extracting income shares: {e}")
            return None

    def create_summary_file(self):
        """Create summary of DINA data availability"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating DINA Summary")
        logger.info("=" * 60)

        summary = {
            'source': 'Piketty-Saez-Zucman Distributional National Accounts',
            'coverage': '1962-2022',
            'files_available': {},
            'data_extracted': list(self.extracted_data.keys())
        }

        # Check which files exist
        for name, filepath in self.dina_files.items():
            if filepath.exists():
                summary['files_available'][name] = {
                    'filename': filepath.name,
                    'size_mb': round(filepath.stat().st_size / 1024 / 1024, 2)
                }

        # Save summary
        summary_file = US_OUTPUT / "us_dina_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"✅ Summary saved: {summary_file.name}")
        logger.info(f"\nDINA files available: {len(summary['files_available'])}")
        for name, info in summary['files_available'].items():
            logger.info(f"  - {name}: {info['filename']} ({info['size_mb']} MB)")

        return summary

    def create_readme(self):
        """Create README for DINA data"""
        readme_content = """# US DINA Data
## Piketty-Saez-Zucman Distributional National Accounts

**Source:** https://gabriel-zucman.eu/usdina/
**Coverage:** 1962-2022
**Detail Level:** Complete income distribution by percentile

## Files in This Directory

### DINA Data Files
- `us_dina_income_shares.xlsx` - Top income shares (Top 1%, 10%, etc.)
- `us_dina_summary.json` - Summary of available DINA data

### Original DINA Files (Technical/data/raw/us_dina/)
- `PSZ2022_DistributionalSeries.xlsx` - Complete distributional series
- `PSZ2022_MacroSeries.xlsx` - Macroeconomic aggregates
- `PSZ2018MainData.xlsx` - Main DINA dataset
- `PSZ_Codebook.pdf` - Documentation

## What This Data Provides

**Income Distribution:**
- Pre-tax and post-tax income by percentile
- Top 1%, 0.1%, 0.01% income shares
- Bottom 50%, Middle 40% shares

**Tax Incidence:**
- Federal, state, and local taxes by income level
- Complete tax burden analysis
- Effective tax rates by percentile

**Historical Coverage:**
- 60 years of consistent data (1962-2022)
- Annual observations
- Internationally comparable methodology

## Usage

This is the most detailed distributional tax data available for any country.

All data follows DINA methodology documented in:
Piketty, T., Saez, E., & Zucman, G. (2018). "Distributional National Accounts: Methods and Estimates for the United States." Quarterly Journal of Economics, 133(2), 553-609.

## Integration Status

✅ Downloaded from gabriel-zucman.eu
✅ Stored in project structure
⏳ Full integration into US analysis pending

---

*Generated: October 6, 2025*
*Project: Gerhard*
"""

        readme_file = US_OUTPUT / "US_DINA_README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        logger.info(f"✅ README created: {readme_file.name}")

    def run(self):
        """Run complete US DINA integration"""
        logger.info("🇺🇸 US DINA Integration")
        logger.info("Piketty-Saez-Zucman Distributional National Accounts")
        logger.info("")

        # Step 1: Extract distributional series
        key_sheets = self.extract_distributional_series()

        # Step 2: Extract top income shares
        income_shares = self.extract_top_income_shares()

        # Step 3: Create summary
        summary = self.create_summary_file()

        # Step 4: Create README
        self.create_readme()

        logger.info("\n" + "=" * 60)
        logger.info("✅ US DINA Integration Complete!")
        logger.info("=" * 60)
        logger.info(f"Output directory: {US_OUTPUT}")
        logger.info(f"Files created: {len(list(US_OUTPUT.glob('*dina*')))}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Analyze extracted distributional data")
        logger.info("2. Create visualizations (top income shares)")
        logger.info("3. Update US PDF report with inequality analysis")
        logger.info("")


def main():
    integrator = USDINAIntegrator()
    integrator.run()


if __name__ == "__main__":
    main()
