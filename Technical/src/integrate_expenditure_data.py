"""
Integrate Government Expenditure Data into Country Directories
Add World Bank expenditure data to all country Output/Data folders

Project: Gerhard - Expenditure Integration
"""

import pandas as pd
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, countries_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

WB_EXPENDITURE_DIR = raw_data_dir() / "worldbank" / "expenditure"
COUNTRIES_DIR = countries_dir()


class ExpenditureIntegrator:
    """Integrate expenditure data into country directories"""

    def __init__(self):
        # Load World Bank expenditure data
        self.wb_wide = None
        self.load_world_bank_data()

        # Get list of countries
        self.countries = self.get_country_list()

        # Create ISO2 to ISO3 mapping
        self.iso_mapping = self.create_iso_mapping()

    def load_world_bank_data(self):
        """Load World Bank expenditure data"""
        logger.info("=" * 60)
        logger.info("Loading World Bank Expenditure Data")
        logger.info("=" * 60)

        wide_file = WB_EXPENDITURE_DIR / "wb_expenditure_wide.csv"

        if not wide_file.exists():
            logger.error(f"World Bank data not found: {wide_file}")
            return False

        self.wb_wide = pd.read_csv(wide_file)
        logger.info(f"✅ Loaded: {len(self.wb_wide):,} observations")
        logger.info(f"   Countries: {self.wb_wide['country_code'].nunique()}")
        logger.info(f"   Years: {self.wb_wide['year'].min()}-{self.wb_wide['year'].max()}")

        return True

    def get_country_list(self):
        """Get list of existing country directories"""
        if not COUNTRIES_DIR.exists():
            logger.error(f"Countries directory not found: {COUNTRIES_DIR}")
            return []

        # Get all country directories (2 or 3 letter codes)
        countries = []
        for item in COUNTRIES_DIR.iterdir():
            if item.is_dir() and len(item.name) in [2, 3]:
                countries.append(item.name)

        logger.info(f"\n✅ Found {len(countries)} country directories")
        return sorted(countries)

    def create_iso_mapping(self):
        """Create mapping from ISO2 to ISO3 codes"""
        # Standard ISO 3166-1 mapping
        mapping = {
            'AD': 'AND', 'AE': 'ARE', 'AF': 'AFG', 'AG': 'ATG', 'AL': 'ALB',
            'AM': 'ARM', 'AO': 'AGO', 'AR': 'ARG', 'AT': 'AUT', 'AU': 'AUS',
            'AZ': 'AZE', 'BA': 'BIH', 'BB': 'BRB', 'BD': 'BGD', 'BE': 'BEL',
            'BF': 'BFA', 'BG': 'BGR', 'BH': 'BHR', 'BI': 'BDI', 'BJ': 'BEN',
            'BO': 'BOL', 'BR': 'BRA', 'BS': 'BHS', 'BT': 'BTN', 'BW': 'BWA',
            'BY': 'BLR', 'BZ': 'BLZ', 'CA': 'CAN', 'CD': 'COD', 'CF': 'CAF',
            'CG': 'COG', 'CH': 'CHE', 'CI': 'CIV', 'CL': 'CHL', 'CM': 'CMR',
            'CN': 'CHN', 'CO': 'COL', 'CR': 'CRI', 'CU': 'CUB', 'CV': 'CPV',
            'CY': 'CYP', 'CZ': 'CZE', 'DE': 'DEU', 'DJ': 'DJI', 'DK': 'DNK',
            'DM': 'DMA', 'DO': 'DOM', 'DZ': 'DZA', 'EC': 'ECU', 'EE': 'EST',
            'EG': 'EGY', 'ER': 'ERI', 'ES': 'ESP', 'ET': 'ETH', 'FI': 'FIN',
            'FJ': 'FJI', 'FM': 'FSM', 'FR': 'FRA', 'GA': 'GAB', 'GB': 'GBR',
            'GD': 'GRD', 'GE': 'GEO', 'GH': 'GHA', 'GM': 'GMB', 'GN': 'GIN',
            'GQ': 'GNQ', 'GR': 'GRC', 'GT': 'GTM', 'GW': 'GNB', 'GY': 'GUY',
            'HN': 'HND', 'HR': 'HRV', 'HT': 'HTI', 'HU': 'HUN', 'ID': 'IDN',
            'IE': 'IRL', 'IL': 'ISR', 'IN': 'IND', 'IQ': 'IRQ', 'IR': 'IRN',
            'IS': 'ISL', 'IT': 'ITA', 'JM': 'JAM', 'JO': 'JOR', 'JP': 'JPN',
            'KE': 'KEN', 'KG': 'KGZ', 'KH': 'KHM', 'KI': 'KIR', 'KM': 'COM',
            'KN': 'KNA', 'KP': 'PRK', 'KR': 'KOR', 'KW': 'KWT', 'KZ': 'KAZ',
            'LA': 'LAO', 'LB': 'LBN', 'LC': 'LCA', 'LI': 'LIE', 'LK': 'LKA',
            'LR': 'LBR', 'LS': 'LSO', 'LT': 'LTU', 'LU': 'LUX', 'LV': 'LVA',
            'LY': 'LBY', 'MA': 'MAR', 'MC': 'MCO', 'MD': 'MDA', 'ME': 'MNE',
            'MG': 'MDG', 'MH': 'MHL', 'MK': 'MKD', 'ML': 'MLI', 'MM': 'MMR',
            'MN': 'MNG', 'MR': 'MRT', 'MT': 'MLT', 'MU': 'MUS', 'MV': 'MDV',
            'MW': 'MWI', 'MX': 'MEX', 'MY': 'MYS', 'MZ': 'MOZ', 'NA': 'NAM',
            'NE': 'NER', 'NG': 'NGA', 'NI': 'NIC', 'NL': 'NLD', 'NO': 'NOR',
            'NP': 'NPL', 'NR': 'NRU', 'NZ': 'NZL', 'OM': 'OMN', 'PA': 'PAN',
            'PE': 'PER', 'PG': 'PNG', 'PH': 'PHL', 'PK': 'PAK', 'PL': 'POL',
            'PT': 'PRT', 'PW': 'PLW', 'PY': 'PRY', 'QA': 'QAT', 'RO': 'ROU',
            'RS': 'SRB', 'RU': 'RUS', 'RW': 'RWA', 'SA': 'SAU', 'SB': 'SLB',
            'SC': 'SYC', 'SD': 'SDN', 'SE': 'SWE', 'SG': 'SGP', 'SI': 'SVN',
            'SK': 'SVK', 'SL': 'SLE', 'SM': 'SMR', 'SN': 'SEN', 'SO': 'SOM',
            'SR': 'SUR', 'SS': 'SSD', 'ST': 'STP', 'SV': 'SLV', 'SY': 'SYR',
            'SZ': 'SWZ', 'TD': 'TCD', 'TG': 'TGO', 'TH': 'THA', 'TJ': 'TJK',
            'TL': 'TLS', 'TM': 'TKM', 'TN': 'TUN', 'TO': 'TON', 'TR': 'TUR',
            'TT': 'TTO', 'TV': 'TUV', 'TZ': 'TZA', 'UA': 'UKR', 'UG': 'UGA',
            'US': 'USA', 'UY': 'URY', 'UZ': 'UZB', 'VA': 'VAT', 'VC': 'VCT',
            'VE': 'VEN', 'VN': 'VNM', 'VU': 'VUT', 'WS': 'WSM', 'YE': 'YEM',
            'ZA': 'ZAF', 'ZM': 'ZMB', 'ZW': 'ZWE',
        }
        return mapping

    def create_expenditure_file(self, country_code):
        """Create expenditure Excel file for a country"""

        # Convert ISO2 to ISO3 if needed
        if len(country_code) == 2:
            wb_code = self.iso_mapping.get(country_code, country_code)
        else:
            wb_code = country_code

        # Get country data
        country_data = self.wb_wide[self.wb_wide['country_code'] == wb_code].copy()

        if len(country_data) == 0:
            return None

        # Sort by year
        country_data = country_data.sort_values('year')

        # Select key columns and rename for clarity
        expenditure_df = country_data[['year', 'country_name']].copy()

        # Add expenditure indicators (with better names)
        indicator_mapping = {
            'gov_expenditure_gdp': 'Total_Govt_Expenditure_GDP',
            'education_expenditure': 'Education_Expenditure_GDP',
            'education_expenditure_govt': 'Education_Pct_Govt_Budget',
            'health_expenditure': 'Health_Expenditure_GDP',
            'health_expenditure_govt': 'Health_Pct_Govt_Budget',
            'military_expenditure': 'Military_Expenditure_GDP',
            'rd_expenditure': 'RD_Expenditure_GDP',
            'social_expenditure': 'Social_Protection_Adequacy',
        }

        for old_name, new_name in indicator_mapping.items():
            if old_name in country_data.columns:
                expenditure_df[new_name] = country_data[old_name]

        # Rename columns
        expenditure_df = expenditure_df.rename(columns={
            'year': 'Year',
            'country_name': 'Country'
        })

        return expenditure_df

    def integrate_country(self, country_code):
        """Integrate expenditure data for a single country"""

        country_dir = COUNTRIES_DIR / country_code / "Output" / "Data"

        # Create Output/Data directory if it doesn't exist
        country_dir.mkdir(parents=True, exist_ok=True)

        # Create expenditure file
        expenditure_df = self.create_expenditure_file(country_code)

        if expenditure_df is None or len(expenditure_df) == 0:
            return False

        # Save to Excel
        output_file = country_dir / f"{country_code.lower()}_government_expenditure.xlsx"

        write_single_sheet_excel(expenditure_df, output_file, sheet_name='Expenditure')

        logger.info(f"  ✅ {country_code}: {len(expenditure_df)} years ({expenditure_df['Year'].min()}-{expenditure_df['Year'].max()})")

        return True

    def create_expenditure_summary(self, country_code):
        """Create summary JSON for a country's expenditure data"""

        # Convert ISO2 to ISO3 if needed
        if len(country_code) == 2:
            wb_code = self.iso_mapping.get(country_code, country_code)
        else:
            wb_code = country_code

        country_data = self.wb_wide[self.wb_wide['country_code'] == wb_code]

        if len(country_data) == 0:
            return None

        # Get latest year with data
        latest = country_data.sort_values('year').iloc[-1]

        summary = {
            'country_code': country_code,
            'country_name': str(latest['country_name']),
            'data_coverage': {
                'years': f"{int(country_data['year'].min())}-{int(country_data['year'].max())}",
                'observations': int(len(country_data)),
            },
            'latest_data': {
                'year': int(latest['year']),
                'total_expenditure_gdp': float(latest['gov_expenditure_gdp']) if pd.notna(latest.get('gov_expenditure_gdp')) else None,
                'education_gdp': float(latest['education_expenditure']) if pd.notna(latest.get('education_expenditure')) else None,
                'health_gdp': float(latest['health_expenditure']) if pd.notna(latest.get('health_expenditure')) else None,
                'military_gdp': float(latest['military_expenditure']) if pd.notna(latest.get('military_expenditure')) else None,
            },
            'data_source': 'World Bank Open Data',
            'download_date': '2025-10-06',
        }

        # Save summary
        country_dir = COUNTRIES_DIR / country_code / "Output" / "Data"
        summary_file = country_dir / f"{country_code.lower()}_expenditure_summary.json"

        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    def integrate_all_countries(self):
        """Integrate expenditure data for all countries"""
        logger.info("\n" + "=" * 60)
        logger.info("Integrating Expenditure Data into Country Directories")
        logger.info("=" * 60)

        integrated = 0
        no_data = 0

        for country_code in self.countries:
            success = self.integrate_country(country_code)

            if success:
                self.create_expenditure_summary(country_code)
                integrated += 1
            else:
                no_data += 1

        logger.info("\n" + "=" * 60)
        logger.info("Integration Summary")
        logger.info("=" * 60)
        logger.info(f"Countries processed: {len(self.countries)}")
        logger.info(f"Successfully integrated: {integrated}")
        logger.info(f"No expenditure data: {no_data}")

        return integrated

    def create_global_summary(self):
        """Create global summary of expenditure coverage"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Global Coverage Summary")
        logger.info("=" * 60)

        summary = {
            'total_countries': len(self.countries),
            'countries_with_expenditure_data': int(self.wb_wide['country_code'].nunique()),
            'indicators': {
                'total_expenditure': {
                    'countries': int(self.wb_wide['gov_expenditure_gdp'].notna().sum()),
                    'name': 'Total government expenditure (% GDP)'
                },
                'education': {
                    'countries': int(self.wb_wide['education_expenditure'].notna().sum()),
                    'name': 'Education expenditure (% GDP)'
                },
                'health': {
                    'countries': int(self.wb_wide['health_expenditure'].notna().sum()),
                    'name': 'Health expenditure (% GDP)'
                },
                'military': {
                    'countries': int(self.wb_wide['military_expenditure'].notna().sum()),
                    'name': 'Military expenditure (% GDP)'
                },
            },
            'time_coverage': {
                'earliest_year': int(self.wb_wide['year'].min()),
                'latest_year': int(self.wb_wide['year'].max()),
                'total_observations': len(self.wb_wide),
            },
            'data_source': 'World Bank Open Data',
            'integration_date': '2025-10-06',
        }

        # Save global summary
        summary_file = BASE_DIR / "expenditure_integration_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"\n✅ Global summary saved: {summary_file.name}")

        # Print summary
        logger.info("\nCoverage by Indicator:")
        for indicator, info in summary['indicators'].items():
            logger.info(f"  {info['name']}: {info['countries']} countries")

        return summary

    def run(self):
        """Run complete integration"""
        logger.info("Government Expenditure Data Integration")
        logger.info("")

        if self.wb_wide is None:
            logger.error("No World Bank data loaded. Exiting.")
            return

        # Integrate all countries
        integrated_count = self.integrate_all_countries()

        # Create global summary
        self.create_global_summary()

        logger.info("\n" + "=" * 60)
        logger.info("✅ Expenditure Integration Complete!")
        logger.info("=" * 60)
        logger.info(f"Countries integrated: {integrated_count}")
        logger.info("")
        logger.info("Each country now has:")
        logger.info("  - {country_code}_government_expenditure.xlsx")
        logger.info("  - {country_code}_expenditure_summary.json")
        logger.info("")


def main():
    integrator = ExpenditureIntegrator()
    integrator.run()


if __name__ == "__main__":
    main()
