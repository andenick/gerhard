"""
Tax Data Processing Script
Standardizes and processes international taxation data
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir, processed_data_dir, ensure_dir

logger = setup_logging(__name__)

# Define paths
RAW_DATA_DIR = raw_data_dir()
PROCESSED_DATA_DIR = ensure_dir(processed_data_dir())
OUTPUT_DIR = output_data_dir()


class TaxDataProcessor:
    """Processes and standardizes tax data from multiple sources"""

    def __init__(self):
        self.data_sources = {}

    def process_world_bank_data(self) -> pd.DataFrame:
        """Process World Bank tax revenue data"""
        logger.info("Processing World Bank data...")

        file_path = RAW_DATA_DIR / "worldbank_tax_revenue.csv"
        if not file_path.exists():
            logger.warning(f"World Bank data not found at {file_path}")
            return None

        try:
            df = pd.read_csv(file_path)

            # Standardize columns
            df_clean = df.rename(columns={
                'country': 'country_name',
                'countryiso3code': 'country_code',
                'date': 'year',
                'value': 'tax_revenue_pct_gdp'
            })

            # Keep only relevant columns
            cols = ['country_name', 'country_code', 'year', 'tax_revenue_pct_gdp']
            df_clean = df_clean[[c for c in cols if c in df_clean.columns]]

            # Remove missing values
            df_clean = df_clean.dropna(subset=['tax_revenue_pct_gdp'])

            # Convert year to integer
            df_clean['year'] = pd.to_numeric(df_clean['year'], errors='coerce').astype('Int64')

            # Sort
            df_clean = df_clean.sort_values(['country_code', 'year'])

            # Save to Output (Nick's standard: one sheet per file)
            output_file = OUTPUT_DIR / "world_bank_tax_revenue.xlsx"
            df_clean.to_excel(output_file, index=False, sheet_name='Data')
            logger.info(f"Processed World Bank data saved to {output_file}")
            logger.info(f"  Records: {len(df_clean)}, Countries: {df_clean['country_code'].nunique()}")

            self.data_sources['world_bank'] = df_clean
            return df_clean

        except Exception as e:
            logger.error(f"Error processing World Bank data: {e}")
            return None

    def create_unified_dataset(self) -> pd.DataFrame:
        """Create unified dataset combining all sources"""
        logger.info("Creating unified international tax dataset...")

        datasets = []

        # Add each processed dataset
        for source_name, df in self.data_sources.items():
            if df is not None:
                df_copy = df.copy()
                df_copy['data_source'] = source_name
                datasets.append(df_copy)

        if not datasets:
            logger.warning("No datasets available to unify")
            return None

        # Combine all datasets
        unified = pd.concat(datasets, ignore_index=True, sort=False)

        # Save unified dataset
        output_file = OUTPUT_DIR / "unified_international_tax_data.xlsx"
        unified.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Unified dataset saved to {output_file}")
        logger.info(f"  Total records: {len(unified)}")

        return unified

    def generate_summary_statistics(self) -> pd.DataFrame:
        """Generate summary statistics across all data sources"""
        logger.info("Generating summary statistics...")

        summaries = []

        for source_name, df in self.data_sources.items():
            if df is None:
                continue

            summary = {
                'data_source': source_name,
                'total_records': len(df),
                'countries': df['country_code'].nunique() if 'country_code' in df.columns else 0,
                'year_min': df['year'].min() if 'year' in df.columns else None,
                'year_max': df['year'].max() if 'year' in df.columns else None,
                'metrics_available': ', '.join([c for c in df.columns if c not in ['country_name', 'country_code', 'year', 'data_source']])
            }
            summaries.append(summary)

        summary_df = pd.DataFrame(summaries)

        # Save summary
        output_file = OUTPUT_DIR / "data_summary_statistics.xlsx"
        summary_df.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Summary statistics saved to {output_file}")

        return summary_df

    def process_all(self):
        """Process all available data sources"""
        logger.info("=" * 60)
        logger.info("Starting tax data processing...")
        logger.info("=" * 60)

        # Process each source
        self.process_world_bank_data()

        # Create unified dataset
        unified = self.create_unified_dataset()

        # Generate summaries
        summary = self.generate_summary_statistics()

        logger.info("\n" + "=" * 60)
        logger.info("Processing complete!")
        logger.info("=" * 60)
        logger.info(f"Output files saved to: {OUTPUT_DIR}")
        logger.info("\nGenerated files:")
        for file in OUTPUT_DIR.glob("*.xlsx"):
            logger.info(f"  - {file.name}")

        return unified, summary


def main():
    """Main execution function"""
    logger.info("Tax Data Processing Script - Gerhard Project")
    logger.info(f"Raw data directory: {RAW_DATA_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")

    processor = TaxDataProcessor()
    unified, summary = processor.process_all()

    logger.info("\n" + "=" * 60)
    logger.info("Summary of processed data:")
    logger.info("=" * 60)
    if summary is not None:
        logger.info(f"\n{summary.to_string()}")


if __name__ == "__main__":
    main()
