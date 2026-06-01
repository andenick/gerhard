"""
Extract US DINA Distributional Tables
Parse PSZ2022 Distributional Series into clean Excel files

Project: Gerhard - DINA Table Extraction
"""

import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, countries_dir

logger = setup_logging(__name__)

DINA_DIR = raw_data_dir() / "us_dina"
US_OUTPUT = countries_dir() / "US" / "Output" / "Data"

class DINATableExtractor:
    """Extract and clean DINA distributional tables"""

    def __init__(self):
        self.dina_file = DINA_DIR / "PSZ2022_DistributionalSeries.xlsx"
        self.xl = pd.ExcelFile(self.dina_file)
        self.extracted_tables = {}

    def extract_table(self, sheet_name, header_row=7, data_start_row=8):
        """Extract a single table from DINA file

        Args:
            sheet_name: Name of sheet to extract
            header_row: Row number containing column headers (0-indexed)
            data_start_row: Row number where data starts

        Returns:
            DataFrame with cleaned data
        """
        try:
            # Read the sheet
            df = pd.read_excel(self.dina_file, sheet_name=sheet_name)

            # Extract headers from header row
            headers = df.iloc[header_row].tolist()

            # Extract data starting from data_start_row
            data_df = df.iloc[data_start_row:].copy()
            data_df.columns = headers

            # First column is year - rename it
            year_col = data_df.columns[0]
            data_df = data_df.rename(columns={year_col: 'Year'})

            # Convert Year to integer (drop any NaN rows)
            data_df = data_df.dropna(subset=['Year'])
            data_df['Year'] = data_df['Year'].astype(int)

            # Sort by year
            data_df = data_df.sort_values('Year')

            # Reset index
            data_df = data_df.reset_index(drop=True)

            logger.info(f"✅ Extracted {sheet_name}: {len(data_df)} years ({data_df['Year'].min()}-{data_df['Year'].max()})")

            return data_df

        except Exception as e:
            logger.error(f"Error extracting {sheet_name}: {e}")
            return None

    def extract_income_shares_tables(self):
        """Extract key income share tables"""
        logger.info("=" * 60)
        logger.info("Extracting Income Share Tables")
        logger.info("=" * 60)

        # Key tables for income shares
        key_tables = {
            # Factor income (Part A)
            'TA1': 'Factor Income Shares',

            # Pre-tax income (Part B)
            'TB1': 'PreTax Income Shares',

            # Post-tax income (Part C)
            'TC1': 'PostTax Income Shares',

            # Fiscal income (Part D)
            'TD1': 'Fiscal Income Shares',
        }

        extracted = {}

        for table_code, description in key_tables.items():
            logger.info(f"\nExtracting {table_code}: {description}")
            df = self.extract_table(table_code)

            if df is not None:
                extracted[table_code] = {
                    'description': description,
                    'data': df
                }

                # Show sample
                logger.info(f"  Columns: {', '.join(df.columns[:8].tolist())}...")
                logger.info(f"  Latest data ({df['Year'].max()}): Top 10% = {df['Top 10%'].iloc[-1]:.3f}")

        return extracted

    def extract_wealth_tables(self):
        """Extract wealth distribution tables"""
        logger.info("\n" + "=" * 60)
        logger.info("Extracting Wealth Distribution Tables")
        logger.info("=" * 60)

        # Wealth tables (Part E)
        wealth_tables = {
            'TE1': 'Wealth Shares',
        }

        extracted = {}

        for table_code, description in wealth_tables.items():
            logger.info(f"\nExtracting {table_code}: {description}")
            df = self.extract_table(table_code)

            if df is not None:
                extracted[table_code] = {
                    'description': description,
                    'data': df
                }

                # Show sample
                logger.info(f"  Columns: {', '.join(df.columns[:8].tolist())}...")
                if 'Top 10%' in df.columns:
                    logger.info(f"  Latest data ({df['Year'].max()}): Top 10% = {df['Top 10%'].iloc[-1]:.3f}")

        return extracted

    def extract_tax_tables(self):
        """Extract tax burden tables"""
        logger.info("\n" + "=" * 60)
        logger.info("Extracting Tax Burden Tables")
        logger.info("=" * 60)

        # Tax tables (Part G)
        tax_tables = {
            'TG1': 'Total Tax Rates',
        }

        extracted = {}

        for table_code, description in tax_tables.items():
            logger.info(f"\nExtracting {table_code}: {description}")
            df = self.extract_table(table_code)

            if df is not None:
                extracted[table_code] = {
                    'description': description,
                    'data': df
                }

                # Show sample
                logger.info(f"  Columns: {', '.join(df.columns[:8].tolist())}...")

        return extracted

    def create_combined_excel(self, income_shares, wealth_shares, tax_rates):
        """Create combined Excel file with all key data"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Combined Excel File")
        logger.info("=" * 60)

        output_file = US_OUTPUT / "us_dina_distributional_data.xlsx"

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:

            # Income shares
            for table_code, data in income_shares.items():
                df = data['data']
                sheet_name = table_code
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  Added sheet: {sheet_name} - {data['description']}")

            # Wealth shares
            for table_code, data in wealth_shares.items():
                df = data['data']
                sheet_name = table_code
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  Added sheet: {sheet_name} - {data['description']}")

            # Tax rates
            for table_code, data in tax_rates.items():
                df = data['data']
                sheet_name = table_code
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  Added sheet: {sheet_name} - {data['description']}")

        logger.info(f"\n✅ Combined file saved: {output_file.name}")
        logger.info(f"   Location: {output_file}")

        return output_file

    def create_top_shares_file(self, income_shares):
        """Create focused file with just top income shares"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Top Income Shares File")
        logger.info("=" * 60)

        # Extract just the top shares from each income concept
        top_shares_data = {}

        for table_code, data in income_shares.items():
            df = data['data']

            # Select Year and top share columns
            top_cols = ['Year', 'Top 10%', 'Top 5%', 'Top 1%', 'Top 0.5%', 'Top 0.1%', 'Top 0.01%']
            available_cols = [col for col in top_cols if col in df.columns]

            top_df = df[available_cols].copy()
            top_shares_data[data['description']] = top_df

            logger.info(f"  {data['description']}: {len(available_cols)-1} top share series")

        # Create Excel file
        output_file = US_OUTPUT / "us_top_income_shares.xlsx"

        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            for description, df in top_shares_data.items():
                sheet_name = description.replace(' Income Shares', '').replace(' ', '_')
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"  Added sheet: {sheet_name}")

        logger.info(f"\n✅ Top shares file saved: {output_file.name}")

        return output_file

    def run(self):
        """Run complete DINA table extraction"""
        logger.info("🇺🇸 US DINA Table Extraction")
        logger.info("Piketty-Saez-Zucman Distributional National Accounts")
        logger.info("")

        # Extract income shares
        income_shares = self.extract_income_shares_tables()

        # Extract wealth shares
        wealth_shares = self.extract_wealth_tables()

        # Extract tax rates
        tax_rates = self.extract_tax_tables()

        # Create combined Excel
        combined_file = self.create_combined_excel(income_shares, wealth_shares, tax_rates)

        # Create top shares file
        top_shares_file = self.create_top_shares_file(income_shares)

        logger.info("\n" + "=" * 60)
        logger.info("✅ DINA Table Extraction Complete!")
        logger.info("=" * 60)
        logger.info(f"Files created in: {US_OUTPUT}")
        logger.info(f"  1. us_dina_distributional_data.xlsx (complete data)")
        logger.info(f"  2. us_top_income_shares.xlsx (top shares only)")
        logger.info("")
        logger.info("Data includes:")
        logger.info(f"  - Income shares: {len(income_shares)} tables (Factor, PreTax, PostTax, Fiscal)")
        logger.info(f"  - Wealth shares: {len(wealth_shares)} table(s)")
        logger.info(f"  - Tax rates: {len(tax_rates)} table(s)")
        logger.info("")


def main():
    extractor = DINATableExtractor()
    extractor.run()


if __name__ == "__main__":
    main()
