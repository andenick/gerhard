"""
Country Data Collection Script
Processes international data into country-specific datasets
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import json
from pathlib import Path
import sys
import ast

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, countries_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()
DATA_DIR = output_data_dir()


class CountryDataCollector:
    """Collects and organizes data for individual countries"""

    def __init__(self):
        self.international_data = None
        self.country_list = None
        self.load_source_data()

    def load_source_data(self):
        """Load source datasets"""
        logger.info("Loading source data...")

        # Load international historical data
        intl_file = DATA_DIR / "international_historical_tax_data.xlsx"
        if intl_file.exists():
            self.international_data = pd.read_excel(intl_file)

            # Parse country information
            self.international_data['country_dict'] = self.international_data['country_name'].apply(ast.literal_eval)
            self.international_data['country_code'] = self.international_data['country_dict'].apply(lambda x: x['id'])
            self.international_data['country_name_clean'] = self.international_data['country_dict'].apply(lambda x: x['value'])

            logger.info(f"Loaded {len(self.international_data)} international records")

            # Get unique countries
            self.country_list = self.international_data[['country_code', 'country_name_clean']].drop_duplicates()
            logger.info(f"Found {len(self.country_list)} unique countries")
        else:
            logger.error("International data file not found")

    def collect_country_data(self, country_code, country_name):
        """Collect all data for a specific country"""
        logger.info(f"Collecting data for {country_name} ({country_code})")

        country_dir = COUNTRIES_DIR / country_code

        # Extract country-specific data
        country_data = self.international_data[
            self.international_data['country_code'] == country_code
        ].copy()

        if len(country_data) == 0:
            logger.warning(f"  No data found for {country_name}")
            return False

        # Clean and prepare data
        country_data = country_data[[
            'year',
            'tax_revenue_pct_gdp',
            'country_code',
            'country_name_clean'
        ]].copy()

        country_data = country_data.rename(columns={
            'country_name_clean': 'country_name'
        })

        country_data = country_data.sort_values('year')

        # Save national data
        output_file = country_dir / "Output" / "Data" / f"{country_code.lower()}_national_tax_data.xlsx"
        write_single_sheet_excel(country_data, output_file)
        logger.info(f"  Saved national data: {len(country_data)} years")

        # Update config
        self.update_config(country_code, country_name, country_data)

        return True

    def update_config(self, country_code, country_name, data):
        """Update country configuration file with data info"""
        country_dir = COUNTRIES_DIR / country_code
        config_file = country_dir / "Technical" / "data" / "config.json"

        with open(config_file, 'r') as f:
            config = json.load(f)

        # Update with data information
        config['data_collection']['national_data'] = True
        config['data_years']['first_year'] = int(data['year'].min())
        config['data_years']['last_year'] = int(data['year'].max())
        config['data_years']['total_years'] = len(data)
        config['status'] = 'data_collected'

        # Calculate average tax revenue
        avg_tax = data['tax_revenue_pct_gdp'].mean()
        config['tax_metrics'] = {
            'average_tax_pct_gdp': round(avg_tax, 2),
            'latest_year': int(data['year'].max()),
            'latest_tax_pct_gdp': round(data[data['year'] == data['year'].max()]['tax_revenue_pct_gdp'].iloc[0], 2)
        }

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def collect_all_countries(self):
        """Collect data for all countries"""
        logger.info("=" * 60)
        logger.info("Collecting Country Data")
        logger.info("=" * 60)

        if self.international_data is None or self.country_list is None:
            logger.warning("No international data available — country collection will be limited")
            return 0

        collected = 0
        failed = 0

        for _, row in self.country_list.iterrows():
            country_code = row['country_code']
            country_name = row['country_name_clean']

            try:
                success = self.collect_country_data(country_code, country_name)
                if success:
                    collected += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"  Error collecting {country_name}: {e}")
                failed += 1

        logger.info("\n" + "=" * 60)
        logger.info("Data Collection Complete!")
        logger.info("=" * 60)
        logger.info(f"Successfully collected: {collected} countries")
        logger.info(f"Failed: {failed} countries")

        return collected


def main():
    logger.info("Country Data Collector - Gerhard Project")

    collector = CountryDataCollector()
    count = collector.collect_all_countries()

    logger.info(f"\nSuccessfully collected data for {count} countries")
    logger.info("Next steps:")
    logger.info("1. Collect subnational data for federal countries")
    logger.info("2. Generate country analyses")
    logger.info("3. Create country reports")


if __name__ == "__main__":
    main()
