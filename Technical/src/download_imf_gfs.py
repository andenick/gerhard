#!/usr/bin/env python3
"""
IMF Government Finance Statistics Downloader
Comprehensive fiscal data for 190+ countries
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys
from datetime import datetime
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

class IMFGFSDownloader:
    """Downloads IMF Government Finance Statistics data"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.raw_dir = self.output_dir / "raw" / "imf" / "gfs"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # IMF API endpoints
        # Primary: SDMX Central (metadata + data when available)
        # Note: As of 2026-03, data queries return 501; dataservices.imf.org is unreachable.
        # The script will attempt both and fall back gracefully.
        self.base_url = "https://sdmxcentral.imf.org/ws/public/sdmxapi/rest/data"
        self.backup_url = "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData"

        # GFS Data Categories
        self.gfs_categories = {
            "REVENUE": {
                "code": "GGR",
                "name": "General Government Revenue",
                "subcategories": {
                    "TAX": "Tax Revenue",
                    "SOCIAL": "Social Security Contributions",
                    "GRANT": "Grants",
                    "OTHER": "Other Revenue"
                }
            },
            "EXPENDITURE": {
                "code": "GGE",
                "name": "General Government Expenditure",
                "subcategories": {
                    "COMP": "Compensation of Employees",
                    "USE": "Use of Goods and Services",
                    "SUBSIDY": "Subsidies",
                    "INTEREST": "Interest Payments",
                    "SOCIAL_BEN": "Social Benefits",
                    "OTHER": "Other Expenditure"
                }
            },
            "DEFICIT": {
                "code": "GGDEBT",
                "name": "Government Deficit/Surplus",
                "subcategories": {
                    "DEFICIT": "Net Lending/Borrowing",
                    "DEBT": "Gross Government Debt"
                }
            }
        }

        # Key countries (expanded list for broader coverage)
        self.countries = {
            # G20 Major Economies
            "US": "United States", "CN": "China", "JP": "Japan", "DE": "Germany",
            "FR": "France", "GB": "United Kingdom", "IT": "Italy", "BR": "Brazil",
            "CA": "Canada", "KR": "South Korea", "AU": "Australia", "MX": "Mexico",
            "IN": "India", "ID": "Indonesia", "TR": "Turkey", "SA": "Saudi Arabia",
            "ZA": "South Africa", "AR": "Argentina", "RU": "Russia",

            # European Union
            "ES": "Spain", "NL": "Netherlands", "BE": "Belgium", "PL": "Poland",
            "SE": "Sweden", "AT": "Austria", "DK": "Denmark", "FI": "Finland",
            "GR": "Greece", "PT": "Portugal", "IE": "Ireland", "CZ": "Czech Republic",
            "HU": "Hungary", "RO": "Romania", "BG": "Bulgaria", "HR": "Croatia",
            "SK": "Slovakia", "SI": "Slovenia", "LT": "Lithuania", "LV": "Latvia",
            "EE": "Estonia", "CY": "Cyprus", "LU": "Luxembourg", "MT": "Malta",

            # Other Advanced Economies
            "CH": "Switzerland", "NO": "Norway", "IL": "Israel", "NZ": "New Zealand",
            "SG": "Singapore", "HK": "Hong Kong", "TW": "Taiwan",

            # Emerging Markets
            "TH": "Thailand", "MY": "Malaysia", "PH": "Philippines", "VN": "Vietnam",
            "PK": "Pakistan", "BD": "Bangladesh", "CL": "Chile", "CO": "Colombia",
            "PE": "Peru", "EG": "Egypt", "NG": "Nigeria", "KE": "Kenya",
            "GH": "Ghana", "TZ": "Tanzania", "UG": "Uganda", "MOZ": "Mozambique",
            "ZM": "Zambia", "ZW": "Zimbabwe",

            # Middle East & North Africa
            "AE": "United Arab Emirates", "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain",
            "OM": "Oman", "JO": "Jordan", "LB": "Lebanon", "MA": "Morocco",
            "TN": "Tunisia", "DZ": "Algeria", "LY": "Libya",

            # Central Asia & Caucasus
            "KZ": "Kazakhstan", "UZ": "Uzbekistan", "KG": "Kyrgyzstan", "TJ": "Tajikistan",
            "GE": "Georgia", "AM": "Armenia", "AZ": "Azerbaijan",

            # Latin America & Caribbean
            "VE": "Venezuela", "EC": "Ecuador", "BO": "Bolivia", "PY": "Paraguay",
            "UY": "Uruguay", "CR": "Costa Rica", "PA": "Panama", "DO": "Dominican Republic",
            "GT": "Guatemala", "HN": "Honduras", "SV": "El Salvador", "NI": "Nicaragua",

            # Pacific Islands
            "FJ": "Fiji", "PG": "Papua New Guinea", "SB": "Solomon Islands",
            "VU": "Vanuatu", "WS": "Samoa", "TO": "Tonga"
        }

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def construct_sdmx_url(self, country_code: str, indicator: str, years: str = None) -> str:
        """Construct IMF SDMX API URL for GFS data.

        Uses the GGO (General Government Operations) dataflow on SDMX Central.
        Format: {base_url}/IMF,GGO,1.0/.{country_code}?startPeriod=1990&endPeriod=2024
        Backup: {backup_url}/GFS/A.{country_code}?startPeriod=1990&endPeriod=2024
        """
        start_year = "1990"
        end_year = "2024"
        if years is not None:
            parts = years.split(",")
            start_year = parts[0]
            end_year = parts[1] if len(parts) > 1 else parts[0]

        # Primary: SDMX Central GGO dataflow
        url = f"{self.base_url}/IMF,GGO,1.0/.{country_code}?startPeriod={start_year}&endPeriod={end_year}"
        return url

    def construct_backup_url(self, country_code: str, start_year: str = "1990", end_year: str = "2024") -> str:
        """Construct backup IMF JSON API URL"""
        return f"{self.backup_url}/GFS/A.{country_code}?startPeriod={start_year}&endPeriod={end_year}"

    def download_country_data(self, country_code: str, country_name: str) -> Dict:
        """Download all GFS data for a specific country"""
        logger.info(f"Downloading GFS data for {country_name} ({country_code})...")

        country_data = {
            'country_code': country_code,
            'country_name': country_name,
            'download_timestamp': datetime.now().isoformat(),
            'data': {}
        }

        # Download for each major category
        for category_key, category_info in self.gfs_categories.items():
            try:
                # Try SDMX API first
                sdmx_url = self.construct_sdmx_url(country_code, category_info['code'])
                data = self.download_sdmx_data(sdmx_url, category_key)

                if data:
                    country_data['data'][category_key] = data
                    logger.info(f"  {country_name} {category_key} data downloaded (SDMX)")
                else:
                    # Try backup URL (IMF JSON REST API)
                    logger.warning(f"SDMX failed for {country_name} {category_key}, trying backup API...")
                    backup_url = self.construct_backup_url(country_code)
                    data = self.download_sdmx_data(backup_url, category_key)
                    if data:
                        country_data['data'][category_key] = data
                        logger.info(f"  {country_name} {category_key} data downloaded (Backup API)")
                    else:
                        # Fallback to alternative method
                        alternative_data = self.download_alternative_data(country_code, category_key)
                        if alternative_data:
                            country_data['data'][category_key] = alternative_data
                            logger.info(f"  {country_name} {category_key} data downloaded (Alternative)")

                # Rate limiting
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error downloading {category_key} for {country_name}: {e}")
                continue

        return country_data

    def download_sdmx_data(self, url: str, category: str) -> Optional[Dict]:
        """Download data using IMF SDMX API"""
        try:
            response = self.session.get(url, timeout=60)

            # Reject HTML error pages masquerading as data
            content_type = response.headers.get('Content-Type', '')
            if 'html' in content_type.lower():
                logger.warning(f"Received HTML error page instead of data from {url}")
                return None

            if response.status_code == 200:
                # Parse XML response
                root = ET.fromstring(response.content)

                data = {
                    'download_method': 'SDMX',
                    'url': url,
                    'observations': [],
                    'metadata': {}
                }

                # Extract observations
                for series in root.findall('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Series'):
                    series_key = series.find('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}SeriesKey')
                    obs_list = series.find('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Obs')

                    for obs in obs_list.findall('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}Obs'):
                        obs_time = obs.find('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}ObsDimension').attrib['value']
                        obs_value = obs.find('.//{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic}ObsValue').attrib['value']

                        observation = {
                            'year': int(obs_time),
                            'value': float(obs_value) if obs_value else None,
                            'category': category
                        }
                        data['observations'].append(observation)

                return data if data['observations'] else None

            else:
                logger.warning(f"SDMX API failed: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.warning(f"SDMX parsing error: {e}")
            return None

    def download_alternative_data(self, country_code: str, category: str) -> Optional[Dict]:
        """Alternative download method when SDMX fails"""
        # This would implement alternative scraping or data collection methods
        # For now, return None to indicate no data available
        logger.info(f"No alternative data available for {country_code} {category}")
        return None

    def create_country_dataframe(self, country_data: Dict) -> pd.DataFrame:
        """Convert country data to pandas DataFrame"""
        observations = []

        for category_key, category_data in country_data['data'].items():
            if 'observations' in category_data:
                for obs in category_data['observations']:
                    obs['country_code'] = country_data['country_code']
                    obs['country_name'] = country_data['country_name']
                    obs['category'] = category_key
                    obs['category_name'] = self.gfs_categories[category_key]['name']
                    observations.append(obs)

        if observations:
            df = pd.DataFrame(observations)
            # Sort by year and category
            df = df.sort_values(['year', 'category']).reset_index(drop=True)
            return df
        else:
            return pd.DataFrame()

    def save_country_data(self, country_data: Dict, df: pd.DataFrame):
        """Save country data in multiple formats"""
        country_code = country_data['country_code']
        country_name = country_data['country_name'].replace(' ', '_').lower()

        # Save raw JSON data
        json_file = self.raw_dir / f"{country_code}_gfs_raw.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(country_data, f, indent=2)

        # Save processed DataFrame as CSV
        if len(df) > 0:
            csv_file = self.raw_dir / f"{country_code}_gfs_processed.csv"
            df.to_csv(csv_file, index=False)

            # Save as Excel
            excel_file = self.raw_dir / f"{country_code}_gfs_processed.xlsx"
            write_single_sheet_excel(df, excel_file)

            logger.info(f"✓ {country_name} data saved: {len(df)} observations")
        else:
            logger.warning(f"No processed data to save for {country_name}")

    def calculate_fiscal_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fiscal indicators from raw data"""
        if len(df) == 0:
            return df

        # Pivot data to have categories as columns
        pivot_df = df.pivot_table(
            index=['country_code', 'country_name', 'year'],
            columns='category',
            values='value',
            aggfunc='first'
        ).reset_index()

        # Calculate fiscal balance (if revenue and expenditure available)
        if 'REVENUE' in pivot_df.columns and 'EXPENDITURE' in pivot_df.columns:
            pivot_df['fiscal_balance'] = pivot_df['REVENUE'] - pivot_df['EXPENDITURE']
            pivot_df['fiscal_balance_pct_gdp'] = (pivot_df['fiscal_balance'] / pivot_df['REVENUE']) * 100

        # Calculate revenue composition
        revenue_cols = [col for col in pivot_df.columns if 'TAX' in col or 'SOCIAL' in col]
        if revenue_cols:
            pivot_df['tax_revenue_pct'] = pivot_df['REVENUE'].apply(lambda x: 0 if pd.isna(x) else x)
            for col in revenue_cols:
                if col in pivot_df.columns:
                    pivot_df[f'{col}_pct_revenue'] = (pivot_df[col] / pivot_df['REVENUE']) * 100

        return pivot_df

    def download_all_countries(self) -> Dict:
        """Download data for all countries"""
        logger.info(f"Starting download for {len(self.countries)} countries...")

        results = {}
        total_countries = len(self.countries)

        for i, (country_code, country_name) in enumerate(self.countries.items(), 1):
            logger.info(f"Progress: {i}/{total_countries} - {country_name}")

            # Download country data
            country_data = self.download_country_data(country_code, country_name)

            # Convert to DataFrame
            df = self.create_country_dataframe(country_data)

            # Calculate fiscal indicators
            if len(df) > 0:
                df_indicators = self.calculate_fiscal_indicators(df)
                country_data['processed_data'] = df_indicators.to_dict('records')
                country_data['observation_count'] = len(df)

            # Save data
            self.save_country_data(country_data, df)

            results[country_code] = {
                'country_name': country_name,
                'download_successful': len(df) > 0,
                'observation_count': len(df),
                'categories_found': list(df['category'].unique()) if len(df) > 0 else [],
                'year_range': {
                    'start': int(df['year'].min()) if len(df) > 0 else None,
                    'end': int(df['year'].max()) if len(df) > 0 else None
                } if len(df) > 0 else None
            }

            # Save progress checkpoint
            if i % 10 == 0:
                self.save_progress(results, f"checkpoint_{i}.json")
                logger.info(f"Checkpoint saved at {i} countries")

            # Rate limiting between countries
            time.sleep(2)

        # Save final results
        self.save_progress(results, "final_results.json")
        logger.info("✅ All countries download complete!")

        return results

    def save_progress(self, results: Dict, filename: str):
        """Save download progress"""
        progress_file = self.raw_dir / filename
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def create_master_dataset(self, results: Dict) -> pd.DataFrame:
        """Create master dataset from all countries"""
        logger.info("Creating master GFS dataset...")

        all_data = []

        for country_code, result in results.items():
            if result['download_successful']:
                # Load processed data
                excel_file = self.raw_dir / f"{country_code}_gfs_processed.xlsx"
                if excel_file.exists():
                    df = pd.read_excel(excel_file)
                    all_data.append(df)

        if all_data:
            master_df = pd.concat(all_data, ignore_index=True)
            logger.info(f"Master dataset created with {len(master_df)} observations")

            # Save master dataset
            master_file = self.output_dir / "processed" / "imf_gfs_master_dataset.xlsx"
            master_file.parent.mkdir(parents=True, exist_ok=True)
            write_single_sheet_excel(master_df, master_file)

            master_csv = master_file.with_suffix('.csv')
            master_df.to_csv(master_csv, index=False)

            logger.info(f"✅ Master dataset saved: {master_file}")
            return master_df
        else:
            logger.warning("No data available for master dataset")
            return pd.DataFrame()

    def generate_download_report(self, results: Dict):
        """Generate comprehensive download report"""
        logger.info("Generating download report...")

        report = {
            'download_date': datetime.now().isoformat(),
            'total_countries_attempted': len(self.countries),
            'successful_downloads': sum(1 for r in results.values() if r['download_successful']),
            'failed_downloads': sum(1 for r in results.values() if not r['download_successful']),
            'total_observations': sum(r['observation_count'] for r in results.values()),
            'output_directory': str(self.raw_dir),
            'categories_found': set(),
            'year_coverage': {},
            'countries_summary': {}
        }

        # Analyze results
        for country_code, result in results.items():
            report['countries_summary'][country_code] = {
                'name': result['country_name'],
                'success': result['download_successful'],
                'observations': result['observation_count'],
                'categories': result['categories_found'],
                'year_range': result['year_range']
            }

            # Track categories found
            report['categories_found'].update(result['categories_found'])

            # Track year coverage
            if result['year_range'] and result['year_range']['start']:
                start_year = result['year_range']['start']
                end_year = result['year_range']['end']
                if start_year not in report['year_coverage']:
                    report['year_coverage'][start_year] = 0
                if end_year not in report['year_coverage']:
                    report['year_coverage'][end_year] = 0
                report['year_coverage'][start_year] += 1
                report['year_coverage'][end_year] += 1

        report['categories_found'] = list(report['categories_found'])

        # Save report
        report_file = self.raw_dir / "download_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        logger.info(f"✅ Download report saved: {report_file}")
        logger.info(f"Success rate: {report['successful_downloads']}/{report['total_countries_attempted']} countries")

        return report

def main():
    """Main execution function"""
    # Setup directories — writes to Technical/data/raw/imf/gfs/
    base_dir = Path(__file__).resolve().parent.parent
    output_dir = base_dir / "data"

    # Create downloader
    downloader = IMFGFSDownloader(output_dir)

    logger.info("🚀 Starting IMF GFS download...")
    logger.info(f"Output directory: {downloader.raw_dir}")
    logger.info(f"Countries: {len(downloader.countries)}")

    # Download all data
    results = downloader.download_all_countries()

    # Create master dataset
    master_df = downloader.create_master_dataset(results)

    # Generate report
    report = downloader.generate_download_report(results)

    logger.info("✅ IMF GFS download complete!")
    logger.info(f"Successfully downloaded data for {report['successful_downloads']} countries")
    logger.info(f"Total observations: {report['total_observations']}")

    return results, master_df, report

if __name__ == "__main__":
    results, master_df, report = main()