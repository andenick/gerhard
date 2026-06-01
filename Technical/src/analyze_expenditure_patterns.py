"""
Government Expenditure Analysis - Enhanced Pipeline
===============================================

Comprehensive analysis of government expenditure patterns by function,
combining World Bank aggregate data with detailed COFOG classification.

Creates:
- Expenditure breakdowns by function (COFOG categories)
- International comparisons and rankings
- Time series analysis of spending patterns
- Sectoral efficiency analysis
- Integration with existing tax analysis

Created: October 19, 2025
Project: Gerhard - Fiscal Analysis Expansion Phase 1
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from pathlib import Path
import sys
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Use non-interactive backend
matplotlib.use('Agg')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, countries_dir, raw_data_dir
from utils.config import project_root
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

# Base directories
WB_DATA_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_data_dir()
COUNTRIES_DIR = countries_dir()


class GovernmentExpenditureAnalyzer:
    """Comprehensive government expenditure analysis"""

    def __init__(self):
        self.wb_data = None
        self.cofog_mapping = self._create_cofog_mapping()
        self.regional_mapping = self._create_regional_mapping()
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Analysis results storage
        self.results = {}

    def _create_cofog_mapping(self) -> Dict[str, Dict]:
        """Create COFOG classification mapping for World Bank indicators"""
        return {
            'education': {
                'cofog_code': '09',
                'cofog_name': 'Education',
                'wb_indicators': ['SE.XPD.TOTL.GD.ZS', 'SE.XPD.TOTL.GB.ZS'],
                'description': 'Education spending and training'
            },
            'health': {
                'cofog_code': '07',
                'cofog_name': 'Health',
                'wb_indicators': ['SH.XPD.GHED.GD.ZS', 'SH.XPD.GHED.GE.ZS'],
                'description': 'Healthcare and medical services'
            },
            'defense': {
                'cofog_code': '02',
                'cofog_name': 'Defense',
                'wb_indicators': ['MS.MIL.XPND.GD.ZS'],
                'description': 'Military defense and civil protection'
            },
            'economic_affairs': {
                'cofog_code': '04',
                'cofog_name': 'Economic affairs',
                'wb_indicators': ['GB.XPD.RSDV.GD.ZS'],  # R&D as proxy
                'description': 'Economic development and infrastructure'
            },
            'social_protection': {
                'cofog_code': '10',
                'cofog_name': 'Social protection',
                'wb_indicators': [],  # No direct World Bank equivalent
                'description': 'Social security and welfare'
            }
        }

    def _create_regional_mapping(self) -> Dict[str, List[str]]:
        """Create regional country groupings"""
        return {
            'OECD': ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'AUS', 'NLD', 'SWE', 'NOR', 'DNK',
                    'CHE', 'AUT', 'BEL', 'IRL', 'NZL', 'KOR', 'ESP', 'ITA', 'MEX', 'PRT', 'GRC',
                    'CZE', 'HUN', 'POL', 'CHL', 'COL', 'CRI', 'EST', 'ISR', 'SVK', 'SVN', 'TUR'],
            'EU': ['DEU', 'FRA', 'ITA', 'ESP', 'NLD', 'BEL', 'AUT', 'POL', 'SWE', 'CZE', 'ROU',
                   'GRC', 'PRT', 'IRL', 'FIN', 'BGR', 'DNK', 'SVK', 'HUN', 'HRV', 'LTU', 'SVN',
                   'EST', 'CYP', 'LVA', 'MLT', 'LUX'],
            'G7': ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'ITA'],
            'BRICS': ['BRA', 'RUS', 'IND', 'CHN', 'ZAF'],
            'Nordic': ['DNK', 'NOR', 'SWE', 'FIN', 'ISL'],
            'Asia_Pacific': ['CHN', 'JPN', 'IND', 'KOR', 'AUS', 'IDN', 'MYS', 'PHL', 'THA', 'SGP'],
            'Africa': ['NGA', 'ZAF', 'EGY', 'KEN', 'MAR', 'GHA', 'TUN', 'ETH', 'TZA']
        }

    def load_world_bank_data(self) -> bool:
        """Load World Bank expenditure data"""
        logger.info("=" * 80)
        logger.info("Loading World Bank Government Expenditure Data")
        logger.info("=" * 80)

        # Load wide format data
        wide_file = WB_DATA_DIR / "wb_expenditure_wide.csv"
        if not wide_file.exists():
            logger.error(f"World Bank expenditure data not found: {wide_file}")
            return False

        self.wb_data = pd.read_csv(wide_file)
        logger.info(f"✅ Loaded expenditure data: {len(self.wb_data):,} observations")
        logger.info(f"   Countries: {self.wb_data['country_code'].nunique()}")
        logger.info(f"   Years: {self.wb_data['year'].min()}-{self.wb_data['year'].max()}")

        # Data quality checks
        self._validate_data()

        return True

    def _validate_data(self):
        """Validate loaded data"""
        logger.info("\nValidating data quality...")

        # Check for missing values
        missing_summary = {}
        for col in ['gov_expenditure_gdp', 'education_expenditure', 'health_expenditure', 'military_expenditure']:
            if col in self.wb_data.columns:
                missing_pct = (self.wb_data[col].isnull().sum() / len(self.wb_data)) * 100
                missing_summary[col] = missing_pct

        logger.info("Missing data summary:")
        for col, pct in missing_summary.items():
            logger.info(f"  {col}: {pct:.1f}% missing")

        # Filter to recent years for analysis
        self.wb_data = self.wb_data[self.wb_data['year'] >= 2000]
        logger.info(f"✅ Filtered to 2000+: {len(self.wb_data):,} observations")

    def analyze_expenditure_patterns(self) -> Dict:
        """Analyze global expenditure patterns"""
        logger.info("\n" + "=" * 80)
        logger.info("Analyzing Global Government Expenditure Patterns")
        logger.info("=" * 80)

        analysis = {}

        # 1. Global averages by sector
        global_avg = self.wb_data.groupby('year')[['gov_expenditure_gdp', 'education_expenditure',
                                                   'health_expenditure', 'military_expenditure']].mean()

        analysis['global_averages'] = global_avg
        logger.info("✅ Calculated global expenditure averages")

        # 2. Country rankings (latest year)
        latest_year = self.wb_data['year'].max()
        latest_data = self.wb_data[self.wb_data['year'] == latest_year].copy()

        rankings = {}
        for indicator in ['gov_expenditure_gdp', 'education_expenditure', 'health_expenditure', 'military_expenditure']:
            if indicator in latest_data.columns:
                clean_data = latest_data.dropna(subset=[indicator])
                rankings[indicator] = clean_data.nlargest(20, indicator)[['country_code', 'country_name', indicator]]

        analysis['rankings'] = rankings
        logger.info(f"✅ Created country rankings for {latest_year}")

        # 3. Regional comparisons
        regional_stats = self._calculate_regional_comparisons()
        analysis['regional_comparisons'] = regional_stats
        logger.info("✅ Calculated regional comparisons")

        # 4. Trend analysis
        trends = self._analyze_expenditure_trends()
        analysis['trends'] = trends
        logger.info("✅ Analyzed expenditure trends")

        self.results['expenditure_patterns'] = analysis
        return analysis

    def _calculate_regional_comparisons(self) -> Dict:
        """Calculate expenditure statistics by region"""
        regional_data = {}

        for region, countries in self.regional_mapping.items():
            region_df = self.wb_data[self.wb_data['country_code'].isin(countries)]

            if len(region_df) > 0:
                regional_data[region] = {
                    'avg_total_expenditure': region_df['gov_expenditure_gdp'].mean(),
                    'avg_education_share': region_df['education_expenditure'].mean(),
                    'avg_health_share': region_df['health_expenditure'].mean(),
                    'avg_military_share': region_df['military_expenditure'].mean(),
                    'countries_count': len(region_df['country_code'].unique()),
                    'years_coverage': f"{region_df['year'].min()}-{region_df['year'].max()}"
                }

        return regional_data

    def _analyze_expenditure_trends(self) -> Dict:
        """Analyze expenditure trends over time"""
        trends = {}

        # Global trends
        global_trend = self.wb_data.groupby('year')[['gov_expenditure_gdp', 'education_expenditure',
                                                      'health_expenditure', 'military_expenditure']].mean()

        # Calculate growth rates
        for col in global_trend.columns:
            if global_trend[col].notna().sum() > 1:
                start_val = global_trend[col].dropna().iloc[0]
                end_val = global_trend[col].dropna().iloc[-1]
                years = len(global_trend[col].dropna())

                if start_val > 0:
                    annual_growth = ((end_val / start_val) ** (1/years) - 1) * 100
                    trends[f'{col}_growth'] = annual_growth

        # Country-level trends (top economies)
        top_economies = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'ITA', 'CAN', 'KOR']
        country_trends = {}

        for country in top_economies:
            country_data = self.wb_data[self.wb_data['country_code'] == country]
            if len(country_data) > 5:  # Need at least 5 years of data
                country_trends[country] = {
                    'latest_total': country_data.iloc[-1]['gov_expenditure_gdp'],
                    'trend_direction': 'increasing' if country_data.iloc[-1]['gov_expenditure_gdp'] > country_data.iloc[0]['gov_expenditure_gdp'] else 'decreasing',
                    'volatility': country_data['gov_expenditure_gdp'].std()
                }

        trends['country_trends'] = country_trends

        return trends

    def create_cofog_breakdowns(self) -> Dict:
        """Create COFOG-style expenditure breakdowns"""
        logger.info("\n" + "=" * 80)
        logger.info("Creating COFOG Expenditure Breakdowns")
        logger.info("=" * 80)

        cofog_analysis = {}

        # Map World Bank indicators to COFOG categories
        for sector, config in self.cofog_mapping.items():
            if config['wb_indicators']:
                logger.info(f"Processing {config['cofog_name']} sector...")

                sector_data = self._process_sector_data(sector, config)
                cofog_analysis[sector] = sector_data

        # Create synthetic COFOG breakdown for countries with complete data
        synthetic_cofog = self._create_synthetic_cofog()
        cofog_analysis['synthetic_cofog'] = synthetic_cofog

        self.results['cofog_breakdowns'] = cofog_analysis
        return cofog_analysis

    def _process_sector_data(self, sector: str, config: Dict) -> Dict:
        """Process data for a specific sector"""
        sector_stats = {}

        # Get indicator data
        for indicator in config['wb_indicators']:
            if indicator in self.wb_data.columns:
                data = self.wb_data[['country_code', 'country_name', 'year', indicator]].dropna()

                if len(data) > 0:
                    sector_stats[indicator] = {
                        'latest_global_avg': data[data['year'] == data['year'].max()][indicator].mean(),
                        'top_countries': data[data['year'] == data['year'].max()].nlargest(10, indicator)[['country_code', indicator]].to_dict('records'),
                        'time_series_avg': data.groupby('year')[indicator].mean().to_dict(),
                        'data_coverage': len(data['country_code'].unique())
                    }

        return sector_stats

    def _create_synthetic_cofog(self) -> pd.DataFrame:
        """Create synthetic COFOG breakdown using available data"""
        logger.info("Creating synthetic COFOG breakdowns...")

        # Get latest year data
        latest_year = self.wb_data['year'].max()
        latest_data = self.wb_data[self.wb_data['year'] == latest_year].copy()

        # Create COFOG breakdown for countries with good data coverage
        cofog_breakdowns = []

        for _, country_row in latest_data.iterrows():
            if pd.notna(country_row['gov_expenditure_gdp']):
                breakdown = {
                    'country_code': country_row['country_code'],
                    'country_name': country_row['country_name'],
                    'year': latest_year,
                    'total_expenditure_pct_gdp': country_row['gov_expenditure_gdp']
                }

                # Add known sectors
                if pd.notna(country_row['education_expenditure']):
                    breakdown['education_pct_gdp'] = country_row['education_expenditure']

                if pd.notna(country_row['health_expenditure']):
                    breakdown['health_pct_gdp'] = country_row['health_expenditure']

                if pd.notna(country_row['military_expenditure']):
                    breakdown['defense_pct_gdp'] = country_row['military_expenditure']

                # Estimate remaining as "other government services"
                known_sectors = sum([v for k, v in breakdown.items() if '_pct_gdp' in k and k != 'total_expenditure_pct_gdp'])
                breakdown['other_services_pct_gdp'] = max(0, breakdown['total_expenditure_pct_gdp'] - known_sectors)

                cofog_breakdowns.append(breakdown)

        return pd.DataFrame(cofog_breakdowns)

    def generate_excel_outputs(self) -> Dict[str, str]:
        """Generate Excel files with expenditure analysis"""
        logger.info("\n" + "=" * 80)
        logger.info("Generating Excel Outputs")
        logger.info("=" * 80)

        output_files = {}

        # 1. Global Expenditure Overview
        global_overview = self._create_global_overview_sheet()
        global_file = self.output_dir / "global_expenditure_overview.xlsx"
        write_single_sheet_excel(global_overview, global_file, sheet_name='Global_Expenditure')
        output_files['global_overview'] = str(global_file)
        logger.info(f"✅ Created: {global_file.name}")

        # 2. Country Expenditure Rankings
        rankings_file = self._create_rankings_sheet()
        output_files['rankings'] = str(rankings_file)
        logger.info(f"✅ Created: {rankings_file.name}")

        # 3. Regional Comparisons
        regional_file = self._create_regional_comparisons_sheet()
        output_files['regional'] = str(regional_file)
        logger.info(f"✅ Created: {regional_file.name}")

        # 4. COFOG Breakdowns
        cofog_file = self._create_cofog_sheet()
        output_files['cofog'] = str(cofog_file)
        logger.info(f"✅ Created: {cofog_file.name}")

        # 5. Time Series Data
        trends_file = self._create_trends_sheet()
        output_files['trends'] = str(trends_file)
        logger.info(f"✅ Created: {trends_file.name}")

        return output_files

    def _create_global_overview_sheet(self) -> pd.DataFrame:
        """Create global expenditure overview sheet"""
        global_data = []

        for year in sorted(self.wb_data['year'].unique()):
            year_data = self.wb_data[self.wb_data['year'] == year]

            overview_row = {
                'year': year,
                'countries_with_data': year_data['country_code'].nunique(),
                'avg_total_expenditure_pct_gdp': year_data['gov_expenditure_gdp'].mean(),
                'median_total_expenditure_pct_gdp': year_data['gov_expenditure_gdp'].median(),
                'avg_education_expenditure_pct_gdp': year_data['education_expenditure'].mean(),
                'avg_health_expenditure_pct_gdp': year_data['health_expenditure'].mean(),
                'avg_military_expenditure_pct_gdp': year_data['military_expenditure'].mean(),
                'global_data_quality_score': (1 - year_data[['gov_expenditure_gdp', 'education_expenditure',
                                                           'health_expenditure']].isnull().sum().sum() /
                                             (len(year_data) * 3)) * 100
            }
            global_data.append(overview_row)

        return pd.DataFrame(global_data)

    def _create_rankings_sheet(self) -> Path:
        """Create country rankings sheet"""
        rankings_data = []
        latest_year = self.wb_data['year'].max()
        latest_data = self.wb_data[self.wb_data['year'] == latest_year].copy()

        # Rankings by total expenditure
        for indicator in ['gov_expenditure_gdp', 'education_expenditure', 'health_expenditure', 'military_expenditure']:
            if indicator in latest_data.columns:
                clean_data = latest_data.dropna(subset=[indicator])
                top_20 = clean_data.nlargest(20, indicator)

                for rank, (_, row) in enumerate(top_20.iterrows(), 1):
                    rankings_data.append({
                        'indicator': indicator,
                        'rank': rank,
                        'country_code': row['country_code'],
                        'country_name': row['country_name'],
                        'value': row[indicator],
                        'year': latest_year
                    })

        rankings_df = pd.DataFrame(rankings_data)
        rankings_file = self.output_dir / "expenditure_rankings.xlsx"
        write_single_sheet_excel(rankings_df, rankings_file, sheet_name='Rankings')

        return rankings_file

    def _create_regional_comparisons_sheet(self) -> Path:
        """Create regional comparisons sheet"""
        regional_data = []

        for region_name, countries in self.regional_mapping.items():
            region_df = self.wb_data[self.wb_data['country_code'].isin(countries)]

            if len(region_df) > 0:
                for year in sorted(region_df['year'].unique()):
                    year_data = region_df[region_df['year'] == year]

                    regional_data.append({
                        'region': region_name,
                        'year': year,
                        'countries_count': len(year_data['country_code'].unique()),
                        'avg_total_expenditure_pct_gdp': year_data['gov_expenditure_gdp'].mean(),
                        'avg_education_pct_gdp': year_data['education_expenditure'].mean(),
                        'avg_health_pct_gdp': year_data['health_expenditure'].mean(),
                        'avg_military_pct_gdp': year_data['military_expenditure'].mean()
                    })

        regional_df = pd.DataFrame(regional_data)
        regional_file = self.output_dir / "regional_expenditure_comparisons.xlsx"
        write_single_sheet_excel(regional_df, regional_file, sheet_name='Regional_Comparisons')

        return regional_file

    def _create_cofog_sheet(self) -> Path:
        """Create COFOG breakdowns sheet"""
        if 'synthetic_cofog' in self.results['cofog_breakdowns']:
            cofog_df = self.results['cofog_breakdowns']['synthetic_cofog']
        else:
            # Create empty dataframe if no COFOG data
            cofog_df = pd.DataFrame(columns=['country_code', 'country_name', 'year', 'total_expenditure_pct_gdp'])

        cofog_file = self.output_dir / "cofog_expenditure_breakdowns.xlsx"
        write_single_sheet_excel(cofog_df, cofog_file, sheet_name='COFOG_Breakdowns')

        return cofog_file

    def _create_trends_sheet(self) -> Path:
        """Create time series trends sheet"""
        trends_data = []

        # Global trends
        global_trends = self.wb_data.groupby('year')[['gov_expenditure_gdp', 'education_expenditure',
                                                      'health_expenditure', 'military_expenditure']].mean().reset_index()

        for _, row in global_trends.iterrows():
            trends_data.append({
                'geography': 'Global',
                'year': row['year'],
                'total_expenditure_pct_gdp': row['gov_expenditure_gdp'],
                'education_pct_gdp': row['education_expenditure'],
                'health_pct_gdp': row['health_expenditure'],
                'military_pct_gdp': row['military_expenditure']
            })

        # Add regional trends for major regions
        for region in ['OECD', 'EU', 'G7']:
            if region in self.regional_mapping:
                countries = self.regional_mapping[region]
                region_data = self.wb_data[self.wb_data['country_code'].isin(countries)]

                if len(region_data) > 0:
                    regional_trends = region_data.groupby('year')[['gov_expenditure_gdp', 'education_expenditure',
                                                                  'health_expenditure', 'military_expenditure']].mean().reset_index()

                    for _, row in regional_trends.iterrows():
                        trends_data.append({
                            'geography': region,
                            'year': row['year'],
                            'total_expenditure_pct_gdp': row['gov_expenditure_gdp'],
                            'education_pct_gdp': row['education_expenditure'],
                            'health_pct_gdp': row['health_expenditure'],
                            'military_pct_gdp': row['military_expenditure']
                        })

        trends_df = pd.DataFrame(trends_data)
        trends_file = self.output_dir / "expenditure_time_series.xlsx"
        write_single_sheet_excel(trends_df, trends_file, sheet_name='Time_Series')

        return trends_file

    def create_visualization_showcase(self) -> List[str]:
        """Create visualization showcase for expenditure analysis"""
        logger.info("\n" + "=" * 80)
        logger.info("Creating Expenditure Visualization Showcase")
        logger.info("=" * 80)

        viz_dir = self.output_dir.parent / "PDFs"
        viz_dir.mkdir(parents=True, exist_ok=True)

        charts_created = []

        # Chart 1: Global Expenditure Trends
        chart1 = self._create_global_trends_chart(viz_dir)
        charts_created.append(chart1)

        # Chart 2: Regional Comparison
        chart2 = self._create_regional_comparison_chart(viz_dir)
        charts_created.append(chart2)

        # Chart 3: Top Countries Rankings
        chart3 = self._create_rankings_chart(viz_dir)
        charts_created.append(chart3)

        # Chart 4: COFOG Distribution (if data available)
        chart4 = self._create_cofog_distribution_chart(viz_dir)
        charts_created.append(chart4)

        logger.info(f"✅ Created {len(charts_created)} expenditure visualization charts")
        return charts_created

    def _create_global_trends_chart(self, output_dir: Path) -> str:
        """Create global expenditure trends chart"""
        plt.figure(figsize=(12, 8))

        global_data = self.wb_data.groupby('year')[['gov_expenditure_gdp', 'education_expenditure',
                                                   'health_expenditure', 'military_expenditure']].mean()

        plt.plot(global_data.index, global_data['gov_expenditure_gdp'], linewidth=3, label='Total Government Expenditure', color='#2E86AB')
        plt.plot(global_data.index, global_data['education_expenditure'], linewidth=2.5, label='Education', color='#A23B72')
        plt.plot(global_data.index, global_data['health_expenditure'], linewidth=2.5, label='Health', color='#F18F01')
        plt.plot(global_data.index, global_data['military_expenditure'], linewidth=2.5, label='Military', color='#C73E1D')

        plt.title('Global Government Expenditure Trends (% of GDP)\n2000-2024', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('% of GDP', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        chart_file = output_dir / "global_expenditure_trends.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_regional_comparison_chart(self, output_dir: Path) -> str:
        """Create regional comparison chart"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        latest_year = self.wb_data['year'].max()

        # Plot for each sector
        sectors = ['gov_expenditure_gdp', 'education_expenditure', 'health_expenditure', 'military_expenditure']
        titles = ['Total Expenditure', 'Education', 'Health', 'Military']
        axes = [ax1, ax2, ax3, ax4]

        for sector, title, ax in zip(sectors, titles, axes):
            regional_data = []
            for region_name, countries in self.regional_mapping.items():
                if region_name in ['OECD', 'EU', 'G7', 'BRICS']:
                    region_df = self.wb_data[self.wb_data['country_code'].isin(countries)]
                    year_data = region_df[region_df['year'] == latest_year]

                    if len(year_data) > 0 and sector in year_data.columns:
                        regional_data.append({
                            'region': region_name,
                            'value': year_data[sector].mean()
                        })

            if regional_data:
                df = pd.DataFrame(regional_data)
                ax.bar(df['region'], df['value'], color=['#2E86AB', '#A23B72', '#F18F01', '#C73E1D'])
                ax.set_title(f'{title} ({latest_year})', fontweight='bold')
                ax.set_ylabel('% of GDP')
                ax.tick_params(axis='x', rotation=45)
                ax.grid(True, alpha=0.3)

        plt.suptitle('Regional Government Expenditure Comparison\n(% of GDP)', fontsize=16, fontweight='bold')
        plt.tight_layout()

        chart_file = output_dir / "regional_expenditure_comparison.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_rankings_chart(self, output_dir: Path) -> str:
        """Create top countries rankings chart"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        latest_year = self.wb_data['year'].max()
        latest_data = self.wb_data[self.wb_data['year'] == latest_year]

        sectors = ['gov_expenditure_gdp', 'education_expenditure', 'health_expenditure', 'military_expenditure']
        titles = ['Total Expenditure', 'Education', 'Health', 'Military']
        axes = [ax1, ax2, ax3, ax4]

        for sector, title, ax in zip(sectors, titles, axes):
            if sector in latest_data.columns:
                clean_data = latest_data.dropna(subset=[sector])
                top_10 = clean_data.nlargest(10, sector)

                ax.barh(range(len(top_10)), top_10[sector], color='#2E86AB')
                ax.set_yticks(range(len(top_10)))
                ax.set_yticklabels([f"{code}" for code in top_10['country_code']])
                ax.set_title(f'Top 10 Countries - {title} ({latest_year})', fontweight='bold')
                ax.set_xlabel('% of GDP')
                ax.invert_yaxis()
                ax.grid(True, alpha=0.3)

        plt.suptitle('Top Countries by Government Expenditure Category\n(% of GDP)', fontsize=16, fontweight='bold')
        plt.tight_layout()

        chart_file = output_dir / "expenditure_rankings_top_countries.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_cofog_distribution_chart(self, output_dir: Path) -> str:
        """Create COFOG distribution chart"""
        plt.figure(figsize=(14, 8))

        if 'synthetic_cofog' in self.results['cofog_breakdowns']:
            cofog_df = self.results['cofog_breakdowns']['synthetic_cofog']
            latest_year = cofog_df['year'].max()
            latest_data = cofog_df[cofog_df['year'] == latest_year]

            # Check what columns are available
            available_sectors = []
            for sector in ['education_pct_gdp', 'health_pct_gdp', 'defense_pct_gdp']:
                if sector in latest_data.columns:
                    available_sectors.append(sector)

            if 'other_services_pct_gdp' in latest_data.columns:
                available_sectors.append('other_services_pct_gdp')

            if len(available_sectors) > 0:
                # Select countries with available data
                complete_countries = latest_data.dropna(subset=[available_sectors[0]])

                if len(complete_countries) > 0:
                    # Get top 15 countries by total expenditure
                    top_countries = complete_countries.nlargest(15, 'total_expenditure_pct_gdp')

                    # Create stacked bar chart with available sectors
                    sector_mapping = {
                        'education_pct_gdp': 'Education',
                        'health_pct_gdp': 'Health',
                        'defense_pct_gdp': 'Defense',
                        'other_services_pct_gdp': 'Other Services'
                    }

                    sector_colors = {
                        'education_pct_gdp': '#A23B72',
                        'health_pct_gdp': '#F18F01',
                        'defense_pct_gdp': '#C73E1D',
                        'other_services_pct_gdp': '#2E86AB'
                    }

                    bottom = np.zeros(len(top_countries))

                    for sector in available_sectors:
                        if sector in top_countries.columns:
                            values = top_countries[sector].fillna(0)
                            plt.bar(range(len(top_countries)), values, bottom=bottom,
                                   label=sector_mapping[sector], color=sector_colors[sector], alpha=0.8)
                            bottom += values

                    plt.title('Government Expenditure by Function - Top 15 Countries\n(% of GDP)',
                             fontsize=16, fontweight='bold', pad=20)
                    plt.xlabel('Countries', fontsize=12)
                    plt.ylabel('% of GDP', fontsize=12)
                    plt.xticks(range(len(top_countries)),
                              [f"{code}" for code in top_countries['country_code']], rotation=45)
                    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                    plt.grid(True, alpha=0.3)
                    plt.tight_layout()

        chart_file = output_dir / "cofog_distribution_top_countries.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def integrate_with_countries(self) -> bool:
        """Integrate expenditure analysis into country directories"""
        logger.info("\n" + "=" * 80)
        logger.info("Integrating Expenditure Analysis with Country Directories")
        logger.info("=" * 80)

        if not COUNTRIES_DIR.exists():
            logger.warning("Countries directory not found. Skipping integration.")
            return False

        countries_updated = 0

        for country_dir in COUNTRIES_DIR.iterdir():
            if country_dir.is_dir() and len(country_dir.name) in [2, 3]:
                country_code = country_dir.name
                output_data_dir = country_dir / "Output" / "Data"
                output_data_dir.mkdir(parents=True, exist_ok=True)

                # Get country expenditure data
                country_data = self.wb_data[self.wb_data['country_code'] == country_code]

                if len(country_data) > 0:
                    # Create country-specific expenditure file
                    country_file = output_data_dir / f"{country_code}_expenditure_analysis.xlsx"
                    write_single_sheet_excel(country_data, country_file, sheet_name='Expenditure_Data')

                    countries_updated += 1

        logger.info(f"✅ Updated {countries_updated} country directories with expenditure data")
        return True

    def run_complete_analysis(self) -> Dict:
        """Run complete government expenditure analysis"""
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE GOVERNMENT EXPENDITURE ANALYSIS")
        logger.info("=" * 80)

        results = {}

        # Load data
        if not self.load_world_bank_data():
            logger.error("Failed to load data. Analysis aborted.")
            return results

        # Run analysis
        logger.info("\n🔍 Running expenditure pattern analysis...")
        expenditure_patterns = self.analyze_expenditure_patterns()
        results['expenditure_patterns'] = expenditure_patterns

        logger.info("\n📊 Creating COFOG breakdowns...")
        cofog_breakdowns = self.create_cofog_breakdowns()
        results['cofog_breakdowns'] = cofog_breakdowns

        logger.info("\n📈 Generating Excel outputs...")
        excel_files = self.generate_excel_outputs()
        results['excel_files'] = excel_files

        logger.info("\n🎨 Creating visualizations...")
        charts = self.create_visualization_showcase()
        results['charts'] = charts

        logger.info("\n🌐 Integrating with country directories...")
        integration_success = self.integrate_with_countries()
        results['country_integration'] = integration_success

        # Save analysis summary
        summary_file = self.output_dir / "expenditure_analysis_summary.json"
        with open(summary_file, 'w') as f:
            # Convert pandas objects to JSON-serializable format
            json_results = self._convert_to_json(results)
            json.dump(json_results, f, indent=2, default=str)

        logger.info(f"\n✅ Analysis complete! Summary saved to: {summary_file.name}")

        return results

    def _convert_to_json(self, obj):
        """Convert pandas objects to JSON-serializable format"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif isinstance(obj, dict):
            return {k: self._convert_to_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_json(item) for item in obj]
        elif pd.isna(obj):
            return None
        else:
            return obj


def main():
    """Main execution function"""
    analyzer = GovernmentExpenditureAnalyzer()

    logger.info("🚀 Starting Government Expenditure Analysis")
    logger.info("Project: Gerhard - Fiscal Analysis Expansion")

    results = analyzer.run_complete_analysis()

    if results:
        logger.info("\n" + "=" * 80)
        logger.info("🎉 EXPENDITURE ANALYSIS COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"📊 Excel files created: {len(results.get('excel_files', {}))}")
        logger.info(f"📈 Charts created: {len(results.get('charts', []))}")
        logger.info(f"🌐 Country integration: {'✅ Success' if results.get('country_integration') else '❌ Failed'}")

        logger.info("\n📋 Key Deliverables:")
        for file_type, file_path in results.get('excel_files', {}).items():
            logger.info(f"  • {file_type}: {Path(file_path).name}")

    else:
        logger.error("❌ Analysis failed to complete")


if __name__ == "__main__":
    main()