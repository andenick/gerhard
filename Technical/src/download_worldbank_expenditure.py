"""
Download World Bank Government Expenditure Data
Multiple expenditure indicators for 200+ countries

Project: Gerhard - Expenditure Data Collection
"""

import requests
import pandas as pd
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, ensure_dir

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir() / "worldbank" / "expenditure")


class WorldBankExpenditureDownloader:
    """Download World Bank government expenditure data"""

    def __init__(self):
        self.base_url = "https://api.worldbank.org/v2"
        self.indicators = {
            # Total government expenditure
            'gov_expenditure_gdp': {
                'code': 'NE.CON.GOVT.ZS',
                'name': 'General government final consumption expenditure (% of GDP)',
                'description': 'Total government final consumption expenditure'
            },
            'gov_expenditure_usd': {
                'code': 'NE.CON.GOVT.CD',
                'name': 'General government final consumption expenditure (current US$)',
                'description': 'Total government expenditure in USD'
            },

            # Sectoral expenditure
            'education_expenditure': {
                'code': 'SE.XPD.TOTL.GD.ZS',
                'name': 'Government expenditure on education, total (% of GDP)',
                'description': 'Public spending on education'
            },
            'education_expenditure_govt': {
                'code': 'SE.XPD.TOTL.GB.ZS',
                'name': 'Government expenditure on education, total (% of government expenditure)',
                'description': 'Education as share of total government spending'
            },
            'health_expenditure': {
                'code': 'SH.XPD.GHED.GD.ZS',
                'name': 'Domestic general government health expenditure (% of GDP)',
                'description': 'Public spending on health'
            },
            'health_expenditure_govt': {
                'code': 'SH.XPD.GHED.GE.ZS',
                'name': 'Domestic general government health expenditure (% of general government expenditure)',
                'description': 'Health as share of total government spending'
            },
            'military_expenditure': {
                'code': 'MS.MIL.XPND.GD.ZS',
                'name': 'Military expenditure (% of GDP)',
                'description': 'Military spending'
            },

            # R&D expenditure
            'rd_expenditure': {
                'code': 'GB.XPD.RSDV.GD.ZS',
                'name': 'Research and development expenditure (% of GDP)',
                'description': 'Government R&D spending'
            },

            # Social protection
            'social_expenditure': {
                'code': 'per_sa_allsa.adq_pop_tot',
                'name': 'Adequacy of social safety net programs (% of total welfare of beneficiary households)',
                'description': 'Social protection spending'
            },
        }

    def download_indicator(self, indicator_code, indicator_name):
        """Download a single indicator for all countries"""
        logger.info(f"\nDownloading: {indicator_name}")
        logger.info(f"Indicator: {indicator_code}")

        try:
            # World Bank API: Get all countries, all years
            url = f"{self.base_url}/country/all/indicator/{indicator_code}"
            params = {
                'format': 'json',
                'per_page': 20000,  # High number to get all data
                'date': '1960:2024'  # All years
            }

            response = requests.get(url, params=params, timeout=60)

            if response.status_code == 200:
                data = response.json()

                # World Bank API returns [metadata, data]
                if len(data) < 2 or not data[1]:
                    logger.warning(f"No data returned for {indicator_code}")
                    return None

                # Parse data
                records = []
                for item in data[1]:
                    records.append({
                        'country_name': item.get('country', {}).get('value'),
                        'country_code': item.get('countryiso3code'),
                        'indicator_name': item.get('indicator', {}).get('value'),
                        'indicator_code': item.get('indicator', {}).get('id'),
                        'year': item.get('date'),
                        'value': item.get('value'),
                    })

                df = pd.DataFrame(records)

                # Remove rows with no data
                df = df.dropna(subset=['value'])

                if len(df) == 0:
                    logger.warning(f"No valid data for {indicator_code}")
                    return None

                logger.info(f"  Downloaded: {len(df):,} observations")
                logger.info(f"  Countries: {df['country_code'].nunique()}")
                logger.info(f"  Years: {df['year'].min()}-{df['year'].max()}")

                return df

            else:
                logger.error(f"HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error downloading {indicator_code}: {e}")
            return None

    def download_all_indicators(self):
        """Download all expenditure indicators"""
        logger.info("=" * 60)
        logger.info("World Bank Government Expenditure Data Download")
        logger.info("=" * 60)

        all_data = {}

        for key, indicator in self.indicators.items():
            df = self.download_indicator(indicator['code'], indicator['name'])

            if df is not None:
                # Save individual indicator
                filename = f"wb_{key}.csv"
                filepath = RAW_DATA_DIR / filename
                df.to_csv(filepath, index=False)
                logger.info(f"  ✅ Saved: {filename}")

                all_data[key] = df

            # Be nice to API
            time.sleep(0.5)

        return all_data

    def create_combined_dataset(self, all_data):
        """Create combined dataset with all indicators"""
        logger.info("\n" + "=" * 60)
        logger.info("Creating Combined Dataset")
        logger.info("=" * 60)

        if not all_data:
            logger.warning("No data to combine")
            return

        # Combine all data
        combined = []
        for key, df in all_data.items():
            df_copy = df.copy()
            df_copy['indicator_short'] = key
            combined.append(df_copy)

        combined_df = pd.concat(combined, ignore_index=True)

        # Save combined
        combined_file = RAW_DATA_DIR / "wb_expenditure_combined.csv"
        combined_df.to_csv(combined_file, index=False)
        logger.info(f"✅ Combined dataset saved: {combined_file.name}")
        logger.info(f"   Total observations: {len(combined_df):,}")

        # Create pivot table (wide format)
        logger.info("\nCreating pivot table (wide format)...")

        pivot_df = combined_df.pivot_table(
            index=['country_code', 'country_name', 'year'],
            columns='indicator_short',
            values='value',
            aggfunc='first'
        ).reset_index()

        pivot_file = RAW_DATA_DIR / "wb_expenditure_wide.csv"
        pivot_df.to_csv(pivot_file, index=False)
        logger.info(f"✅ Pivot table saved: {pivot_file.name}")
        logger.info(f"   Observations: {len(pivot_df):,}")

        return pivot_df

    def create_summary(self, all_data, pivot_df):
        """Create summary statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("Summary Statistics")
        logger.info("=" * 60)

        summary = {
            'indicators_downloaded': len(all_data),
            'total_observations': sum(len(df) for df in all_data.values()),
            'countries_with_data': {},
            'latest_year': {},
        }

        for key, df in all_data.items():
            summary['countries_with_data'][key] = int(df['country_code'].nunique())
            summary['latest_year'][key] = str(df['year'].max())

        # Print summary
        logger.info(f"\nIndicators downloaded: {summary['indicators_downloaded']}")
        logger.info(f"Total observations: {summary['total_observations']:,}")
        logger.info("\nCountries with data by indicator:")
        for key, count in summary['countries_with_data'].items():
            logger.info(f"  {key}: {count} countries")

        # Latest data availability
        logger.info("\nLatest year available by indicator:")
        for key, year in summary['latest_year'].items():
            logger.info(f"  {key}: {year}")

        # Save summary
        import json
        summary_file = RAW_DATA_DIR / "download_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\n✅ Summary saved: {summary_file.name}")

    def create_readme(self):
        """Create README for downloaded data"""
        readme = """# World Bank Government Expenditure Data

**Downloaded:** October 6, 2025
**Source:** World Bank Open Data API
**Coverage:** 200+ countries

## Indicators Downloaded

### Total Government Expenditure
- **gov_expenditure_gdp** (NE.CON.GOVT.ZS)
  - General government final consumption expenditure (% of GDP)
  - Total government consumption

- **gov_expenditure_usd** (NE.CON.GOVT.CD)
  - General government final consumption expenditure (current US$)
  - Absolute expenditure in USD

### Education
- **education_expenditure** (SE.XPD.TOTL.GD.ZS)
  - Government expenditure on education, total (% of GDP)

- **education_expenditure_govt** (SE.XPD.TOTL.GB.ZS)
  - Government expenditure on education (% of government expenditure)

### Health
- **health_expenditure** (SH.XPD.GHED.GD.ZS)
  - Domestic general government health expenditure (% of GDP)

- **health_expenditure_govt** (SH.XPD.GHED.GE.ZS)
  - Health expenditure (% of general government expenditure)

### Defense
- **military_expenditure** (MS.MIL.XPND.GD.ZS)
  - Military expenditure (% of GDP)

### Research & Development
- **rd_expenditure** (GB.XPD.RSDV.GD.ZS)
  - Research and development expenditure (% of GDP)

## Files

### Individual Indicators
- `wb_gov_expenditure_gdp.csv` - Total expenditure (% GDP)
- `wb_education_expenditure.csv` - Education spending
- `wb_health_expenditure.csv` - Health spending
- `wb_military_expenditure.csv` - Defense spending
- etc.

### Combined Datasets
- `wb_expenditure_combined.csv` - All indicators (long format)
- `wb_expenditure_wide.csv` - Pivot table (wide format, by country-year)

### Metadata
- `download_summary.json` - Summary statistics
- `README.md` - This file

## Data Format

**Long Format (combined):**
```
country_code, country_name, year, indicator_code, indicator_name, indicator_short, value
```

**Wide Format (pivot):**
```
country_code, country_name, year, gov_expenditure_gdp, education_expenditure, health_expenditure, ...
```

## Coverage

- **Time Span:** 1960-2024 (varies by indicator and country)
- **Countries:** 200+ countries and territories
- **Update Frequency:** Annual

## Data Quality

**Strengths:**
- Broad country coverage
- Long time series
- Standardized methodology

**Limitations:**
- Some missing data (especially older years)
- Not all countries report all indicators
- Aggregate data (no detailed functional classification)
- Data lags (typically 1-2 years)

## Usage

For detailed functional classification (COFOG), use:
- OECD Data Explorer (OECD countries)
- Eurostat (EU countries)
- IMF GFS (all countries)

World Bank data is best for:
- Broad cross-country comparisons
- Long time series
- Quick aggregate expenditure metrics

## API Details

**World Bank API v2:**
- URL: https://api.worldbank.org/v2/
- Format: JSON, XML, CSV
- Documentation: https://datahelpdesk.worldbank.org/

**Example API call:**
```
https://api.worldbank.org/v2/country/all/indicator/NE.CON.GOVT.ZS?format=json&per_page=20000&date=1960:2024
```

---

*Downloaded: October 6, 2025*
*Project: Gerhard - Fiscal Analysis*
"""

        readme_file = RAW_DATA_DIR / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme)
        logger.info(f"✅ README created: {readme_file.name}")

    def run(self):
        """Run complete download"""
        logger.info("World Bank Government Expenditure Downloader")
        logger.info("")

        # Download all indicators
        all_data = self.download_all_indicators()

        # Create combined dataset
        pivot_df = self.create_combined_dataset(all_data)

        # Create summary
        self.create_summary(all_data, pivot_df)

        # Create README
        self.create_readme()

        logger.info("\n" + "=" * 60)
        logger.info("✅ World Bank Download Complete!")
        logger.info("=" * 60)
        logger.info(f"Output directory: {RAW_DATA_DIR}")
        logger.info(f"Files created: {len(list(RAW_DATA_DIR.glob('*')))}")
        logger.info("")


def main():
    downloader = WorldBankExpenditureDownloader()
    downloader.run()


if __name__ == "__main__":
    main()
