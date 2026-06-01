#!/usr/bin/env python3
"""
Eurostat COFOG Parser
Transforms 211 MB TSV file into structured government spending datasets
"""

import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
import gzip
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

class EurostatCOFOGParser:
    """Parses Eurostat Government Finance Statistics with COFOG classification"""

    def __init__(self, input_file: Path, output_dir: Path):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.processed_dir = self.output_dir / "processed" / "eurostat_cofog"
        self.country_dir = self.processed_dir / "countries"

        # Create directories
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.country_dir.mkdir(parents=True, exist_ok=True)

        # COFOG Classification
        self.cofog_divisions = {
            "01": "General public services",
            "02": "Defence",
            "03": "Public order and safety",
            "04": "Economic affairs",
            "05": "Environmental protection",
            "06": "Housing and community amenities",
            "07": "Health",
            "08": "Recreation, culture and religion",
            "09": "Education",
            "10": "Social protection"
        }

        self.cofog_groups = {
            # Division 01
            "0101": "Executive and legislative organs, financial and fiscal affairs, external affairs",
            "0102": "Foreign economic aid",
            "0103": "General services",
            "0104": "Basic research",
            "0105": "R&D related to general public services",
            "0106": "Public debt transactions",
            "0107": "Transfers of a general character between different levels of government",
            "0108": "Transfers of a general character to the private sector and abroad",
            "0109": "General public services, n.e.c.",

            # Division 07 - Health
            "0701": "Medical products, appliances and equipment",
            "0702": "Outpatient services",
            "0703": "Hospital services",
            "0704": "Public health services",
            "0705": "R&D related to health",

            # Division 09 - Education
            "0901": "Pre-primary and primary education",
            "0902": "Secondary education",
            "0903": "Post-secondary non-tertiary education",
            "0904": "Tertiary education",
            "0905": "Education not definable by level",
            "0906": "Subsidiary services to education",
            "0907": "R&D related to education",

            # Division 10 - Social Protection
            "1001": "Sickness and disability",
            "1002": "Old age",
            "1003": "Survivors",
            "1004": "Family and children",
            "1005": "Unemployment",
            "1006": "Housing",
            "1007": "Social exclusion, n.e.c.",
            "1008": "R&D related to social protection",

            # And many more groups for all divisions...
        }

        # EU Countries (27)
        self.eu_countries = {
            "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia",
            "CY": "Cyprus", "CZ": "Czech Republic", "DK": "Denmark", "EE": "Estonia",
            "FI": "Finland", "FR": "France", "DE": "Germany", "GR": "Greece",
            "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia",
            "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
            "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
            "SI": "Slovenia", "ES": "Spain", "SE": "Sweden"
        }

        # Data columns expected
        self.expected_columns = [
            "DATAFLOW", "REF_AREA", "FREQ", "TIME_PERIOD", "OBS_VALUE",
            "UNIT_MULT", "COFOG99", "COFOG99_LABEL", "SECTOR", "SECTOR_LABEL",
            "PRICE_BASE", "PRICE_BASE_LABEL", "UNIT_MEASURE", "UNIT_MEASURE_LABEL"
        ]

    def detect_file_format(self) -> str:
        """Detect if file is gzipped or plain text"""
        if self.input_file.suffix == '.gz':
            return 'gzip'
        elif self.input_file.suffix == '.zip':
            return 'zip'
        else:
            return 'text'

    def read_eurostat_data(self, chunk_size: int = 100000) -> pd.DataFrame:
        """Read Eurostat data in chunks to handle large file"""
        logger.info(f"Reading Eurostat data from {self.input_file}")
        logger.info(f"File size: {self.input_file.stat().st_size / (1024*1024):.1f} MB")

        file_format = self.detect_file_format()
        logger.info(f"Detected format: {file_format}")

        chunks = []
        total_rows = 0

        try:
            if file_format == 'gzip':
                # Read gzipped file
                with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                    # Skip header lines if they exist
                    for i, line in enumerate(f):
                        if i < 10 and line.startswith('\\'):
                            continue
                        elif i >= 10:
                            # Read remaining as CSV with tab separator
                            f.seek(0)
                            for chunk_num, chunk in enumerate(pd.read_csv(
                                f, sep='\t', chunksize=chunk_size, low_memory=False
                            )):
                                chunks.append(chunk)
                                total_rows += len(chunk)
                                if chunk_num % 10 == 0:
                                    logger.info(f"Processed {total_rows:,} rows...")
                            break
            else:
                # Read plain text file
                for chunk_num, chunk in enumerate(pd.read_csv(
                    self.input_file, sep='\t', chunksize=chunk_size, low_memory=False
                )):
                    chunks.append(chunk)
                    total_rows += len(chunk)
                    if chunk_num % 10 == 0:
                        logger.info(f"Processed {total_rows:,} rows...")

            # Combine all chunks
            df = pd.concat(chunks, ignore_index=True)
            logger.info(f"✅ Total rows loaded: {len(df):,}")

            return df

        except Exception as e:
            logger.error(f"Error reading Eurostat data: {e}")
            return pd.DataFrame()

    def clean_and_standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize the Eurostat data"""
        logger.info("Cleaning and standardizing data...")

        # Create a copy to avoid SettingWithCopyWarning
        df_clean = df.copy()

        # Handle missing columns
        missing_cols = set(self.expected_columns) - set(df_clean.columns)
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}")
            for col in missing_cols:
                df_clean[col] = None

        # Clean numeric values
        numeric_cols = ['OBS_VALUE', 'UNIT_MULT']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

        # Clean time period
        if 'TIME_PERIOD' in df_clean.columns:
            df_clean['year'] = pd.to_numeric(df_clean['TIME_PERIOD'], errors='coerce')

        # Standardize country codes
        if 'REF_AREA' in df_clean.columns:
            df_clean['country_code'] = df_clean['REF_AREA'].str.strip()
            df_clean['country_name'] = df_clean['country_code'].map(self.eu_countries)

        # Extract COFOG codes and names
        if 'COFOG99' in df_clean.columns:
            df_clean['cofog_code'] = df_clean['COFOG99'].str.strip()
            df_clean['cofog_division'] = df_clean['cofog_code'].str[:2]
            df_clean['cofog_division_name'] = df_clean['cofog_division'].map(self.cofog_divisions)

        # Calculate values in millions if needed
        if 'UNIT_MULT' in df_clean.columns and 'OBS_VALUE' in df_clean.columns:
            df_clean['value_millions'] = df_clean.apply(
                lambda row: row['OBS_VALUE'] / (1000 ** row['UNIT_MULT'])
                if pd.notna(row['UNIT_MULT']) else row['OBS_VALUE'],
                axis=1
            )

        # Filter for EU countries only
        df_clean = df_clean[df_clean['country_code'].isin(self.eu_countries.keys())]

        # Remove rows with missing essential data
        essential_cols = ['country_code', 'year', 'cofog_code', 'value_millions']
        df_clean = df_clean.dropna(subset=essential_cols)

        logger.info(f"✅ Data cleaned. Rows remaining: {len(df_clean):,}")
        return df_clean

    def extract_country_data(self, df: pd.DataFrame, country_code: str) -> pd.DataFrame:
        """Extract data for a specific country"""
        country_df = df[df['country_code'] == country_code].copy()
        logger.info(f"Extracted {len(country_df)} rows for {country_code} ({self.eu_countries[country_code]})")
        return country_df

    def create_country_summary(self, country_df: pd.DataFrame, country_code: str) -> Dict:
        """Create summary statistics for a country"""
        summary = {
            'country_code': country_code,
            'country_name': self.eu_countries[country_code],
            'total_observations': len(country_df),
            'year_range': {
                'start': int(country_df['year'].min()) if len(country_df) > 0 else None,
                'end': int(country_df['year'].max()) if len(country_df) > 0 else None
            },
            'cofog_divisions': [],
            'total_spending_eur': {
                'latest_year': {},
                'average': {}
            }
        }

        # Get COFOG divisions covered
        divisions = country_df['cofog_division'].dropna().unique()
        for div in sorted(divisions):
            div_name = self.cofog_divisions.get(div, div)
            summary['cofog_divisions'].append({
                'code': div,
                'name': div_name,
                'observations': len(country_df[country_df['cofog_division'] == div])
            })

        # Calculate spending by latest year
        if len(country_df) > 0:
            latest_year = country_df['year'].max()
            latest_data = country_df[country_df['year'] == latest_year]

            for _, row in latest_data.iterrows():
                if pd.notna(row['cofog_division']):
                    div = row['cofog_division']
                    div_name = self.cofog_divisions.get(div, div)
                    summary['total_spending_eur']['latest_year'][div] = {
                        'name': div_name,
                        'value_millions': float(row['value_millions']),
                        'year': int(latest_year)
                    }

        return summary

    def save_country_data(self, country_df: pd.DataFrame, country_code: str, summary: Dict):
        """Save country data in multiple formats"""
        country_name = self.eu_countries[country_code].replace(' ', '_').lower()

        # Save as Excel (pivot format)
        excel_file = self.country_dir / f"{country_code}_cofog_expenditure.xlsx"

        # Create pivot table for easier analysis
        pivot_df = country_df.pivot_table(
            index=['year', 'cofog_division', 'cofog_division_name'],
            values='value_millions',
            aggfunc='sum'
        ).reset_index()

        write_single_sheet_excel(pivot_df, excel_file)

        # Save as CSV
        csv_file = self.country_dir / f"{country_code}_cofog_expenditure.csv"
        country_df.to_csv(csv_file, index=False)

        # Save summary as JSON
        summary_file = self.country_dir / f"{country_code}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Saved {country_code} data to {excel_file}")

    def process_all_countries(self, df: pd.DataFrame):
        """Process all EU countries"""
        logger.info(f"Processing data for {len(self.eu_countries)} EU countries...")

        results = {}

        for i, (country_code, country_name) in enumerate(self.eu_countries.items(), 1):
            logger.info(f"Processing {i}/{len(self.eu_countries)}: {country_name} ({country_code})")

            # Extract country data
            country_df = self.extract_country_data(df, country_code)

            if len(country_df) == 0:
                logger.warning(f"No data found for {country_name}")
                continue

            # Create summary
            summary = self.create_country_summary(country_df, country_code)

            # Save data
            self.save_country_data(country_df, country_code, summary)

            results[country_code] = summary

            # Create additional visualizations for key countries
            if country_code in ['DE', 'FR', 'IT', 'ES', 'NL']:  # Top 5 EU economies
                self.create_country_visualizations(country_df, country_code)

        # Save overall results
        results_file = self.processed_dir / "all_countries_summary.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        logger.info(f"✅ All countries processed. Results saved to {results_file}")
        return results

    def create_country_visualizations(self, country_df: pd.DataFrame, country_code: str):
        """Create simple data summaries for visualization"""
        logger.info(f"Creating visualization data for {country_code}")

        # Create time series by COFOG division
        ts_data = country_df.groupby(['year', 'cofog_division', 'cofog_division_name'])['value_millions'].sum().reset_index()

        # Create latest year breakdown
        latest_year = country_df['year'].max()
        latest_data = country_df[country_df['year'] == latest_year]

        # Save visualization data
        viz_file = self.country_dir / f"{country_code}_visualization_data.json"

        viz_data = {
            'country_code': country_code,
            'country_name': self.eu_countries[country_code],
            'latest_year': int(latest_year),
            'time_series': ts_data.to_dict('records'),
            'latest_breakdown': latest_data.to_dict('records')
        }

        with open(viz_file, 'w', encoding='utf-8') as f:
            json.dump(viz_data, f, indent=2)

    def create_master_dataset(self, df: pd.DataFrame):
        """Create master dataset for all EU countries"""
        logger.info("Creating master EU COFOG dataset...")

        # Create aggregated dataset
        master_df = df.groupby([
            'country_code', 'country_name', 'year', 'cofog_division', 'cofog_division_name'
        ])['value_millions'].sum().reset_index()

        # Calculate totals by country and year
        country_totals = master_df.groupby(['country_code', 'country_name', 'year'])['value_millions'].sum().reset_index()
        country_totals = country_totals.rename(columns={'value_millions': 'total_spending_millions'})

        # Merge back to get percentages
        master_df = master_df.merge(country_totals, on=['country_code', 'country_name', 'year'])
        master_df['spending_percentage'] = (master_df['value_millions'] / master_df['total_spending_millions']) * 100

        # Save master datasets
        master_file = self.processed_dir / "eu_cofog_master_dataset.xlsx"
        write_single_sheet_excel(master_df, master_file)

        master_csv = self.processed_dir / "eu_cofog_master_dataset.csv"
        master_df.to_csv(master_csv, index=False)

        logger.info(f"✅ Master dataset saved: {master_file}")
        logger.info(f"Shape: {master_df.shape}, Size: {master_file.stat().st_size / (1024*1024):.1f} MB")

        return master_df

    def generate_processing_report(self, df: pd.DataFrame, results: Dict):
        """Generate comprehensive processing report"""
        logger.info("Generating processing report...")

        report = {
            'processing_date': datetime.now().isoformat(),
            'input_file': str(self.input_file),
            'input_size_mb': self.input_file.stat().st_size / (1024*1024),
            'total_rows_original': len(df),
            'total_countries_processed': len(results),
            'output_directory': str(self.processed_dir),
            'countries_summary': {},
            'data_quality': {
                'years_coverage': {},
                'cofog_divisions_coverage': {}
            }
        }

        # Summarize each country
        for country_code, summary in results.items():
            report['countries_summary'][country_code] = {
                'name': summary['country_name'],
                'observations': summary['total_observations'],
                'year_range': summary['year_range'],
                'cofog_divisions_count': len(summary['cofog_divisions'])
            }

        # Calculate coverage statistics
        all_years = []
        all_divisions = []
        for summary in results.values():
            if summary['year_range']['start']:
                all_years.extend(range(summary['year_range']['start'], summary['year_range']['end'] + 1))
            all_divisions.extend([d['code'] for d in summary['cofog_divisions']])

        report['data_quality']['years_coverage'] = {
            'earliest': min(all_years) if all_years else None,
            'latest': max(all_years) if all_years else None,
            'unique_years': len(set(all_years))
        }

        report['data_quality']['cofog_divisions_coverage'] = {
            'divisions_found': list(set(all_divisions)),
            'divisions_count': len(set(all_divisions)),
            'coverage_percentage': (len(set(all_divisions)) / len(self.cofog_divisions)) * 100
        }

        # Save report
        report_file = self.processed_dir / "processing_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        logger.info(f"✅ Processing report saved: {report_file}")
        return report

def main():
    """Main execution function"""
    # File paths
    _technical_dir = Path(__file__).resolve().parent.parent
    input_file = _technical_dir / "data" / "raw" / "eurostat" / "gfs_2024_h1.tsv.gz"
    output_dir = _technical_dir / "data"

    # Create parser
    parser = EurostatCOFOGParser(input_file, output_dir)

    logger.info("🚀 Starting Eurostat COFOG parsing...")
    logger.info(f"Input file: {input_file}")
    logger.info(f"Output directory: {parser.processed_dir}")

    # Read and process data
    df = parser.read_eurostat_data()

    if len(df) == 0:
        logger.error("No data loaded. Exiting.")
        return

    # Clean data
    df_clean = parser.clean_and_standardize_data(df)

    # Process all countries
    results = parser.process_all_countries(df_clean)

    # Create master dataset
    master_df = parser.create_master_dataset(df_clean)

    # Generate report
    report = parser.generate_processing_report(df_clean, results)

    logger.info("✅ Eurostat COFOG parsing complete!")
    logger.info(f"Processed {len(results)} EU countries")
    logger.info(f"Master dataset: {master_df.shape[0]:,} observations")

    return results, master_df, report

if __name__ == "__main__":
    results, master_df, report = main()