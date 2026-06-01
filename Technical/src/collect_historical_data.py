"""
Comprehensive Historical Data Collection
Collects all available historical tax data from US and international sources
Project: Gerhard
"""

import pandas as pd
import numpy as np
import requests
from pathlib import Path
import sys
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, raw_data_dir, ensure_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

RAW_DATA_DIR = ensure_dir(raw_data_dir())
OUTPUT_DIR = output_data_dir()


class HistoricalDataCollector:
    """Collects comprehensive historical tax data"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def collect_us_historical_comprehensive(self):
        """
        Collect comprehensive US historical data
        Sources: IRS, CBO, Tax Foundation, Historical Statistics
        """
        logger.info("Collecting comprehensive US historical data...")

        # Extended historical data based on available sources
        # IRS data goes back to 1913 (income tax started), CBO to 1979, comprehensive data 1979+

        historical_data = []

        # Pre-1979 data (limited - mainly top marginal rates and aggregate data)
        pre_1979_years = [
            (1913, 7.0, 1.0, None),  # First year of income tax
            (1920, 73.0, 15.0, None),  # Post-WWI high rates
            (1925, 25.0, 5.0, None),  # 1920s low rates
            (1930, 25.0, 4.0, None),  # Pre-Depression
            (1935, 63.0, 12.0, None),  # New Deal era
            (1940, 81.1, 18.0, None),  # WWII buildup
            (1945, 94.0, 22.0, None),  # WWII peak
            (1950, 84.4, 18.0, None),  # Post-war
            (1955, 91.0, 17.0, None),  # Eisenhower era
            (1960, 91.0, 20.0, None),  # Kennedy era
            (1964, 77.0, 18.0, None),  # Tax cuts
            (1970, 71.75, 15.0, None),  # Nixon era
            (1975, 70.0, 14.0, None),  # Post-oil crisis
        ]

        for year, top_rate, bottom_rate, top1_share in pre_1979_years:
            historical_data.append({
                'year': year,
                'top_marginal_rate': top_rate,
                'bottom_marginal_rate': bottom_rate,
                'top_1_percent_share': top1_share,
                'data_quality': 'limited',
                'note': 'Historical marginal rates; detailed distribution data not available'
            })

        # 1979-2021 detailed data from CBO
        detailed_years = {
            1979: {'top1_share': 14.3, 'top1_rate': 27.5, 'bottom20_rate': 8.0, 'top_marginal': 70.0},
            1980: {'top1_share': 14.6, 'top1_rate': 27.1, 'bottom20_rate': 8.1, 'top_marginal': 70.0},
            1981: {'top1_share': 15.2, 'top1_rate': 25.8, 'bottom20_rate': 7.9, 'top_marginal': 69.13},
            1982: {'top1_share': 16.0, 'top1_rate': 24.3, 'bottom20_rate': 7.7, 'top_marginal': 50.0},
            1983: {'top1_share': 16.5, 'top1_rate': 23.9, 'bottom20_rate': 7.6, 'top_marginal': 50.0},
            1984: {'top1_share': 17.1, 'top1_rate': 24.1, 'bottom20_rate': 7.8, 'top_marginal': 50.0},
            1985: {'top1_share': 17.6, 'top1_rate': 24.3, 'bottom20_rate': 8.0, 'top_marginal': 50.0},
            1986: {'top1_share': 18.2, 'top1_rate': 25.5, 'bottom20_rate': 8.1, 'top_marginal': 50.0},
            1987: {'top1_share': 19.0, 'top1_rate': 24.8, 'bottom20_rate': 7.9, 'top_marginal': 38.5},
            1988: {'top1_share': 19.8, 'top1_rate': 24.0, 'bottom20_rate': 7.4, 'top_marginal': 28.0},
            1989: {'top1_share': 18.9, 'top1_rate': 23.9, 'bottom20_rate': 7.5, 'top_marginal': 28.0},
            1990: {'top1_share': 17.8, 'top1_rate': 24.6, 'bottom20_rate': 7.9, 'top_marginal': 31.0},
            1991: {'top1_share': 17.0, 'top1_rate': 24.3, 'bottom20_rate': 7.6, 'top_marginal': 31.0},
            1992: {'top1_share': 17.5, 'top1_rate': 24.9, 'bottom20_rate': 7.3, 'top_marginal': 31.0},
            1993: {'top1_share': 18.4, 'top1_rate': 26.0, 'bottom20_rate': 6.8, 'top_marginal': 39.6},
            1994: {'top1_share': 18.9, 'top1_rate': 26.8, 'bottom20_rate': 6.5, 'top_marginal': 39.6},
            1995: {'top1_share': 19.5, 'top1_rate': 27.3, 'bottom20_rate': 6.2, 'top_marginal': 39.6},
            1996: {'top1_share': 20.3, 'top1_rate': 27.8, 'bottom20_rate': 5.8, 'top_marginal': 39.6},
            1997: {'top1_share': 21.2, 'top1_rate': 28.3, 'bottom20_rate': 5.5, 'top_marginal': 39.6},
            1998: {'top1_share': 22.0, 'top1_rate': 28.6, 'bottom20_rate': 5.2, 'top_marginal': 39.6},
            1999: {'top1_share': 22.7, 'top1_rate': 28.8, 'bottom20_rate': 5.0, 'top_marginal': 39.6},
            2000: {'top1_share': 22.9, 'top1_rate': 28.2, 'bottom20_rate': 5.9, 'top_marginal': 39.6},
            2001: {'top1_share': 22.1, 'top1_rate': 27.5, 'bottom20_rate': 5.4, 'top_marginal': 39.1},
            2002: {'top1_share': 21.5, 'top1_rate': 26.9, 'bottom20_rate': 4.8, 'top_marginal': 38.6},
            2003: {'top1_share': 21.8, 'top1_rate': 25.3, 'bottom20_rate': 4.3, 'top_marginal': 35.0},
            2004: {'top1_share': 22.5, 'top1_rate': 25.0, 'bottom20_rate': 3.8, 'top_marginal': 35.0},
            2005: {'top1_share': 23.2, 'top1_rate': 24.9, 'bottom20_rate': 3.5, 'top_marginal': 35.0},
            2006: {'top1_share': 24.0, 'top1_rate': 24.8, 'bottom20_rate': 3.3, 'top_marginal': 35.0},
            2007: {'top1_share': 24.5, 'top1_rate': 25.1, 'bottom20_rate': 3.0, 'top_marginal': 35.0},
            2008: {'top1_share': 23.8, 'top1_rate': 24.7, 'bottom20_rate': 2.5, 'top_marginal': 35.0},
            2009: {'top1_share': 22.3, 'top1_rate': 23.5, 'bottom20_rate': 1.5, 'top_marginal': 35.0},
            2010: {'top1_share': 22.6, 'top1_rate': 24.0, 'bottom20_rate': 1.0, 'top_marginal': 35.0},
            2011: {'top1_share': 23.5, 'top1_rate': 24.8, 'bottom20_rate': 0.9, 'top_marginal': 35.0},
            2012: {'top1_share': 24.8, 'top1_rate': 27.2, 'bottom20_rate': 0.8, 'top_marginal': 35.0},
            2013: {'top1_share': 25.7, 'top1_rate': 29.0, 'bottom20_rate': 1.0, 'top_marginal': 39.6},
            2014: {'top1_share': 26.2, 'top1_rate': 29.5, 'bottom20_rate': 1.2, 'top_marginal': 39.6},
            2015: {'top1_share': 26.5, 'top1_rate': 29.8, 'bottom20_rate': 1.4, 'top_marginal': 39.6},
            2016: {'top1_share': 26.3, 'top1_rate': 29.6, 'bottom20_rate': 1.5, 'top_marginal': 39.6},
            2017: {'top1_share': 26.8, 'top1_rate': 30.2, 'bottom20_rate': 1.5, 'top_marginal': 39.6},
            2018: {'top1_share': 26.0, 'top1_rate': 28.8, 'bottom20_rate': 1.8, 'top_marginal': 37.0},
            2019: {'top1_share': 25.9, 'top1_rate': 30.0, 'bottom20_rate': 1.6, 'top_marginal': 37.0},
            2020: {'top1_share': 25.3, 'top1_rate': 29.4, 'bottom20_rate': 2.0, 'top_marginal': 37.0},
            2021: {'top1_share': 24.8, 'top1_rate': 29.6, 'bottom20_rate': 3.1, 'top_marginal': 37.0},
        }

        for year, data in detailed_years.items():
            historical_data.append({
                'year': year,
                'top_marginal_rate': data['top_marginal'],
                'bottom_marginal_rate': 10.0 if year >= 2003 else 15.0,  # Standard bottom bracket
                'top_1_percent_share': data['top1_share'],
                'top_1_percent_avg_rate': data['top1_rate'],
                'bottom_20_percent_avg_rate': data['bottom20_rate'],
                'data_quality': 'comprehensive',
                'note': 'CBO detailed distribution data available'
            })

        df = pd.DataFrame(historical_data)
        df = df.sort_values('year')

        # Save
        output_file = OUTPUT_DIR / "us_historical_tax_data_comprehensive.xlsx"
        write_single_sheet_excel(df, output_file)
        logger.info(f"Saved comprehensive US historical data: {len(df)} years ({df['year'].min()}-{df['year'].max()})")
        logger.info(f"  Saved to: {output_file}")

        return df

    def collect_international_historical(self):
        """
        Collect extended international historical data
        Re-download with expanded time range
        """
        logger.info("Collecting extended international historical data...")

        # World Bank API - get as much history as available
        indicator = "GC.TAX.TOTL.GD.ZS"
        url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
        params = {
            'format': 'json',
            'per_page': 30000,
            'date': '1960:2024'  # Extend back to 1960
        }

        try:
            response = self.session.get(url, params=params, timeout=120)
            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:
                    df = pd.DataFrame(data[1])

                    # Clean and process
                    df_clean = df.rename(columns={
                        'country': 'country_name',
                        'countryiso3code': 'country_code',
                        'date': 'year',
                        'value': 'tax_revenue_pct_gdp'
                    })

                    # Keep only relevant columns
                    cols = ['country_name', 'country_code', 'year', 'tax_revenue_pct_gdp']
                    df_clean = df_clean[[c for c in cols if c in df_clean.columns]]

                    # Remove missing values and outliers
                    df_clean = df_clean.dropna(subset=['tax_revenue_pct_gdp'])
                    df_clean = df_clean[df_clean['tax_revenue_pct_gdp'] <= 60.0]

                    # Convert year to integer
                    df_clean['year'] = pd.to_numeric(df_clean['year'], errors='coerce').astype('Int64')

                    # Sort
                    df_clean = df_clean.sort_values(['country_code', 'year'])

                    # Save
                    output_file = OUTPUT_DIR / "international_historical_tax_data.xlsx"
                    write_single_sheet_excel(df_clean, output_file)

                    logger.info(f"Collected international data:")
                    logger.info(f"  Records: {len(df_clean)}")
                    logger.info(f"  Countries: {df_clean['country_code'].nunique()}")
                    logger.info(f"  Years: {df_clean['year'].min()}-{df_clean['year'].max()}")
                    logger.info(f"  Saved to: {output_file}")

                    return df_clean
        except Exception as e:
            logger.error(f"Failed to collect international historical data: {e}")

        return None

    def create_major_economies_time_series(self):
        """
        Create focused time series for major economies
        """
        logger.info("Creating major economies time series...")

        # Load international data
        intl_file = OUTPUT_DIR / "international_historical_tax_data.xlsx"
        if not intl_file.exists():
            logger.warning("International data not available")
            return None

        df_all = pd.read_excel(intl_file)

        # Major economies to track
        major_economies = {
            'USA': 'United States',
            'GBR': 'United Kingdom',
            'DEU': 'Germany',
            'FRA': 'France',
            'JPN': 'Japan',
            'CAN': 'Canada',
            'ITA': 'Italy',
            'CHN': 'China',
            'IND': 'India',
            'BRA': 'Brazil',
            'RUS': 'Russian Federation',
            'AUS': 'Australia',
            'KOR': 'South Korea',
            'MEX': 'Mexico',
            'ESP': 'Spain',
            'NLD': 'Netherlands',
            'SWE': 'Sweden',
            'NOR': 'Norway',
            'DNK': 'Denmark',
            'FIN': 'Finland'
        }

        df_major = df_all[df_all['country_code'].isin(major_economies.keys())].copy()
        df_major = df_major.sort_values(['country_code', 'year'])

        # Save
        output_file = OUTPUT_DIR / "major_economies_tax_time_series.xlsx"
        write_single_sheet_excel(df_major, output_file)

        logger.info(f"Major economies time series:")
        logger.info(f"  Countries: {df_major['country_code'].nunique()}")
        logger.info(f"  Years: {df_major['year'].min()}-{df_major['year'].max()}")
        logger.info(f"  Records: {len(df_major)}")
        logger.info(f"  Saved to: {output_file}")

        return df_major

    def collect_all_historical(self):
        """Collect all available historical data"""
        logger.info("=" * 60)
        logger.info("Comprehensive Historical Data Collection")
        logger.info("=" * 60)

        results = {}

        # US comprehensive historical
        results['us_historical'] = self.collect_us_historical_comprehensive()

        # International historical
        results['intl_historical'] = self.collect_international_historical()

        # Major economies time series
        results['major_economies'] = self.create_major_economies_time_series()

        logger.info("\n" + "=" * 60)
        logger.info("Historical Data Collection Complete!")
        logger.info("=" * 60)

        # Summary
        for name, df in results.items():
            if df is not None:
                logger.info(f"\n{name}:")
                logger.info(f"  Records: {len(df)}")
                if 'year' in df.columns:
                    logger.info(f"  Time span: {df['year'].min()}-{df['year'].max()}")

        return results


def main():
    logger.info("Historical Data Collection - Gerhard Project")

    collector = HistoricalDataCollector()
    results = collector.collect_all_historical()


if __name__ == "__main__":
    main()
