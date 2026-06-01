"""
Extract WID.world Distributional Data
Extract top income shares, wealth distribution, and inequality metrics

Project: Gerhard - Enhanced with Distributional Data
Data Source: WID.world (Saez-Piketty-Zucman database)
"""

import pandas as pd
import json
from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, countries_dir, ensure_dir
from utils.config import project_root
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WID_DIR = raw_data_dir() / "wid"
OUTPUT_DIR = ensure_dir(project_root() / "Technical" / "data" / "processed" / "wid_distributional")
COUNTRIES_DIR = countries_dir()


class WIDExtractor:
    """Extract distributional data from WID.world"""

    def __init__(self):
        self.countries_file = WID_DIR / "WID_countries.csv"
        self.extraction_stats = defaultdict(int)

        # Key variables to extract
        self.key_variables = {
            # Top income shares (pre-tax)
            'sptinc992j': 'top10_pretax_income_share',
            'sptinc992i': 'top1_pretax_income_share',
            'sptinc992t': 'top01_pretax_income_share',
            'sptinc992u': 'top001_pretax_income_share',

            # Middle/bottom shares (pre-tax)
            'sptinc992m': 'middle40_pretax_income_share',
            'sptinc992n': 'bottom50_pretax_income_share',

            # Top income shares (post-tax/disposable)
            'sdiinc992j': 'top10_posttax_income_share',
            'sdiinc992i': 'top1_posttax_income_share',

            # Middle/bottom shares (post-tax)
            'sdiinc992m': 'middle40_posttax_income_share',
            'sdiinc992n': 'bottom50_posttax_income_share',

            # Wealth shares
            'shweal992j': 'top10_wealth_share',
            'shweal992i': 'top1_wealth_share',
            'shweal992t': 'top01_wealth_share',

            # Average incomes (for reference)
            'aptinc992j': 'avg_income_top10',
            'aptinc992i': 'avg_income_top1',
        }

    def load_countries_list(self):
        """Load list of WID countries"""
        df = pd.read_csv(self.countries_file, sep=';')
        logger.info(f"Loaded {len(df)} countries from WID")
        return df

    def extract_country_data(self, country_code):
        """Extract distributional data for a single country"""
        data_file = WID_DIR / f"WID_data_{country_code}.csv"

        if not data_file.exists():
            logger.warning(f"Data file not found for {country_code}")
            return None

        try:
            # Load country data
            df = pd.read_csv(data_file, sep=';')

            # Filter for relevant percentiles (p0p100 = full population for shares)
            # For income/wealth shares, we want p90p100 (top 10%), p99p100 (top 1%), etc.
            # But WID stores shares at different percentile codes

            extracted_data = []

            for wid_var, our_name in self.key_variables.items():
                # Find this variable in the data
                var_data = df[df['variable'] == wid_var].copy()

                if len(var_data) == 0:
                    continue

                # For shares, use appropriate percentile
                if 'share' in our_name:
                    # Shares are typically stored at specific percentiles
                    # Top 10%: p90p100, Top 1%: p99p100, etc.
                    if 'top10' in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p90p100']
                    elif 'top1' in our_name and 'top01' not in our_name and 'top001' not in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p99p100']
                    elif 'top01' in our_name and 'top001' not in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p99.9p100']
                    elif 'top001' in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p99.99p100']
                    elif 'middle40' in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p50p90']
                    elif 'bottom50' in our_name:
                        pct_data = var_data[var_data['percentile'] == 'p0p50']
                    else:
                        pct_data = var_data[var_data['percentile'] == 'p0p100']
                else:
                    # For averages, use p0p100
                    pct_data = var_data[var_data['percentile'] == 'p0p100']

                if len(pct_data) == 0:
                    continue

                # Create time series for this variable
                for _, row in pct_data.iterrows():
                    extracted_data.append({
                        'country_code': country_code,
                        'year': row['year'],
                        'variable': our_name,
                        'value': row['value']
                    })

            if not extracted_data:
                return None

            # Convert to DataFrame
            df_extracted = pd.DataFrame(extracted_data)

            # Pivot to wide format (years as rows, variables as columns)
            df_wide = df_extracted.pivot_table(
                index=['country_code', 'year'],
                columns='variable',
                values='value'
            ).reset_index()

            return df_wide

        except Exception as e:
            logger.error(f"Error extracting {country_code}: {e}")
            return None

    def save_country_data(self, country_code, df):
        """Save extracted data for a country"""
        if df is None or len(df) == 0:
            return False

        output_file = OUTPUT_DIR / f"{country_code.lower()}_wid_distributional.xlsx"

        try:
            write_single_sheet_excel(df, output_file, sheet_name='Distributional_Data')
            self.extraction_stats['saved'] += 1
            return True

        except Exception as e:
            logger.error(f"Error saving {country_code}: {e}")
            return False

    def create_summary_statistics(self, countries_df):
        """Create summary of what was extracted"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Extraction Summary")
        logger.info("=" * 60)

        summary = {
            'total_countries_in_wid': len(countries_df),
            'countries_processed': self.extraction_stats['processed'],
            'countries_with_data': self.extraction_stats['saved'],
            'extraction_rate': round(self.extraction_stats['saved'] / len(countries_df) * 100, 1)
        }

        for key, value in summary.items():
            logger.info(f"{key}: {value}")

        # Save summary
        summary_file = OUTPUT_DIR / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\nSummary saved to: {summary_file}")

        return summary

    def extract_all_countries(self):
        """Extract distributional data for all countries"""
        logger.info("=" * 60)
        logger.info("Extracting WID Distributional Data for All Countries")
        logger.info("=" * 60)

        countries_df = self.load_countries_list()

        # Process each country
        for idx, row in countries_df.iterrows():
            country_code = row['alpha2']
            country_name = row['shortname']

            self.extraction_stats['processed'] += 1

            if self.extraction_stats['processed'] % 25 == 0:
                logger.info(f"Progress: {self.extraction_stats['processed']}/{len(countries_df)} "
                          f"({self.extraction_stats['saved']} with data)")

            # Extract data
            df = self.extract_country_data(country_code)

            if df is not None:
                # Save data
                if self.save_country_data(country_code, df):
                    if self.extraction_stats['saved'] <= 10:  # Log first 10
                        logger.info(f"✅ {country_code} ({country_name}): "
                                  f"{len(df)} years, {len(df.columns)-2} variables")

        logger.info("")
        logger.info(f"✅ Extraction complete! "
                   f"{self.extraction_stats['saved']}/{len(countries_df)} countries with data")

        # Create summary
        self.create_summary_statistics(countries_df)

    def run(self):
        """Run complete extraction process"""
        logger.info("🔍 WID.world Distributional Data Extraction")
        logger.info("Extracting top income shares, wealth distribution, inequality metrics")
        logger.info("")

        self.extract_all_countries()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ WID Extraction Complete!")
        logger.info("=" * 60)
        logger.info(f"Output directory: {OUTPUT_DIR}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Review extracted data files")
        logger.info("2. Run integration script to add to country directories")
        logger.info("3. Update analyses with distributional metrics")
        logger.info("")


def main():
    extractor = WIDExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
