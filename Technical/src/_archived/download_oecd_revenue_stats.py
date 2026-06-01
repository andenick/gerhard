#!/usr/bin/env python3
"""
OECD Revenue Statistics Downloader
Comprehensive tax structure data for 38+ OECD countries
"""

import requests
import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OECDRevenueDownloader:
    """Downloads OECD Revenue Statistics data"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.raw_dir = self.output_dir / "raw" / "oecd_revenue"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        # OECD API endpoints
        self.base_url = "https://stats.oecd.org/sdmx-json/data"
        self.dataset = "REV"

        # Tax categories (OECD classification)
        self.tax_categories = {
            "1000": "Taxes on income, profits and capital gains",
            "1100": "Individuals",
            "1200": "Corporations",
            "2000": "Social security contributions",
            "3000": "Taxes on payroll and workforce",
            "4000": "Taxes on property",
            "5110": "Value added taxes",
            "5121": "Excise taxes",
            "5200": "Taxes on international trade",
            "6000": "Other taxes"
        }

        # OECD countries
        self.oecd_countries = [
            "AUS", "AUT", "BEL", "CAN", "CHL", "COL", "CRI", "CZE", "DNK", "EST",
            "FIN", "FRA", "DEU", "GRC", "HUN", "ISL", "IRL", "ISR", "ITA", "JPN",
            "KOR", "LVA", "LTU", "LUX", "MEX", "NLD", "NZL", "NOR", "POL", "PRT",
            "SVK", "SVN", "ESP", "SWE", "CHE", "TUR", "GBR", "USA"
        ]

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def construct_api_url(self, country: str, tax_category: str = None) -> str:
        """Construct OECD API URL"""
        if tax_category:
            structure = f"{self.dataset}.{country}.{tax_category}._T._Z._T._T"
        else:
            structure = f"{self.dataset}.{country}._T._T._Z._T._T"

        return f"{self.base_url}/{structure}/all"

    def download_country_data(self, country: str) -> Optional[Dict]:
        """Download data for a specific country"""
        try:
            # Download total tax revenue first
            url = self.construct_api_url(country)
            logger.info(f"Downloading {country} total tax revenue...")

            response = self.session.get(url, timeout=60)
            if response.status_code == 200:
                data = response.json()

                # Save raw data
                output_file = self.raw_dir / f"{country}_total_tax_revenue.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

                logger.info(f"✓ {country} total data saved ({len(str(data))} bytes)")
                return data
            else:
                logger.warning(f"Failed to download {country}: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading {country}: {e}")
            return None

    def download_tax_breakdown(self, country: str) -> Dict[str, Dict]:
        """Download detailed tax breakdown for a country"""
        breakdown_data = {}

        for category_code, category_name in self.tax_categories.items():
            try:
                url = self.construct_api_url(country, category_code)
                logger.info(f"Downloading {country} {category_name}...")

                response = self.session.get(url, timeout=60)
                if response.status_code == 200:
                    data = response.json()

                    # Save category data
                    output_file = self.raw_dir / f"{country}_tax_category_{category_code}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)

                    breakdown_data[category_code] = data
                    logger.info(f"✓ {country} {category_code} saved")
                    time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.warning(f"Error downloading {country} {category_code}: {e}")
                continue

        return breakdown_data

    def process_json_to_dataframe(self, data: Dict, data_type: str = "total") -> pd.DataFrame:
        """Convert OECD JSON data to pandas DataFrame"""
        if not data or 'dataSets' not in data:
            return pd.DataFrame()

        try:
            # Extract time series data
            observations = []

            for dataset in data['dataSets']:
                for series_idx, series in dataset['series'].items():
                    # Parse series key (country, tax category, etc.)
                    series_info = self.parse_series_key(series_idx, data)

                    # Extract observations
                    for period_idx, value in series['observations'].items():
                        year = int(data['structure']['dimensions']['observation'][0][int(period_idx)])

                        obs = {
                            'country': series_info.get('country'),
                            'tax_category': series_info.get('tax_category'),
                            'tax_category_name': series_info.get('tax_category_name'),
                            'year': year,
                            'value': value[0],
                            'unit': series_info.get('unit', '%GDP'),
                            'data_type': data_type
                        }
                        observations.append(obs)

            return pd.DataFrame(observations)

        except Exception as e:
            logger.error(f"Error processing JSON to DataFrame: {e}")
            return pd.DataFrame()

    def parse_series_key(self, series_key: str, data: Dict) -> Dict:
        """Parse OECD series key to extract dimensions"""
        try:
            # Split series key to get dimension indices
            key_parts = series_key.split(':')

            # Get dimension indices from structure
            dimensions = data['structure']['dimensions']['series']

            info = {}

            # Country (first dimension)
            if len(key_parts) > 0:
                country_idx = int(key_parts[0])
                if 'values' in dimensions[0] and len(dimensions[0]['values']) > country_idx:
                    info['country'] = dimensions[0]['values'][country_idx]['id']

            # Tax category (second dimension)
            if len(key_parts) > 1:
                category_idx = int(key_parts[1])
                if 'values' in dimensions[1] and len(dimensions[1]['values']) > category_idx:
                    category_id = dimensions[1]['values'][category_idx]['id']
                    info['tax_category'] = category_id
                    info['tax_category_name'] = self.tax_categories.get(category_id, category_id)

            # Unit (typically %GDP)
            if len(key_parts) > 3:
                unit_idx = int(key_parts[3])
                if 'values' in dimensions[3] and len(dimensions[3]['values']) > unit_idx:
                    info['unit'] = dimensions[3]['values'][unit_idx]['id']

            return info

        except Exception as e:
            logger.warning(f"Error parsing series key: {e}")
            return {}

    def download_all_countries(self):
        """Download data for all OECD countries"""
        logger.info(f"Starting download for {len(self.oecd_countries)} OECD countries...")

        results = {}

        for i, country in enumerate(self.oecd_countries, 1):
            logger.info(f"Progress: {i}/{len(self.oecd_countries)} - {country}")

            # Download total tax revenue
            total_data = self.download_country_data(country)

            # Download detailed breakdown
            breakdown_data = self.download_tax_breakdown(country)

            results[country] = {
                'total_data': total_data,
                'breakdown_data': breakdown_data,
                'categories_downloaded': list(breakdown_data.keys())
            }

            # Rate limiting between countries
            time.sleep(2)

            # Save progress checkpoint
            if i % 5 == 0:
                self.save_progress(results, f"checkpoint_{i}.json")
                logger.info(f"Checkpoint saved at {i} countries")

        # Save final results
        self.save_progress(results, "final_results.json")
        logger.info("✅ All OECD countries download complete!")

        return results

    def save_progress(self, results: Dict, filename: str):
        """Save download progress"""
        progress_file = self.raw_dir / filename
        try:
            # Convert data to JSON-serializable format
            serializable_results = {}
            for country, data in results.items():
                serializable_results[country] = {
                    'categories_downloaded': data.get('categories_downloaded', []),
                    'total_data_size': len(str(data.get('total_data', ''))),
                    'breakdown_count': len(data.get('breakdown_data', {}))
                }

            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_results, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def create_summary_statistics(self):
        """Create summary statistics of downloaded data"""
        logger.info("Creating summary statistics...")

        summary = {
            'download_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'countries_attempted': len(self.oecd_countries),
            'tax_categories': list(self.tax_categories.values()),
            'output_directory': str(self.raw_dir),
            'files_downloaded': []
        }

        # Count downloaded files
        for file_path in self.raw_dir.glob("*.json"):
            if file_path.name not in ['checkpoint.json', 'final_results.json']:
                file_size = file_path.stat().st_size
                summary['files_downloaded'].append({
                    'file': file_path.name,
                    'size_bytes': file_size
                })

        summary['total_files'] = len(summary['files_downloaded'])
        summary['total_size_mb'] = sum(f['size_bytes'] for f in summary['files_downloaded']) / (1024 * 1024)

        # Save summary
        summary_file = self.output_dir / "oecd_revenue_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"Summary saved: {summary_file}")
        logger.info(f"Total files: {summary['total_files']}, Size: {summary['total_size_mb']:.2f} MB")

        return summary

def main():
    """Main execution function"""
    # Setup directories
    base_dir = Path(__file__).resolve().parents[3] / "Technical" / "data"
    output_dir = base_dir / "downloads"

    # Create downloader
    downloader = OECDRevenueDownloader(output_dir)

    logger.info("🚀 Starting OECD Revenue Statistics download...")
    logger.info(f"Output directory: {downloader.raw_dir}")
    logger.info(f"Countries: {len(downloader.oecd_countries)} OECD members")

    # Download all data
    results = downloader.download_all_countries()

    # Create summary
    summary = downloader.create_summary_statistics()

    logger.info("✅ OECD Revenue Statistics download complete!")
    logger.info(f"Downloaded {summary['total_files']} files ({summary['total_size_mb']:.2f} MB)")

    return results, summary

if __name__ == "__main__":
    results, summary = main()