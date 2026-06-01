#!/usr/bin/env python3
"""
WID.world Integration Script
Maps complex WID variable codes and extracts international distributional data
"""

import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
from datetime import datetime
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

class WIDDataIntegrator:
    """Integrates WID.world inequality data into fiscal analysis"""

    def __init__(self, input_dir: Path, output_dir: Path):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.wid_dir = self.input_dir / "raw" / "wid"
        self.processed_dir = self.output_dir / "processed" / "wid_inequality"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # WID variable code mappings
        self.wid_variable_mappings = {
            # Income share variables
            "sfiinc": {
                "name": "Share of pre-tax fiscal income",
                "description": "Share of total pre-tax fiscal income held by group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p0p100", "p90p100", "p95p100", "p99p100"]
            },
            "sptinc": {
                "name": "Share of post-tax fiscal income",
                "description": "Share of total post-tax fiscal income held by group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p0p100", "p90p100", "p95p100", "p99p100"]
            },
            "spdispinc": {
                "name": "Share of disposable income",
                "description": "Share of total disposable income held by group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p0p100", "p90p100", "p95p100", "p99p100"]
            },

            # Wealth share variables
            "shweal": {
                "name": "Share of wealth",
                "description": "Share of total net private wealth held by group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p0p100", "p90p100", "p95p100", "p99p100"]
            },

            # Average income/wealth variables
            "afiinc": {
                "name": "Average pre-tax fiscal income",
                "description": "Average pre-tax fiscal income for group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p99p100", "p100"]
            },
            "aptinc": {
                "name": "Average post-tax fiscal income",
                "description": "Average post-tax fiscal income for group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p99p100", "p100"]
            },

            # Tax rates
            "taxrate": {
                "name": "Average tax rate",
                "description": "Average tax rate for income group",
                "percentiles": ["p0p1", "p0p10", "p0p20", "p0p50", "p0p90", "p0p99", "p99p100", "p100"]
            }
        }

        # Priority countries with good data coverage
        self.priority_countries = {
            # G7 + major economies
            "US": "United States", "JP": "Japan", "DE": "Germany", "FR": "France",
            "GB": "United Kingdom", "IT": "Italy", "CA": "Canada", "AU": "Australia",

            # Other OECD with good coverage
            "ES": "Spain", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
            "DK": "Denmark", "FI": "Finland", "CH": "Switzerland", "AT": "Austria",
            "BE": "Belgium", "IE": "Ireland", "NZ": "New Zealand", "KR": "South Korea",

            # Major emerging economies
            "CN": "China", "IN": "India", "BR": "Brazil", "ZA": "South Africa",
            "MX": "Mexico", "RU": "Russia", "TR": "Turkey", "ID": "Indonesia",

            # Latin America
            "AR": "Argentina", "CL": "Chile", "CO": "Colombia", "PE": "Peru",

            # Other notable economies
            "SG": "Singapore", "IL": "Israel", "GR": "Greece", "PT": "Portugal"
        }

        # Country code mappings (WID uses 2-letter ISO codes)
        self.country_code_mapping = {
            "US": "US", "GB": "UK", "DE": "DE", "FR": "FR", "IT": "IT",
            "ES": "ES", "NL": "NL", "SE": "SE", "NO": "NO", "DK": "DK",
            "FI": "FI", "CH": "CH", "AT": "AT", "BE": "BE", "IE": "IE",
            "PT": "PT", "GR": "GR", "CA": "CA", "AU": "AU", "NZ": "NZ",
            "JP": "JP", "KR": "KR", "CN": "CN", "IN": "IN", "BR": "BR",
            "ZA": "ZA", "MX": "MX", "RU": "RU", "TR": "TR", "ID": "ID",
            "AR": "AR", "CL": "CL", "CO": "CO", "PE": "PE", "SG": "SG",
            "IL": "IL", "PL": "PL", "CZ": "CZ", "HU": "HU", "RO": "RO"
        }

    def load_wid_metadata(self) -> Dict:
        """Load WID metadata and country information"""
        logger.info("Loading WID metadata...")

        metadata_file = self.wid_dir / "WID_countries.csv"
        if not metadata_file.exists():
            logger.warning(f"WID metadata file not found: {metadata_file}")
            return {}

        try:
            df = pd.read_csv(metadata_file)
            metadata = {
                'countries': df.to_dict('records'),
                'total_countries': len(df)
            }
            logger.info(f"✅ Loaded metadata for {len(df)} countries/regions")
            return metadata
        except Exception as e:
            logger.error(f"Error loading WID metadata: {e}")
            return {}

    def parse_wid_variable_code(self, variable_code: str) -> Dict:
        """Parse WID variable code to extract components"""
        # Example: "sptinc992j" -> sptinc (variable), 992 (percentile), j (age group)

        parsed = {
            'variable_base': '',
            'percentile_code': '',
            'age_group': '',
            'population_group': '',
            'year': ''
        }

        try:
            # Extract variable base (letters at start)
            import re
            match = re.match(r'^([a-z]+)(\d+)([a-z]*)', variable_code)
            if match:
                parsed['variable_base'] = match.group(1)
                parsed['percentile_code'] = match.group(2)
                parsed['age_group'] = match.group(3)

            # Map percentile codes to readable names
            percentile_map = {
                "0": "p0p100", "1": "p0p1", "10": "p0p10", "20": "p0p20",
                "50": "p0p50", "90": "p0p90", "99": "p0p99", "100": "p100",
                "90100": "p90p100", "95100": "p95p100", "99100": "p99p100"
            }

            if parsed['percentile_code'] in percentile_map:
                parsed['percentile_name'] = percentile_map[parsed['percentile_code']]

        except Exception as e:
            logger.warning(f"Error parsing variable code {variable_code}: {e}")

        return parsed

    def find_country_data_files(self, country_code: str) -> List[Path]:
        """Find WID data files for a specific country"""
        country_files = []

        # Look for various possible file naming patterns
        patterns = [
            f"WID_data_{country_code}*.csv",
            f"WID_data_{country_code.lower()}*.csv",
            f"*{country_code}*.csv",
            f"*{country_code.lower()}*.csv"
        ]

        for pattern in patterns:
            files = list(self.wid_dir.glob(pattern))
            country_files.extend(files)

        # Remove duplicates
        country_files = list(set(country_files))
        logger.info(f"Found {len(country_files)} data files for {country_code}")
        return country_files

    def load_country_data(self, country_code: str, country_files: List[Path]) -> pd.DataFrame:
        """Load and combine all WID data for a country"""
        all_data = []

        for file_path in country_files:
            try:
                logger.info(f"Loading {file_path.name}...")
                df = pd.read_csv(file_path)

                # Add file metadata
                df['source_file'] = file_path.name
                df['country_code'] = country_code

                # Parse variable codes
                if 'Variable' in df.columns:
                    parsed_vars = df['Variable'].apply(self.parse_wid_variable_code)
                    var_df = pd.DataFrame(parsed_vars.tolist())
                    df = pd.concat([df, var_df], axis=1)

                all_data.append(df)

            except Exception as e:
                logger.warning(f"Error loading {file_path}: {e}")
                continue

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"✅ Loaded {len(combined_df)} observations for {country_code}")
            return combined_df
        else:
            logger.warning(f"No data loaded for {country_code}")
            return pd.DataFrame()

    def filter_relevant_variables(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter for relevant inequality variables"""
        if len(df) == 0:
            return df

        # List of relevant variable bases
        relevant_variables = list(self.wid_variable_mappings.keys())

        # Filter by variable base
        if 'variable_base' in df.columns:
            filtered_df = df[df['variable_base'].isin(relevant_variables)]
        elif 'Variable' in df.columns:
            # Fallback: filter by variable name patterns
            pattern = '|'.join(relevant_variables)
            mask = df['Variable'].str.contains(pattern, case=False, na=False)
            filtered_df = df[mask]
        else:
            logger.warning("No variable columns found for filtering")
            filtered_df = df

        logger.info(f"Filtered to {len(filtered_df)} relevant observations")
        return filtered_df

    def clean_country_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize country data"""
        if len(df) == 0:
            return df

        # Clean numeric columns
        numeric_cols = ['Value', 'Year']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Filter out extreme values and missing data
        if 'Value' in df.columns:
            # Remove negative values for shares and positive-only variables
            share_variables = ['sfiinc', 'sptinc', 'spdispinc', 'shweal']
            if 'variable_base' in df.columns:
                share_mask = df['variable_base'].isin(share_variables)
                df.loc[share_mask, 'Value'] = df.loc[share_mask, 'Value'].clip(lower=0, upper=100)

            # Remove extreme outliers
            df = df[(df['Value'].abs() < 1000) | df['Value'].isna()]

        # Convert year
        if 'Year' in df.columns:
            df = df.dropna(subset=['Year'])
            df['Year'] = df['Year'].astype(int)

        # Remove rows with missing essential data
        essential_cols = ['Year', 'Value']
        if 'percentile_name' in df.columns:
            essential_cols.append('percentile_name')

        df = df.dropna(subset=essential_cols)

        logger.info(f"✅ Cleaned data: {len(df)} observations remaining")
        return df

    def create_country_summary(self, df: pd.DataFrame, country_code: str) -> Dict:
        """Create summary statistics for a country"""
        if len(df) == 0:
            return {'country_code': country_code, 'status': 'No data'}

        summary = {
            'country_code': country_code,
            'country_name': self.priority_countries.get(country_code, country_code),
            'total_observations': len(df),
            'year_range': {
                'start': int(df['Year'].min()),
                'end': int(df['Year'].max()),
                'span': int(df['Year'].max() - df['Year'].min())
            },
            'variables_found': [],
            'percentiles_covered': set(),
            'latest_data': {}
        }

        # Variables found
        if 'variable_base' in df.columns:
            variables = df['variable_base'].unique()
            for var in variables:
                if var in self.wid_variable_mappings:
                    var_info = self.wid_variable_mappings[var].copy()
                    var_info['observations'] = len(df[df['variable_base'] == var])
                    summary['variables_found'].append(var_info)

        # Percentiles covered
        if 'percentile_name' in df.columns:
            summary['percentiles_covered'] = list(df['percentile_name'].dropna().unique())

        # Latest data by variable
        latest_year = df['Year'].max()
        latest_data = df[df['Year'] == latest_year]

        for _, row in latest_data.iterrows():
            var_base = row.get('variable_base', '')
            percentile = row.get('percentile_name', '')
            value = row.get('Value', None)

            if var_base and percentile and pd.notna(value):
                if var_base not in summary['latest_data']:
                    summary['latest_data'][var_base] = {}
                summary['latest_data'][var_base][percentile] = float(value)

        # Convert set to list for JSON serialization
        summary['percentiles_covered'] = list(summary['percentiles_covered'])

        return summary

    def save_country_data(self, df: pd.DataFrame, country_code: str, summary: Dict):
        """Save processed country data"""
        country_name = self.priority_countries.get(country_code, country_code).replace(' ', '_').lower()

        # Save processed data
        if len(df) > 0:
            # Excel format
            excel_file = self.processed_dir / f"{country_code}_wid_inequality.xlsx"
            write_single_sheet_excel(df, excel_file)

            # CSV format
            csv_file = self.processed_dir / f"{country_code}_wid_inequality.csv"
            df.to_csv(csv_file, index=False)

            logger.info(f"✅ Saved {country_code} data: {len(df)} observations")

        # Save summary
        summary_file = self.processed_dir / f"{country_code}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

    def integrate_all_countries(self) -> Dict:
        """Integrate WID data for all priority countries"""
        logger.info(f"Starting WID integration for {len(self.priority_countries)} priority countries...")

        results = {}
        metadata = self.load_wid_metadata()

        for i, (country_code, country_name) in enumerate(self.priority_countries.items(), 1):
            logger.info(f"Processing {i}/{len(self.priority_countries)}: {country_name} ({country_code})")

            # Find data files
            country_files = self.find_country_data_files(country_code)

            if not country_files:
                logger.warning(f"No data files found for {country_name}")
                results[country_code] = {
                    'country_name': country_name,
                    'status': 'No files found',
                    'data_available': False
                }
                continue

            # Load data
            raw_df = self.load_country_data(country_code, country_files)

            if len(raw_df) == 0:
                logger.warning(f"No data loaded for {country_name}")
                results[country_code] = {
                    'country_name': country_name,
                    'status': 'No data loaded',
                    'data_available': False
                }
                continue

            # Process data
            filtered_df = self.filter_relevant_variables(raw_df)
            clean_df = self.clean_country_data(filtered_df)

            if len(clean_df) == 0:
                logger.warning(f"No data remaining after cleaning for {country_name}")
                results[country_code] = {
                    'country_name': country_name,
                    'status': 'No data after cleaning',
                    'data_available': False
                }
                continue

            # Create summary
            summary = self.create_country_summary(clean_df, country_code)
            summary['data_available'] = True
            summary['status'] = 'Success'

            # Save data
            self.save_country_data(clean_df, country_code, summary)

            results[country_code] = summary

            logger.info(f"✅ {country_name} integration complete: {len(clean_df)} observations")

        # Save overall results
        results_file = self.processed_dir / "all_countries_summary.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        return results

    def create_master_dataset(self, results: Dict) -> pd.DataFrame:
        """Create master WID inequality dataset"""
        logger.info("Creating master WID inequality dataset...")

        all_data = []

        for country_code, result in results.items():
            if result.get('data_available', False):
                # Load processed data
                excel_file = self.processed_dir / f"{country_code}_wid_inequality.xlsx"
                if excel_file.exists():
                    df = pd.read_excel(excel_file)
                    all_data.append(df)

        if all_data:
            master_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Master dataset created with {len(master_df)} observations")

            # Save master dataset
            master_file = self.processed_dir / "wid_inequality_master_dataset.xlsx"
            write_single_sheet_excel(master_df, master_file)

            master_csv = master_file.with_suffix('.csv')
            master_df.to_csv(master_csv, index=False)

            logger.info(f"✅ Master dataset saved: {master_file}")
            return master_df
        else:
            logger.warning("No data available for master dataset")
            return pd.DataFrame()

    def generate_integration_report(self, results: Dict):
        """Generate comprehensive integration report"""
        logger.info("Generating WID integration report...")

        report = {
            'integration_date': datetime.now().isoformat(),
            'total_countries_attempted': len(self.priority_countries),
            'successful_integrations': sum(1 for r in results.values() if r.get('data_available', False)),
            'failed_integrations': sum(1 for r in results.values() if not r.get('data_available', False)),
            'output_directory': str(self.processed_dir),
            'countries_summary': {},
            'data_quality': {
                'variables_coverage': {},
                'temporal_coverage': {},
                'geographic_coverage': {}
            }
        }

        # Analyze results
        for country_code, result in results.items():
            report['countries_summary'][country_code] = {
                'name': result.get('country_name', country_code),
                'success': result.get('data_available', False),
                'status': result.get('status', 'Unknown'),
                'observations': result.get('total_observations', 0),
                'year_range': result.get('year_range', {}),
                'variables_found': len(result.get('variables_found', [])),
                'percentiles_covered': len(result.get('percentiles_covered', []))
            }

            # Track variable coverage
            for var_info in result.get('variables_found', []):
                var_name = var_info.get('name', 'Unknown')
                if var_name not in report['data_quality']['variables_coverage']:
                    report['data_quality']['variables_coverage'][var_name] = 0
                report['data_quality']['variables_coverage'][var_name] += 1

            # Track temporal coverage
            year_range = result.get('year_range', {})
            if year_range:
                start_year = year_range.get('start')
                end_year = year_range.get('end')
                if start_year and end_year:
                    report['data_quality']['temporal_coverage'][country_code] = {
                        'start': start_year,
                        'end': end_year,
                        'span': end_year - start_year
                    }

        # Calculate coverage statistics
        successful_countries = sum(1 for r in results.values() if r.get('data_available', False))
        if successful_countries > 0:
            report['data_quality']['average_data_span'] = np.mean([
                r['year_range'].get('span', 0) for r in results.values()
                if r.get('year_range') and r.get('data_available', False)
            ])

        # Save report
        report_file = self.processed_dir / "integration_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        logger.info(f"✅ Integration report saved: {report_file}")
        logger.info(f"Success rate: {report['successful_integrations']}/{report['total_countries_attempted']} countries")

        return report

def main():
    """Main execution function"""
    # File paths
    base_dir = Path(__file__).resolve().parent.parent / "data"
    input_dir = base_dir
    output_dir = base_dir

    # Create integrator
    integrator = WIDDataIntegrator(input_dir, output_dir)

    logger.info("🚀 Starting WID.world data integration...")
    logger.info(f"Input directory: {integrator.wid_dir}")
    logger.info(f"Output directory: {integrator.processed_dir}")
    logger.info(f"Priority countries: {len(integrator.priority_countries)}")

    # Integrate all countries
    results = integrator.integrate_all_countries()

    # Create master dataset
    master_df = integrator.create_master_dataset(results)

    # Generate report
    report = integrator.generate_integration_report(results)

    logger.info("✅ WID.world integration complete!")
    logger.info(f"Successfully integrated {report['successful_integrations']} countries")
    if len(master_df) > 0:
        logger.info(f"Master dataset: {len(master_df)} observations")

    return results, master_df, report

if __name__ == "__main__":
    results, master_df, report = main()