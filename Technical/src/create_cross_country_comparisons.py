#!/usr/bin/env python3
"""
Cross-Country Fiscal Comparison Analysis
Creates comprehensive fiscal comparisons across progressivity, sustainability, and development patterns
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

class CrossCountryComparator:
    """Creates comprehensive cross-country fiscal comparisons"""

    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.comparisons_dir = self.output_dir / "analysis" / "cross_country_comparisons"
        self.comparisons_dir.mkdir(parents=True, exist_ok=True)

        # Data sources
        self.worldbank_tax_file = self.data_dir / "Output/Data/world_bank_tax_revenue.xlsx"
        self.worldbank_exp_file = self.data_dir / "processed/worldbank_expenditure_master.xlsx"
        self.fiscal_balances_file = self.data_dir / "analysis/fiscal_balances/fiscal_balances_master_dataset.xlsx"
        self.oecd_data_file = self.data_dir / "downloads/raw/oecd_revenue/oecd_revenue_summary.json"
        self.wid_data_file = self.data_dir / "processed/wid_inequality/wid_inequality_master_dataset.xlsx"

        # Country classifications
        self.income_groups = {
            'high_income': [
                'US', 'JP', 'DE', 'FR', 'GB', 'IT', 'CA', 'AU', 'CH', 'NO', 'SE', 'DK',
                'NL', 'BE', 'AT', 'FI', 'IE', 'NZ', 'SG', 'KR', 'ISL', 'LUX', 'ISR'
            ],
            'upper_middle': [
                'CN', 'BR', 'RU', 'MX', 'IN', 'ID', 'TR', 'SA', 'ZA', 'AR', 'CL', 'CO',
                'PE', 'MY', 'TH', 'PH', 'PL', 'CZ', 'HU', 'GR', 'PT'
            ],
            'lower_middle': [
                'EG', 'NG', 'KE', 'GH', 'BD', 'PK', 'VN', 'UA', 'RO', 'BG', 'SL', 'CM',
                'CI', 'SN', 'UG', 'TZ', 'BD'
            ],
            'low_income': [
                'AF', 'HT', 'ET', 'MW', 'MZ', 'ZM', 'ZW', 'ML', 'BF', 'NE', 'CF', 'SS',
                'LR', 'SD', 'GN'
            ]
        }

        # Development patterns
        self.development_patterns = {
            'anglo_saxon': ['US', 'GB', 'CA', 'AU', 'NZ', 'IE'],
            'continental_european': ['DE', 'FR', 'NL', 'BE', 'AT', 'CH'],
            'nordic': ['SE', 'NO', 'DK', 'FI', 'IS'],
            'mediterranean': ['IT', 'ES', 'PT', 'GR'],
            'east_asian': ['JP', 'KR', 'SG', 'TW', 'HK'],
            'emerging_asian': ['CN', 'IN', 'ID', 'MY', 'TH', 'PH', 'VN'],
            'latin_american': ['BR', 'MX', 'AR', 'CL', 'CO', 'PE'],
            'african_developing': ['ZA', 'NG', 'KE', 'GH', 'EG', 'MA'],
            'transition_economies': ['RU', 'PL', 'CZ', 'HU', 'RO', 'BG']
        }

    def load_all_data_sources(self) -> Dict[str, pd.DataFrame]:
        """Load data from all available sources"""
        logger.info("Loading data from all sources...")

        data_sources = {}

        # World Bank tax data
        if self.worldbank_tax_file.exists():
            try:
                df = pd.read_excel(self.worldbank_tax_file)
                data_sources['worldbank_tax'] = df
                logger.info(f"✓ World Bank tax data: {len(df)} observations")
            except Exception as e:
                logger.warning(f"Error loading World Bank tax data: {e}")

        # World Bank expenditure data
        if self.worldbank_exp_file.exists():
            try:
                df = pd.read_excel(self.worldbank_exp_file)
                data_sources['worldbank_expenditure'] = df
                logger.info(f"✓ World Bank expenditure data: {len(df)} observations")
            except Exception as e:
                logger.warning(f"Error loading World Bank expenditure data: {e}")

        # Fiscal balances data
        if self.fiscal_balances_file.exists():
            try:
                df = pd.read_excel(self.fiscal_balances_file)
                data_sources['fiscal_balances'] = df
                logger.info(f"✓ Fiscal balances data: {len(df)} observations")
            except Exception as e:
                logger.warning(f"Error loading fiscal balances data: {e}")

        # WID inequality data
        if self.wid_data_file.exists():
            try:
                df = pd.read_excel(self.wid_data_file)
                data_sources['wid_inequality'] = df
                logger.info(f"✓ WID inequality data: {len(df)} observations")
            except Exception as e:
                logger.warning(f"Error loading WID data: {e}")

        logger.info(f"✅ Loaded {len(data_sources)} data sources")
        return data_sources

    def create_tax_progressivity_index(self, data_sources: Dict) -> pd.DataFrame:
        """Create tax progressivity index for countries"""
        logger.info("Creating tax progressivity index...")

        progressivity_data = []

        if 'worldbank_tax' in data_sources:
            tax_df = data_sources['worldbank_tax']
            latest_year = tax_df['year'].max() if 'year' in tax_df.columns else 2021

            # Get latest data
            latest_data = tax_df[tax_df['year'] == latest_year]

            for _, row in latest_data.iterrows():
                country_code = row['country_code']
                tax_revenue = row.get('tax_revenue_pct_gdp', 0)

                # Calculate progressivity based on tax level and country classification
                income_group = self.classify_income_group(country_code)

                # Progressivity scoring factors
                if income_group == 'high_income':
                    # High-income countries generally have more progressive systems
                    base_progressivity = 0.7
                    if tax_revenue > 25:  # High tax Nordic countries
                        progressivity_score = 0.9
                    elif tax_revenue > 20:  # Continental European
                        progressivity_score = 0.8
                    elif tax_revenue > 15:  # Anglo-Saxon
                        progressivity_score = 0.7
                    else:  # Low-tax high-income
                        progressivity_score = 0.6
                elif income_group == 'upper_middle':
                    # Middle-income countries vary significantly
                    base_progressivity = 0.5
                    if tax_revenue > 20:  # Higher tax middle-income
                        progressivity_score = 0.7
                    elif tax_revenue > 15:
                        progressivity_score = 0.6
                    else:
                        progressivity_score = 0.5
                else:
                    # Lower-income countries generally have less progressive systems
                    base_progressivity = 0.3
                    progressivity_score = min(0.4, tax_revenue / 50)

                # Development pattern adjustments
                development_pattern = self.classify_development_pattern(country_code)
                pattern_adjustments = {
                    'nordic': 0.2,           # Most progressive
                    'continental_european': 0.15,
                    'anglo_saxon': 0.0,     # Baseline
                    'mediterranean': -0.05,
                    'east_asian': 0.1,
                    'latin_american': -0.1,
                    'african_developing': -0.15,
                    'emerging_asian': 0.05
                }

                pattern_adj = pattern_adjustments.get(development_pattern, 0)
                final_score = max(0, min(1.0, progressivity_score + pattern_adj))

                progressivity_data.append({
                    'country_code': country_code,
                    'country_name': row.get('country_name', country_code),
                    'year': latest_year,
                    'tax_revenue_pct_gdp': tax_revenue,
                    'income_group': income_group,
                    'development_pattern': development_pattern,
                    'progressivity_score': final_score,
                    'progressivity_ranking': self.get_progressivity_ranking(final_score)
                })

        progressivity_df = pd.DataFrame(progressivity_data)
        progressivity_df = progressivity_df.sort_values('progressivity_score', ascending=False).reset_index(drop=True)

        logger.info(f"✅ Created progressivity index for {len(progressivity_df)} countries")
        return progressivity_df

    def get_progressivity_ranking(self, score: float) -> str:
        """Convert progressivity score to ranking"""
        if score >= 0.8:
            return "Very Progressive"
        elif score >= 0.6:
            return "Progressive"
        elif score >= 0.4:
            return "Moderately Progressive"
        elif score >= 0.2:
            return "Slightly Progressive"
        else:
            return "Not Progressive"

    def create_fiscal_sustainability_index(self, data_sources: Dict) -> pd.DataFrame:
        """Create fiscal sustainability index"""
        logger.info("Creating fiscal sustainability index...")

        sustainability_data = []

        if 'fiscal_balances' in data_sources:
            balance_df = data_sources['fiscal_balances']
            latest_year = balance_df['year'].max() if 'year' in balance_df.columns else 2023

            latest_data = balance_df[balance_df['year'] == latest_year]

            for _, row in latest_data.iterrows():
                country_code = row['country_code']
                deficit = row.get('deficit_pct_gdp', 0)
                debt = row.get('debt_pct_gdp', 0)
                revenue = row.get('revenue_pct_gdp', 0)
                sustainability_score_raw = row.get('sustainability_score', 50)

                # Create enhanced sustainability scoring
                score = 100.0

                # Deficit penalties
                if deficit < -6:  # Critical deficit
                    score -= 40
                elif deficit < -3:  # Warning level
                    score -= 20
                elif deficit < 0:  # Mild deficit
                    score -= 10
                elif deficit > 2:  # Surplus
                    score += 10

                # Debt penalties
                if debt > 90:  # Critical debt
                    score -= 30
                elif debt > 60:  # Warning level
                    score -= 15
                elif debt > 30:  # Moderate debt
                    score -= 5

                # Revenue adequacy
                if revenue < 10:  # Very low revenue
                    score -= 20
                elif revenue < 15:  # Low revenue
                    score -= 10

                # Adjust for income group (lower-income countries get more leniency)
                income_group = self.classify_income_group(country_code)
                income_adjustments = {
                    'high_income': 0,
                    'upper_middle': 5,
                    'lower_middle': 10,
                    'low_income': 15
                }
                score += income_adjustments.get(income_group, 0)

                # Normalize to 0-100 scale
                final_score = max(0, min(100, score))

                # Determine sustainability status
                if final_score >= 80:
                    status = "Excellent"
                elif final_score >= 60:
                    status = "Good"
                elif final_score >= 40:
                    status = "Fair"
                elif final_score >= 20:
                    status = "Poor"
                else:
                    status = "Critical"

                sustainability_data.append({
                    'country_code': country_code,
                    'country_name': row.get('country_name', country_code),
                    'year': latest_year,
                    'deficit_pct_gdp': deficit,
                    'debt_pct_gdp': debt,
                    'revenue_pct_gdp': revenue,
                    'sustainability_score': final_score,
                    'sustainability_status': status,
                    'income_group': income_group,
                    'risk_factors': self.identify_risk_factors(deficit, debt, revenue)
                })

        sustainability_df = pd.DataFrame(sustainability_data)
        sustainability_df = sustainability_df.sort_values('sustainability_score', ascending=False).reset_index(drop=True)

        logger.info(f"✅ Created sustainability index for {len(sustainability_df)} countries")
        return sustainability_df

    def identify_risk_factors(self, deficit: float, debt: float, revenue: float) -> List[str]:
        """Identify fiscal risk factors"""
        risks = []

        if deficit < -6:
            risks.append("Critical deficit")
        elif deficit < -3:
            risks.append("High deficit")

        if debt > 90:
            risks.append("Critical debt level")
        elif debt > 60:
            risks.append("High debt level")

        if revenue < 10:
            risks.append("Very low revenue base")
        elif revenue < 15:
            risks.append("Low revenue base")

        if deficit < -3 and debt > 60:
            risks.append("Debt-deficit spiral risk")

        return risks if risks else ["Low risk"]

    def create_development_pattern_analysis(self, data_sources: Dict) -> pd.DataFrame:
        """Analyze fiscal patterns by development group"""
        logger.info("Creating development pattern analysis...")

        pattern_data = []

        # Combine available data
        all_data = []

        if 'worldbank_tax' in data_sources:
            tax_df = data_sources['worldbank_tax']
            all_data.append(tax_df)

        if 'fiscal_balances' in data_sources:
            balance_df = data_sources['fiscal_balances']
            all_data.append(balance_df)

        if all_data:
            # Merge data sources
            combined_df = pd.concat(all_data, ignore_index=True, sort=False)
            latest_year = combined_df['year'].max() if 'year' in combined_df.columns else 2023
            latest_data = combined_df[combined_df['year'] == latest_year]

            # Group by development pattern
            for pattern, countries in self.development_patterns.items():
                pattern_countries = [c for c in countries if c in latest_data['country_code'].values]

                if not pattern_countries:
                    continue

                pattern_subset = latest_data[latest_data['country_code'].isin(pattern_countries)]

                # Calculate pattern averages
                avg_tax_revenue = pattern_subset.get('tax_revenue_pct_gdp', pd.Series([0])).mean()
                avg_deficit = pattern_subset.get('deficit_pct_gdp', pd.Series([0])).mean()
                avg_debt = pattern_subset.get('debt_pct_gdp', pd.Series([0])).mean()
                avg_sustainability = pattern_subset.get('sustainability_score', pd.Series([50])).mean()

                pattern_data.append({
                    'development_pattern': pattern,
                    'num_countries': len(pattern_countries),
                    'avg_tax_revenue_pct_gdp': avg_tax_revenue,
                    'avg_deficit_pct_gdp': avg_deficit,
                    'avg_debt_pct_gdp': avg_debt,
                    'avg_sustainability_score': avg_sustainability,
                    'representative_countries': pattern_subset['country_name'].head(3).tolist() if len(pattern_subset) > 0 else [],
                    'pattern_characteristics': self.describe_pattern_characteristics(pattern, avg_tax_revenue, avg_deficit)
                })

        pattern_df = pd.DataFrame(pattern_data)
        logger.info(f"✅ Created development pattern analysis for {len(pattern_df)} patterns")
        return pattern_df

    def describe_pattern_characteristics(self, pattern: str, avg_tax: float, avg_deficit: float) -> str:
        """Describe characteristics of each development pattern"""
        characteristics = {
            'nordic': 'High tax, comprehensive welfare, generally sustainable',
            'continental_european': 'High tax, social market economy, moderate deficits',
            'anglo_saxon': 'Moderate tax, market-oriented, fiscal discipline',
            'mediterranean': 'High tax, fiscal challenges, debt concerns',
            'east_asian': 'Moderate tax, export-oriented, fiscal prudence',
            'emerging_asian': 'Developing tax systems, growth focus',
            'latin_american': 'Moderate tax, historical instability, improving',
            'african_developing': 'Low tax, development challenges, external aid',
            'transition_economies': 'Transitioning systems, varying performance'
        }

        return characteristics.get(pattern, 'Unique fiscal characteristics')

    def classify_income_group(self, country_code: str) -> str:
        """Classify country by income group"""
        for group, countries in self.income_groups.items():
            if country_code in countries:
                return group
        return 'unknown'

    def classify_development_pattern(self, country_code: str) -> str:
        """Classify country by development pattern"""
        for pattern, countries in self.development_patterns.items():
            if country_code in countries:
                return pattern
        return 'other'

    def create_comprehensive_rankings(self, progressivity_df: pd.DataFrame,
                                    sustainability_df: pd.DataFrame,
                                    pattern_df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive country rankings"""
        logger.info("Creating comprehensive country rankings...")

        # Merge rankings
        rankings_data = []

        if len(progressivity_df) > 0 and len(sustainability_df) > 0:
            merged_df = progressivity_df.merge(
                sustainability_df[['country_code', 'sustainability_score', 'sustainability_status']],
                on='country_code',
                how='inner'
            )

            # Calculate composite score
            merged_df['composite_score'] = (
                merged_df['progressivity_score'] * 0.4 +
                merged_df['sustainability_score'] * 0.6
            )

            # Add rankings
            merged_df['progressivity_rank'] = merged_df['progressivity_score'].rank(ascending=False)
            merged_df['sustainability_rank'] = merged_df['sustainability_score'].rank(ascending=False)
            merged_df['composite_rank'] = merged_df['composite_score'].rank(ascending=False)

            # Categorize overall performance
            merged_df['overall_performance'] = merged_df.apply(self.categorize_performance, axis=1)

            rankings_data = merged_df

        if len(rankings_data) > 0:
            rankings_df = pd.DataFrame(rankings_data)
            rankings_df = rankings_df.sort_values('composite_rank').reset_index(drop=True)
            logger.info(f"✅ Created comprehensive rankings for {len(rankings_df)} countries")
            return rankings_df
        else:
            logger.warning("Insufficient data for comprehensive rankings")
            return pd.DataFrame()

    def categorize_performance(self, row) -> str:
        """Categorize overall fiscal performance"""
        prog_score = row.get('progressivity_score', 0)
        sust_score = row.get('sustainability_score', 0)

        if prog_score >= 0.7 and sust_score >= 70:
            return "Excellent"
        elif prog_score >= 0.5 and sust_score >= 50:
            return "Good"
        elif prog_score >= 0.3 and sust_score >= 30:
            return "Fair"
        else:
            return "Needs Improvement"

    def generate_insights_and_recommendations(self, progressivity_df: pd.DataFrame,
                                             sustainability_df: pd.DataFrame,
                                             pattern_df: pd.DataFrame,
                                             rankings_df: pd.DataFrame) -> Dict:
        """Generate insights and policy recommendations"""
        logger.info("Generating insights and recommendations...")

        insights = {
            'key_findings': [],
            'regional_patterns': {},
            'policy_recommendations': {},
            'comparative_advantages': {},
            'risk_analysis': {},
            'reform_opportunities': []
        }

        # Key findings
        if len(rankings_df) > 0:
            top_performers = rankings_df.head(5)['country_name'].tolist()
            bottom_performers = rankings_df.tail(5)['country_name'].tolist()

            insights['key_findings'] = [
                f"Top performing countries: {', '.join(top_performers)}",
                f"Countries needing reform: {', '.join(bottom_performers)}",
                f"Average progressivity score: {progressivity_df['progressivity_score'].mean():.2f}",
                f"Average sustainability score: {sustainability_df['sustainability_score'].mean():.1f}"
            ]

        # Regional patterns
        if len(pattern_df) > 0:
            for _, row in pattern_df.iterrows():
                insights['regional_patterns'][row['development_pattern']] = {
                    'characteristics': row['pattern_characteristics'],
                    'avg_tax_revenue': row['avg_tax_revenue_pct_gdp'],
                    'fiscal_status': 'Strong' if row['avg_sustainability_score'] > 60 else 'Challenged'
                }

        # Policy recommendations
        insights['policy_recommendations'] = {
            'high_tax_low_sustainability': 'Focus on expenditure efficiency and debt reduction',
            'low_tax_high_sustainability': 'Consider strategic revenue increases for public investment',
            'balanced_approach': 'Maintain current balance while improving efficiency',
            'critical_situations': 'Comprehensive fiscal reform required'
        }

        # Risk analysis
        critical_countries = sustainability_df[sustainability_df['sustainability_status'] == 'Critical']
        if len(critical_countries) > 0:
            insights['risk_analysis']['critical_countries'] = critical_countries['country_name'].tolist()

        # Reform opportunities
        insights['reform_opportunities'] = [
            'Progressive tax structure optimization',
            'Expenditure efficiency improvements',
            'Debt sustainability strategies',
            'International best practice adoption'
        ]

        return insights

    def save_comprehensive_analysis(self, progressivity_df: pd.DataFrame,
                                  sustainability_df: pd.DataFrame,
                                  pattern_df: pd.DataFrame,
                                  rankings_df: pd.DataFrame,
                                  insights: Dict):
        """Save all analysis results"""
        logger.info("Saving comprehensive cross-country analysis...")

        # Save individual analyses
        progressivity_file = self.comparisons_dir / "tax_progressivity_index.xlsx"
        write_single_sheet_excel(progressivity_df, progressivity_file)

        sustainability_file = self.comparisons_dir / "fiscal_sustainability_index.xlsx"
        write_single_sheet_excel(sustainability_df, sustainability_file)

        pattern_file = self.comparisons_dir / "development_pattern_analysis.xlsx"
        write_single_sheet_excel(pattern_df, pattern_file)

        rankings_file = self.comparisons_dir / "comprehensive_fiscal_rankings.xlsx"
        write_single_sheet_excel(rankings_df, rankings_file)

        # Save insights
        insights_file = self.comparisons_dir / "cross_country_insights.json"
        with open(insights_file, 'w', encoding='utf-8') as f:
            json.dump(insights, f, indent=2)

        # Create summary report
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'countries_analyzed': len(rankings_df) if len(rankings_df) > 0 else 0,
            'development_patterns': len(pattern_df) if len(pattern_df) > 0 else 0,
            'key_metrics': {
                'avg_progressivity': progressivity_df['progressivity_score'].mean() if len(progressivity_df) > 0 else 0,
                'avg_sustainability': sustainability_df['sustainability_score'].mean() if len(sustainability_df) > 0 else 0
            },
            'data_sources_used': ['World Bank Tax Data', 'Fiscal Balances Data', 'WID Inequality Data'],
            'analysis_scope': 'Global fiscal comparison with focus on progressivity and sustainability'
        }

        summary_file = self.comparisons_dir / "analysis_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"✅ Cross-country analysis saved to {self.comparisons_dir}")
        logger.info(f"Progressivity index: {len(progressivity_df)} countries")
        logger.info(f"Sustainability index: {len(sustainability_df)} countries")
        logger.info(f"Comprehensive rankings: {len(rankings_df)} countries")

    def run_comprehensive_analysis(self):
        """Run complete cross-country comparison analysis"""
        logger.info("🚀 Starting comprehensive cross-country analysis...")

        # Load data
        data_sources = self.load_all_data_sources()

        if len(data_sources) == 0:
            logger.error("No data sources available for analysis")
            return None

        # Create analyses
        progressivity_df = self.create_tax_progressivity_index(data_sources)
        sustainability_df = self.create_fiscal_sustainability_index(data_sources)
        pattern_df = self.create_development_pattern_analysis(data_sources)
        rankings_df = self.create_comprehensive_rankings(progressivity_df, sustainability_df, pattern_df)

        # Generate insights
        insights = self.generate_insights_and_recommendations(
            progressivity_df, sustainability_df, pattern_df, rankings_df
        )

        # Save results
        self.save_comprehensive_analysis(
            progressivity_df, sustainability_df, pattern_df, rankings_df, insights
        )

        logger.info("✅ Cross-country analysis complete!")

        return {
            'progressivity_index': progressivity_df,
            'sustainability_index': sustainability_df,
            'development_patterns': pattern_df,
            'comprehensive_rankings': rankings_df,
            'insights': insights
        }

def main():
    """Main execution function"""
    # File paths
    base_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir = base_dir

    # Create comparator
    comparator = CrossCountryComparator(base_dir, output_dir)

    # Run analysis
    results = comparator.run_comprehensive_analysis()

    if results:
        logger.info("✅ Cross-country comparison analysis completed successfully")
    else:
        logger.error("❌ Cross-country comparison analysis failed")

    return results

if __name__ == "__main__":
    results = main()