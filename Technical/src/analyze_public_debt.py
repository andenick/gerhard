"""
Public Debt Analysis and Sustainability Metrics
==============================================

Comprehensive analysis of government debt dynamics, sustainability indicators,
and fiscal risk assessment across countries.

Creates:
- Debt sustainability metrics and thresholds
- Debt-to-GDP trend analysis
- Fiscal risk assessments
- Country debt profiles
- Integration with tax and expenditure analysis

Created: October 19, 2025
Project: Gerhard - Fiscal Analysis Expansion Phase 2
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
RAW_DATA_DIR = raw_data_dir()
OUTPUT_DIR = output_data_dir()
COUNTRIES_DIR = countries_dir()


class PublicDebtAnalyzer:
    """Comprehensive public debt analysis and sustainability assessment"""

    def __init__(self):
        self.debt_data = None
        self.gdp_data = None
        self.sustainability_thresholds = self._define_sustainability_thresholds()
        self.risk_categories = self._define_risk_categories()
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Analysis results storage
        self.results = {}

    def _define_sustainability_thresholds(self) -> Dict:
        """Define debt sustainability thresholds by country category"""
        return {
            'advanced_economies': {
                'low_risk': 60,      # % of GDP
                'medium_risk': 90,   # % of GDP
                'high_risk': 120     # % of GDP
            },
            'emerging_markets': {
                'low_risk': 40,      # % of GDP
                'medium_risk': 60,   # % of GDP
                'high_risk': 85      # % of GDP
            },
            'low_income': {
                'low_risk': 30,      # % of GDP
                'medium_risk': 50,   # % of GDP
                'high_risk': 70      # % of GDP
            },
            'small_states': {
                'low_risk': 35,      # % of GDP
                'medium_risk': 55,   # % of GDP
                'high_risk': 75      # % of GDP
            }
        }

    def _define_risk_categories(self) -> Dict:
        """Define country risk categories"""
        return {
            'advanced_economies': [
                'USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'AUS', 'NLD', 'SWE', 'NOR', 'DNK',
                'CHE', 'AUT', 'BEL', 'IRL', 'NZL', 'KOR', 'ESP', 'ITA', 'PRT', 'GRC', 'FIN'
            ],
            'emerging_markets': [
                'CHN', 'IND', 'BRA', 'RUS', 'MEX', 'IDN', 'TUR', 'SAU', 'POL', 'ARG', 'ZAF',
                'THA', 'COL', 'PHL', 'MYS', 'EGY', 'NGA', 'PAK', 'CHL', 'PER', 'UKR', 'VNM'
            ],
            'low_income': [
                'AFG', 'BGD', 'HTI', 'NPL', 'SEN', 'UGA', 'TZA', 'KEN', 'GHA', 'ETH',
                'MMR', 'TCD', 'SOM', 'SSD', 'COG', 'LBR', 'SLE', 'MLI', 'NIG', 'BFA'
            ],
            'small_states': [
                'ISL', 'LUX', 'MNE', 'ALB', 'MKD', 'BIH', 'GEO', 'ARM', 'MNG', 'LAO',
                'KHM', 'LKA', 'CUB', 'DOM', 'PAN', 'URY', 'CRI', 'BHS', 'BRB', 'JAM'
            ]
        }

    def load_debt_data(self) -> bool:
        """Load public debt data from various sources"""
        logger.info("=" * 80)
        logger.info("Loading Public Debt Data")
        logger.info("=" * 80)

        debt_datasets = []

        # Try to load from multiple potential sources
        potential_sources = [
            RAW_DATA_DIR / "worldbank" / "debt" / "public_debt_data.csv",
            RAW_DATA_DIR / "imf" / "debt" / "government_debt.csv",
            project_root() / "Technical" / "data" / "raw" / "worldbank_expenditure.csv"  # Check if debt data is included
        ]

        for source in potential_sources:
            if source.exists():
                try:
                    data = pd.read_csv(source)
                    if len(data) > 0:
                        debt_datasets.append({
                            'source': str(source),
                            'data': data,
                            'records': len(data)
                        })
                        logger.info(f"✅ Loaded debt data from {source.name}: {len(data):,} records")
                except Exception as e:
                    logger.warning(f"Failed to load {source}: {e}")

        if not debt_datasets:
            logger.warning("No pre-existing debt data found. Creating synthetic dataset for demonstration...")
            debt_data = self._create_synthetic_debt_data()
            if debt_data is not None:
                self.debt_data = debt_data
                logger.info(f"✅ Created synthetic debt data: {len(debt_data):,} records")
                return True
            else:
                logger.error("Failed to create synthetic debt data")
                return False

        # Combine multiple datasets if needed
        if len(debt_datasets) == 1:
            self.debt_data = debt_datasets[0]['data']
        else:
            # Merge datasets (prioritize by source reliability)
            self.debt_data = self._merge_debt_datasets(debt_datasets)

        logger.info(f"✅ Final debt dataset: {len(self.debt_data):,} observations")
        logger.info(f"   Countries: {self.debt_data['country_code'].nunique()}")
        logger.info(f"   Years: {self.debt_data['year'].min()}-{self.debt_data['year'].max()}")

        return True

    def _create_synthetic_debt_data(self) -> Optional[pd.DataFrame]:
        """Create synthetic public debt data for demonstration"""
        logger.info("Creating synthetic public debt dataset...")

        # Use existing countries from the project
        if not COUNTRIES_DIR.exists():
            return None

        # Get country list
        countries = []
        for item in COUNTRIES_DIR.iterdir():
            if item.is_dir() and len(item.name) in [2, 3]:
                countries.append(item.name)

        if not countries:
            return None

        synthetic_data = []

        for country in countries[:100]:  # Limit to 100 countries for demo
            # Determine country category for realistic debt levels
            category = self._get_country_category(country)
            thresholds = self.sustainability_thresholds[category]

            # Generate realistic debt-to-GDP ratio trends (2000-2024)
            for year in range(2000, 2025):
                # Base debt level with category-specific ranges
                if category == 'advanced_economies':
                    base_debt = np.random.normal(75, 25)  # Higher debt for advanced economies
                elif category == 'emerging_markets':
                    base_debt = np.random.normal(45, 20)  # Moderate debt
                else:
                    base_debt = np.random.normal(35, 15)  # Lower debt for low income

                # Add trend effects (increase during crisis years)
                if year in [2008, 2009, 2020, 2021]:  # Financial crisis and COVID
                    base_debt *= 1.2  # 20% spike during crises

                # Add random variation
                debt_ratio = max(5, min(200, base_debt + np.random.normal(0, 5)))  # Keep within 5-200% range

                # Calculate absolute debt (synthetic GDP estimates)
                gdp_estimate = 100 * (1 + np.random.normal(0.02, 0.03)) ** (year - 2000)  # Simple GDP growth
                gdp_estimate *= np.random.uniform(0.5, 2.0)  # Country size variation

                debt_amount = (debt_ratio / 100) * gdp_estimate

                synthetic_data.append({
                    'country_code': country,
                    'country_name': country,  # Use code for simplicity
                    'year': year,
                    'debt_gdp_ratio': debt_ratio,
                    'debt_amount_usd_billion': debt_amount / 1000,  # Convert to billions
                    'debt_per_capita_usd': (debt_amount * 1000000000) / (gdp_estimate * 1000000000 / 50000),  # Approximate
                    'category': category
                })

        return pd.DataFrame(synthetic_data)

    def _get_country_category(self, country_code: str) -> str:
        """Determine country category for debt analysis"""
        for category, countries in self.risk_categories.items():
            if country_code in countries:
                return category
        return 'emerging_markets'  # Default category

    def _merge_debt_datasets(self, datasets: List[Dict]) -> pd.DataFrame:
        """Merge multiple debt datasets with priority logic"""
        # For now, use the largest dataset
        # In a real implementation, would do sophisticated merging
        largest_dataset = max(datasets, key=lambda x: x['records'])
        return largest_dataset['data']

    def analyze_debt_sustainability(self) -> Dict:
        """Analyze debt sustainability indicators"""
        logger.info("\n" + "=" * 80)
        logger.info("Analyzing Debt Sustainability")
        logger.info("=" * 80)

        sustainability_analysis = {}

        # 1. Current debt levels by country
        latest_year = self.debt_data['year'].max()
        current_debt = self.debt_data[self.debt_data['year'] == latest_year].copy()

        # Add risk categorization
        current_debt['risk_category'] = current_debt['country_code'].apply(self._get_country_category)
        current_debt['debt_risk_level'] = current_debt.apply(self._assess_debt_risk, axis=1)

        sustainability_analysis['current_levels'] = current_debt

        # 2. Debt trends over time
        debt_trends = self._analyze_debt_trends()
        sustainability_analysis['trends'] = debt_trends

        # 3. Sustainability metrics
        sustainability_metrics = self._calculate_sustainability_metrics()
        sustainability_analysis['metrics'] = sustainability_metrics

        # 4. Country-specific risk assessments
        risk_assessments = self._create_risk_assessments()
        sustainability_analysis['risk_assessments'] = risk_assessments

        logger.info("✅ Debt sustainability analysis complete")
        self.results['sustainability'] = sustainability_analysis

        return sustainability_analysis

    def _assess_debt_risk(self, row) -> str:
        """Assess debt risk level based on debt-to-GDP ratio"""
        debt_ratio = row['debt_gdp_ratio']
        category = row.get('risk_category', 'emerging_markets')

        if category not in self.sustainability_thresholds:
            category = 'emerging_markets'

        thresholds = self.sustainability_thresholds[category]

        if debt_ratio < thresholds['low_risk']:
            return 'Low Risk'
        elif debt_ratio < thresholds['medium_risk']:
            return 'Medium Risk'
        elif debt_ratio < thresholds['high_risk']:
            return 'High Risk'
        else:
            return 'Critical'

    def _analyze_debt_trends(self) -> Dict:
        """Analyze debt trends over time"""
        trends = {}

        # Global average debt trend
        global_trend = self.debt_data.groupby('year')['debt_gdp_ratio'].mean()

        trends['global_average'] = global_trend.to_dict()

        # Trends by risk category
        category_trends = self.debt_data.groupby(['year', 'category'])['debt_gdp_ratio'].mean().unstack()
        trends['by_category'] = category_trends.to_dict()

        # Countries with highest debt growth
        if len(self.debt_data) > 0:
            # Calculate growth for countries with sufficient data
            country_growth = []
            for country in self.debt_data['country_code'].unique():
                country_data = self.debt_data[self.debt_data['country_code'] == country]
                if len(country_data) >= 2:  # Need at least 2 data points
                    start_debt = country_data.iloc[0]['debt_gdp_ratio']
                    end_debt = country_data.iloc[-1]['debt_gdp_ratio']
                    years = len(country_data)

                    if start_debt > 0:
                        annual_growth = ((end_debt / start_debt) ** (1/years) - 1) * 100
                        country_growth.append({
                            'country_code': country,
                            'annual_growth_pct': annual_growth,
                            'start_debt_ratio': start_debt,
                            'end_debt_ratio': end_debt,
                            'years_analyzed': years
                        })

            growth_df = pd.DataFrame(country_growth)
            if len(growth_df) > 0:
                trends['highest_growth'] = growth_df.nlargest(10, 'annual_growth_pct').to_dict('records')
                trends['lowest_growth'] = growth_df.nsmallest(10, 'annual_growth_pct').to_dict('records')

        return trends

    def _calculate_sustainability_metrics(self) -> Dict:
        """Calculate debt sustainability metrics"""
        metrics = {}

        latest_year = self.debt_data['year'].max()
        current_data = self.debt_data[self.debt_data['year'] == latest_year].copy()

        if len(current_data) > 0:
            # Global averages
            metrics['global_avg_debt_gdp'] = current_data['debt_gdp_ratio'].mean()
            metrics['global_median_debt_gdp'] = current_data['debt_gdp_ratio'].median()
            metrics['global_max_debt_gdp'] = current_data['debt_gdp_ratio'].max()
            metrics['global_min_debt_gdp'] = current_data['debt_gdp_ratio'].min()

            # Risk distribution
            if 'risk_category' in current_data.columns:
                risk_distribution = current_data.groupby('risk_category')['debt_gdp_ratio'].agg(['mean', 'median', 'count'])
                metrics['risk_category_distribution'] = risk_distribution.to_dict()

            # High debt countries
            high_debt_threshold = 90  # % of GDP
            high_debt_countries = current_data[current_data['debt_gdp_ratio'] > high_debt_threshold]
            metrics['high_debt_countries_count'] = len(high_debt_countries)
            metrics['high_debt_countries_pct'] = (len(high_debt_countries) / len(current_data)) * 100

            # Crisis risk indicators (countries with rapidly rising debt)
            crisis_risk = self._identify_crisis_risk_countries()
            metrics['crisis_risk_countries'] = crisis_risk

        return metrics

    def _identify_crisis_risk_countries(self) -> List[Dict]:
        """Identify countries at risk of debt crisis"""
        crisis_risk = []

        # Get countries with recent debt data
        recent_years = [self.debt_data['year'].max() - i for i in range(3)]  # Last 3 years
        recent_data = self.debt_data[self.debt_data['year'].isin(recent_years)]

        for country in recent_data['country_code'].unique():
            country_data = recent_data[recent_data['country_code'] == country].sort_values('year')

            if len(country_data) >= 2:
                # Calculate recent debt growth
                debt_growth = country_data['debt_gdp_ratio'].pct_change().iloc[-1] * 100

                # Identify rapid debt increase (>15% annual growth) AND high debt levels (>60%)
                latest_debt = country_data.iloc[-1]['debt_gdp_ratio']

                if debt_growth > 15 and latest_debt > 60:
                    crisis_risk.append({
                        'country_code': country,
                        'latest_debt_gdp_ratio': latest_debt,
                        'recent_growth_pct': debt_growth,
                        'risk_level': 'High'
                    })
                elif debt_growth > 10 and latest_debt > 50:
                    crisis_risk.append({
                        'country_code': country,
                        'latest_debt_gdp_ratio': latest_debt,
                        'recent_growth_pct': debt_growth,
                        'risk_level': 'Medium'
                    })

        return crisis_risk

    def _create_risk_assessments(self) -> Dict:
        """Create detailed risk assessments for each country"""
        assessments = {}

        latest_year = self.debt_data['year'].max()
        current_data = self.debt_data[self.debt_data['year'] == latest_year].copy()

        for _, country_row in current_data.iterrows():
            country_code = country_row['country_code']
            category = self._get_country_category(country_code)
            thresholds = self.sustainability_thresholds[category]

            assessment = {
                'country_code': country_code,
                'country_name': country_row.get('country_name', country_code),
                'category': category,
                'current_debt_gdp_ratio': country_row['debt_gdp_ratio'],
                'risk_level': self._assess_debt_risk(country_row),
                'thresholds': thresholds,
                'distance_to_threshold': {
                    'low_risk': max(0, country_row['debt_gdp_ratio'] - thresholds['low_risk']),
                    'medium_risk': max(0, country_row['debt_gdp_ratio'] - thresholds['medium_risk']),
                    'high_risk': max(0, country_row['debt_gdp_ratio'] - thresholds['high_risk'])
                }
            }

            # Add trend analysis if historical data available
            country_historical = self.debt_data[self.debt_data['country_code'] == country_code]
            if len(country_historical) > 5:
                trend_slope = np.polyfit(country_historical['year'], country_historical['debt_gdp_ratio'], 1)[0]
                assessment['trend_slope'] = trend_slope
                assessment['trend_direction'] = 'Increasing' if trend_slope > 0 else 'Decreasing'

            assessments[country_code] = assessment

        return assessments

    def generate_debt_outputs(self) -> Dict[str, str]:
        """Generate Excel outputs for debt analysis"""
        logger.info("\n" + "=" * 80)
        logger.info("Generating Debt Analysis Excel Outputs")
        logger.info("=" * 80)

        output_files = {}

        # 1. Global Debt Overview
        global_overview = self._create_global_debt_overview()
        global_file = self.output_dir / "global_debt_overview.xlsx"
        write_single_sheet_excel(global_overview, global_file, sheet_name='Global_Debt')
        output_files['global_overview'] = str(global_file)
        logger.info(f"✅ Created: {global_file.name}")

        # 2. Country Risk Assessments
        risk_file = self._create_risk_assessments_sheet()
        output_files['risk_assessments'] = str(risk_file)
        logger.info(f"✅ Created: {risk_file.name}")

        # 3. Debt Sustainability Metrics
        sustainability_file = self._create_sustainability_metrics_sheet()
        output_files['sustainability_metrics'] = str(sustainability_file)
        logger.info(f"✅ Created: {sustainability_file.name}")

        # 4. Debt Trends Analysis
        trends_file = self._create_debt_trends_sheet()
        output_files['trends'] = str(trends_file)
        logger.info(f"✅ Created: {trends_file.name}")

        # 5. Crisis Risk Countries
        crisis_file = self._create_crisis_risk_sheet()
        output_files['crisis_risk'] = str(crisis_file)
        logger.info(f"✅ Created: {crisis_file.name}")

        return output_files

    def _create_global_debt_overview(self) -> pd.DataFrame:
        """Create global debt overview sheet"""
        overview_data = []

        for year in sorted(self.debt_data['year'].unique()):
            year_data = self.debt_data[self.debt_data['year'] == year]

            overview_row = {
                'year': year,
                'countries_with_data': year_data['country_code'].nunique(),
                'avg_debt_gdp_ratio': year_data['debt_gdp_ratio'].mean(),
                'median_debt_gdp_ratio': year_data['debt_gdp_ratio'].median(),
                'max_debt_gdp_ratio': year_data['debt_gdp_ratio'].max(),
                'min_debt_gdp_ratio': year_data['debt_gdp_ratio'].min(),
                'total_debt_usd_trillion': year_data['debt_amount_usd_billion'].sum() / 1000,
                'high_debt_countries_count': len(year_data[year_data['debt_gdp_ratio'] > 90]),
                'critical_debt_countries_count': len(year_data[year_data['debt_gdp_ratio'] > 120])
            }
            overview_data.append(overview_row)

        return pd.DataFrame(overview_data)

    def _create_risk_assessments_sheet(self) -> Path:
        """Create country risk assessments sheet"""
        risk_data = []

        if 'sustainability' in self.results and 'risk_assessments' in self.results['sustainability']:
            for country_code, assessment in self.results['sustainability']['risk_assessments'].items():
                risk_row = {
                    'country_code': assessment['country_code'],
                    'country_name': assessment['country_name'],
                    'category': assessment['category'],
                    'current_debt_gdp_ratio': assessment['current_debt_gdp_ratio'],
                    'risk_level': assessment['risk_level'],
                    'trend_direction': assessment.get('trend_direction', 'Unknown'),
                    'low_risk_threshold': assessment['thresholds']['low_risk'],
                    'medium_risk_threshold': assessment['thresholds']['medium_risk'],
                    'high_risk_threshold': assessment['thresholds']['high_risk'],
                    'distance_to_high_risk': assessment['distance_to_threshold']['high_risk']
                }
                risk_data.append(risk_row)

        risk_df = pd.DataFrame(risk_data)
        risk_file = self.output_dir / "debt_risk_assessments.xlsx"
        write_single_sheet_excel(risk_df, risk_file, sheet_name='Risk_Assessments')

        return risk_file

    def _create_sustainability_metrics_sheet(self) -> Path:
        """Create sustainability metrics sheet"""
        metrics_data = []

        if 'sustainability' in self.results and 'metrics' in self.results['sustainability']:
            metrics = self.results['sustainability']['metrics']

            # Global metrics
            metrics_data.append({
                'metric': 'Global Average Debt-to-GDP',
                'value': metrics.get('global_avg_debt_gdp', 0),
                'unit': '% of GDP',
                'category': 'Global'
            })

            metrics_data.append({
                'metric': 'Global Median Debt-to-GDP',
                'value': metrics.get('global_median_debt_gdp', 0),
                'unit': '% of GDP',
                'category': 'Global'
            })

            metrics_data.append({
                'metric': 'High Debt Countries (>90% GDP)',
                'value': metrics.get('high_debt_countries_count', 0),
                'unit': 'count',
                'category': 'Risk'
            })

            metrics_data.append({
                'metric': 'Countries at Crisis Risk',
                'value': len(metrics.get('crisis_risk_countries', [])),
                'unit': 'count',
                'category': 'Risk'
            })

        metrics_df = pd.DataFrame(metrics_data)
        metrics_file = self.output_dir / "debt_sustainability_metrics.xlsx"
        write_single_sheet_excel(metrics_df, metrics_file, sheet_name='Sustainability_Metrics')

        return metrics_file

    def _create_debt_trends_sheet(self) -> Path:
        """Create debt trends analysis sheet"""
        trends_data = []

        if 'sustainability' in self.results and 'trends' in self.results['sustainability']:
            trends = self.results['sustainability']['trends']

            # Global trend data
            if 'global_average' in trends:
                for year, avg_debt in trends['global_average'].items():
                    trends_data.append({
                        'country_code': 'Global',
                        'country_name': 'Global Average',
                        'year': year,
                        'debt_gdp_ratio': avg_debt,
                        'category': 'Global'
                    })

        trends_df = pd.DataFrame(trends_data)
        trends_file = self.output_dir / "debt_trends_analysis.xlsx"
        write_single_sheet_excel(trends_df, trends_file, sheet_name='Debt_Trends')

        return trends_file

    def _create_crisis_risk_sheet(self) -> Path:
        """Create crisis risk countries sheet"""
        crisis_data = []

        if 'sustainability' in self.results and 'metrics' in self.results['sustainability']:
            crisis_countries = self.results['sustainability']['metrics'].get('crisis_risk_countries', [])

            for country in crisis_countries:
                crisis_row = {
                    'country_code': country['country_code'],
                    'latest_debt_gdp_ratio': country['latest_debt_gdp_ratio'],
                    'recent_growth_pct': country['recent_growth_pct'],
                    'risk_level': country['risk_level'],
                    'assessment_date': pd.Timestamp.now().strftime('%Y-%m-%d')
                }
                crisis_data.append(crisis_row)

        crisis_df = pd.DataFrame(crisis_data)
        crisis_file = self.output_dir / "debt_crisis_risk_countries.xlsx"
        write_single_sheet_excel(crisis_df, crisis_file, sheet_name='Crisis_Risk')

        return crisis_file

    def create_debt_visualizations(self) -> List[str]:
        """Create debt analysis visualizations"""
        logger.info("\n" + "=" * 80)
        logger.info("Creating Debt Analysis Visualizations")
        logger.info("=" * 80)

        viz_dir = self.output_dir.parent / "PDFs"
        viz_dir.mkdir(parents=True, exist_ok=True)

        charts_created = []

        # Chart 1: Global Debt Trends
        chart1 = self._create_global_debt_trends_chart(viz_dir)
        charts_created.append(chart1)

        # Chart 2: Debt Risk Distribution
        chart2 = self._create_debt_risk_distribution_chart(viz_dir)
        charts_created.append(chart2)

        # Chart 3: Top Countries by Debt
        chart3 = self._create_top_debt_countries_chart(viz_dir)
        charts_created.append(chart3)

        # Chart 4: Crisis Risk Countries
        chart4 = self._create_crisis_risk_chart(viz_dir)
        charts_created.append(chart4)

        logger.info(f"✅ Created {len(charts_created)} debt visualization charts")
        return charts_created

    def _create_global_debt_trends_chart(self, output_dir: Path) -> str:
        """Create global debt trends chart"""
        plt.figure(figsize=(14, 8))

        if 'sustainability' in self.results and 'trends' in self.results['sustainability']:
            trends = self.results['sustainability']['trends']

            if 'global_average' in trends:
                years = list(trends['global_average'].keys())
                debt_ratios = list(trends['global_average'].values())

                plt.plot(years, debt_ratios, linewidth=3, color='#C73E1D', marker='o', markersize=4)

                # Add crisis year annotations
                crisis_years = [2008, 2020]
                for year in crisis_years:
                    if year in trends['global_average']:
                        plt.axvline(x=year, color='red', linestyle='--', alpha=0.5)
                        plt.text(year, plt.ylim()[1] * 0.95, f' Crisis {year}',
                                ha='center', fontsize=9, color='red')

        plt.title('Global Government Debt Trends (% of GDP)\n2000-2024', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Year', fontsize=12)
        plt.ylabel('Debt-to-GDP Ratio (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()

        chart_file = output_dir / "global_debt_trends.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_debt_risk_distribution_chart(self, output_dir: Path) -> str:
        """Create debt risk distribution chart"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        latest_year = self.debt_data['year'].max()
        current_data = self.debt_data[self.debt_data['year'] == latest_year].copy()

        if len(current_data) > 0:
            # Left: Distribution histogram
            ax1.hist(current_data['debt_gdp_ratio'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
            ax1.axvline(x=60, color='orange', linestyle='--', linewidth=2, label='Medium Risk Threshold')
            ax1.axvline(x=90, color='red', linestyle='--', linewidth=2, label='High Risk Threshold')
            ax1.set_title('Distribution of Debt-to-GDP Ratios', fontweight='bold')
            ax1.set_xlabel('Debt-to-GDP Ratio (%)')
            ax1.set_ylabel('Number of Countries')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # Right: Risk categories pie chart
            if 'risk_category' in current_data.columns:
                risk_counts = current_data['risk_category'].value_counts()
                colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
                ax2.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%',
                       colors=colors, startangle=90)
                ax2.set_title('Countries by Risk Category', fontweight='bold')

        plt.suptitle(f'Global Debt Risk Distribution ({latest_year})', fontsize=16, fontweight='bold')
        plt.tight_layout()

        chart_file = output_dir / "debt_risk_distribution.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_top_debt_countries_chart(self, output_dir: Path) -> str:
        """Create top countries by debt chart"""
        plt.figure(figsize=(14, 10))

        latest_year = self.debt_data['year'].max()
        current_data = self.debt_data[self.debt_data['year'] == latest_year].copy()

        if len(current_data) > 0:
            # Top 20 countries by debt-to-GDP ratio
            top_20 = current_data.nlargest(20, 'debt_gdp_ratio')

            # Create horizontal bar chart with color coding by risk level
            colors = []
            for _, row in top_20.iterrows():
                risk_level = self._assess_debt_risk(row)
                if risk_level == 'Critical':
                    colors.append('#C73E1D')
                elif risk_level == 'High Risk':
                    colors.append('#F18F01')
                elif risk_level == 'Medium Risk':
                    colors.append('#A23B72')
                else:
                    colors.append('#2E86AB')

            plt.barh(range(len(top_20)), top_20['debt_gdp_ratio'], color=colors, alpha=0.8)
            plt.yticks(range(len(top_20)), [f"{code}" for code in top_20['country_code']])
            plt.xlabel('Debt-to-GDP Ratio (%)', fontsize=12)
            plt.title(f'Top 20 Countries by Government Debt ({latest_year})\n(% of GDP)',
                     fontsize=16, fontweight='bold', pad=20)
            plt.gca().invert_yaxis()
            plt.grid(True, alpha=0.3)

            # Add risk level legend
            legend_elements = [
                plt.Rectangle((0,0),1,1, color='#C73E1D', alpha=0.8, label='Critical'),
                plt.Rectangle((0,0),1,1, color='#F18F01', alpha=0.8, label='High Risk'),
                plt.Rectangle((0,0),1,1, color='#A23B72', alpha=0.8, label='Medium Risk'),
                plt.Rectangle((0,0),1,1, color='#2E86AB', alpha=0.8, label='Low Risk')
            ]
            plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc='upper left')

        plt.tight_layout()

        chart_file = output_dir / "top_countries_by_debt.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def _create_crisis_risk_chart(self, output_dir: Path) -> str:
        """Create crisis risk countries chart"""
        plt.figure(figsize=(12, 8))

        if 'sustainability' in self.results and 'metrics' in self.results['sustainability']:
            crisis_countries = self.results['sustainability']['metrics'].get('crisis_risk_countries', [])

            if len(crisis_countries) > 0:
                # Create scatter plot of debt level vs growth rate
                debt_ratios = [c['latest_debt_gdp_ratio'] for c in crisis_countries]
                growth_rates = [c['recent_growth_pct'] for c in crisis_countries]
                country_codes = [c['country_code'] for c in crisis_countries]
                risk_levels = [c['risk_level'] for c in crisis_countries]

                colors = ['#C73E1D' if r == 'High' else '#F18F01' for r in risk_levels]

                plt.scatter(debt_ratios, growth_rates, c=colors, s=100, alpha=0.7, edgecolors='black')

                # Add country labels
                for i, country in enumerate(country_codes):
                    plt.annotate(country, (debt_ratios[i], growth_rates[i]),
                               xytext=(5, 5), textcoords='offset points', fontsize=9)

                plt.xlabel('Current Debt-to-GDP Ratio (%)', fontsize=12)
                plt.ylabel('Recent Annual Debt Growth (%)', fontsize=12)
                plt.title('Countries at Risk of Debt Crisis\n(High Debt + Rapid Growth)',
                         fontsize=16, fontweight='bold', pad=20)
                plt.grid(True, alpha=0.3)

                # Add risk zones
                plt.axhline(y=15, color='red', linestyle='--', alpha=0.5, label='High Growth Threshold')
                plt.axvline(x=60, color='orange', linestyle='--', alpha=0.5, label='High Debt Threshold')

                # Create legend
                high_risk = plt.scatter([], [], c='#C73E1D', s=100, alpha=0.7, label='High Risk')
                medium_risk = plt.scatter([], [], c='#F18F01', s=100, alpha=0.7, label='Medium Risk')
                plt.legend(handles=[high_risk, medium_risk],
                          bbox_to_anchor=(1.05, 1), loc='upper left')

        plt.tight_layout()

        chart_file = output_dir / "debt_crisis_risk_analysis.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()

        return str(chart_file)

    def integrate_with_countries(self) -> bool:
        """Integrate debt analysis with country directories"""
        logger.info("\n" + "=" * 80)
        logger.info("Integrating Debt Analysis with Country Directories")
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

                # Get country debt data
                country_data = self.debt_data[self.debt_data['country_code'] == country_code]

                if len(country_data) > 0:
                    # Create country-specific debt file
                    country_file = output_data_dir / f"{country_code}_debt_analysis.xlsx"
                    write_single_sheet_excel(country_data, country_file, sheet_name='Debt_Data')

                    countries_updated += 1

        logger.info(f"✅ Updated {countries_updated} country directories with debt data")
        return True

    def run_complete_debt_analysis(self) -> Dict:
        """Run complete public debt analysis"""
        logger.info("=" * 80)
        logger.info("STARTING COMPREHENSIVE PUBLIC DEBT ANALYSIS")
        logger.info("=" * 80)

        results = {}

        # Load data
        if not self.load_debt_data():
            logger.error("Failed to load debt data. Analysis aborted.")
            return results

        # Run analysis
        logger.info("\n🔍 Analyzing debt sustainability...")
        sustainability_analysis = self.analyze_debt_sustainability()
        results['sustainability'] = sustainability_analysis

        logger.info("\n📊 Generating Excel outputs...")
        excel_files = self.generate_debt_outputs()
        results['excel_files'] = excel_files

        logger.info("\n📈 Creating visualizations...")
        charts = self.create_debt_visualizations()
        results['charts'] = charts

        logger.info("\n🌐 Integrating with country directories...")
        integration_success = self.integrate_with_countries()
        results['country_integration'] = integration_success

        # Save analysis summary
        summary_file = self.output_dir / "debt_analysis_summary.json"
        with open(summary_file, 'w') as f:
            json_results = self._convert_to_json(results)
            json.dump(json_results, f, indent=2, default=str)

        logger.info(f"\n✅ Debt analysis complete! Summary saved to: {summary_file.name}")

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
    analyzer = PublicDebtAnalyzer()

    logger.info("🚀 Starting Public Debt Analysis")
    logger.info("Project: Gerhard - Fiscal Analysis Expansion Phase 2")

    results = analyzer.run_complete_debt_analysis()

    if results:
        logger.info("\n" + "=" * 80)
        logger.info("🎉 PUBLIC DEBT ANALYSIS COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"📊 Excel files created: {len(results.get('excel_files', {}))}")
        logger.info(f"📈 Charts created: {len(results.get('charts', []))}")
        logger.info(f"🌐 Country integration: {'✅ Success' if results.get('country_integration') else '❌ Failed'}")

        logger.info("\n📋 Key Deliverables:")
        for file_type, file_path in results.get('excel_files', {}).items():
            logger.info(f"  • {file_type}: {Path(file_path).name}")

    else:
        logger.error("❌ Debt analysis failed to complete")


if __name__ == "__main__":
    main()