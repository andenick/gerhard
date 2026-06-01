#!/usr/bin/env python3
"""
Fiscal Balance Calculator
Calculates revenue - expenditure = deficit/surplus for 161 countries
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

class FiscalBalanceCalculator:
    """Calculates fiscal balances and sustainability metrics"""

    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.results_dir = self.output_dir / "analysis" / "fiscal_balances"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Data sources
        self.worldbank_data = self.data_dir / "processed" / "worldbank_expenditure_master.xlsx"
        self.tax_revenue_data = self.data_dir / "Output/Data" / "world_bank_tax_revenue.xlsx"
        self.imf_gfs_data = self.data_dir / "processed" / "imf_gfs_master_dataset.xlsx"

        # Key fiscal indicators
        self.fiscal_indicators = {
            'revenue': {
                'sources': ['Tax revenue (% of GDP)', 'Total revenue (% of GDP)'],
                'weight': 1.0,
                'description': 'General government revenue as percentage of GDP'
            },
            'expenditure': {
                'sources': ['Government expenditure (% of GDP)', 'Total expenditure (% of GDP)'],
                'weight': 1.0,
                'description': 'General government expenditure as percentage of GDP'
            },
            'deficit': {
                'sources': ['Net lending/borrowing (% of GDP)'],
                'weight': 1.0,
                'description': 'Fiscal balance (positive = surplus, negative = deficit)'
            },
            'debt': {
                'sources': ['Central government debt, total (% of GDP)'],
                'weight': 1.0,
                'description': 'Central government debt as percentage of GDP'
            }
        }

        # Sustainability thresholds
        self.sustainability_thresholds = {
            'deficit_warning': -3.0,  # EU Maastricht criteria
            'deficit_critical': -6.0,
            'debt_warning': 60.0,    # EU Maastricht criteria
            'debt_critical': 90.0,
            'revenue_min': 15.0,     # Minimum revenue for functioning state
            'expenditure_max': 40.0  # Maximum sustainable expenditure
        }

        # Country classification
        self.income_groups = {
            'high_income': ['US', 'JP', 'DE', 'FR', 'GB', 'IT', 'CA', 'AU', 'CH', 'NO', 'SE', 'DK', 'NL', 'BE', 'AT', 'FI', 'IE', 'NZ', 'SG', 'KR'],
            'upper_middle': ['CN', 'BR', 'RU', 'MX', 'IN', 'ID', 'TR', 'SA', 'ZA', 'AR', 'CL', 'CO', 'PE', 'MY', 'TH', 'PH', 'PL', 'CZ', 'HU'],
            'lower_middle': ['EG', 'NG', 'KE', 'GH', 'BD', 'PK', 'VN', 'UA', 'RO', 'BG'],
            'low_income': ['AF', 'HT', 'ET', 'UG', 'TZ', 'MOZ', 'ZM', 'ZW']
        }

    def load_worldbank_expenditure_data(self) -> pd.DataFrame:
        """Load World Bank government expenditure data"""
        logger.info("Loading World Bank expenditure data...")

        if not self.worldbank_data.exists():
            logger.warning(f"World Bank expenditure data not found: {self.worldbank_data}")
            return pd.DataFrame()

        try:
            df = pd.read_excel(self.worldbank_data)
            logger.info(f"✅ Loaded World Bank expenditure data: {len(df)} observations")
            return df
        except Exception as e:
            logger.error(f"Error loading World Bank expenditure data: {e}")
            return pd.DataFrame()

    def load_tax_revenue_data(self) -> pd.DataFrame:
        """Load tax revenue data"""
        logger.info("Loading tax revenue data...")

        if not self.tax_revenue_data.exists():
            logger.warning(f"Tax revenue data not found: {self.tax_revenue_data}")
            return pd.DataFrame()

        try:
            df = pd.read_excel(self.tax_revenue_data)
            logger.info(f"✅ Loaded tax revenue data: {len(df)} observations")
            return df
        except Exception as e:
            logger.error(f"Error loading tax revenue data: {e}")
            return pd.DataFrame()

    def load_imf_gfs_data(self) -> pd.DataFrame:
        """Load IMF GFS data if available"""
        logger.info("Loading IMF GFS data...")

        if not self.imf_gfs_data.exists():
            logger.info("IMF GFS data not available")
            return pd.DataFrame()

        try:
            df = pd.read_excel(self.imf_gfs_data)
            logger.info(f"✅ Loaded IMF GFS data: {len(df)} observations")
            return df
        except Exception as e:
            logger.error(f"Error loading IMF GFS data: {e}")
            return pd.DataFrame()

    def merge_data_sources(self) -> pd.DataFrame:
        """Merge data from multiple sources"""
        logger.info("Merging data sources...")

        # Load all data sources
        wb_exp_df = self.load_worldbank_expenditure_data()
        tax_rev_df = self.load_tax_revenue_data()
        imf_df = self.load_imf_gfs_data()

        all_data = []

        # Process World Bank expenditure data
        if len(wb_exp_df) > 0:
            # Standardize column names
            wb_exp_standardized = self.standardize_worldbank_columns(wb_exp_df, 'expenditure')
            all_data.append(wb_exp_standardized)

        # Process tax revenue data
        if len(tax_rev_df) > 0:
            tax_rev_standardized = self.standardize_worldbank_columns(tax_rev_df, 'revenue')
            all_data.append(tax_rev_standardized)

        # Process IMF data
        if len(imf_df) > 0:
            imf_standardized = self.standardize_imf_columns(imf_df)
            all_data.append(imf_standardized)

        if not all_data:
            logger.warning("No data available from any source")
            return pd.DataFrame()

        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True, sort=False)
        logger.info(f"✅ Combined data: {len(combined_df)} observations")

        return combined_df

    def standardize_worldbank_columns(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Standardize World Bank data column names"""
        standardized = df.copy()

        # Common column mappings
        column_mappings = {
            'Country Code': 'country_code',
            'Country Name': 'country_name',
            'Year': 'year',
            'Indicator Name': 'indicator_name',
            'Value': 'value'
        }

        # Apply column mappings
        for old_name, new_name in column_mappings.items():
            if old_name in standardized.columns:
                standardized[new_name] = standardized[old_name]

        # Add data source
        standardized['data_source'] = 'World Bank'
        standardized['data_type'] = data_type

        # Ensure required columns exist
        required_cols = ['country_code', 'country_name', 'year', 'value']
        for col in required_cols:
            if col not in standardized.columns:
                logger.warning(f"Missing required column: {col}")
                return pd.DataFrame()

        # Clean data
        standardized = standardized.dropna(subset=required_cols)
        standardized['year'] = pd.to_numeric(standardized['year'], errors='coerce')
        standardized['value'] = pd.to_numeric(standardized['value'], errors='coerce')

        return standardized[required_cols + ['data_source', 'data_type']]

    def standardize_imf_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize IMF GFS data column names"""
        standardized = df.copy()

        # IMF-specific column mappings
        column_mappings = {
            'country_code': 'country_code',
            'country_name': 'country_name',
            'year': 'year',
            'value': 'value',
            'category': 'indicator_name'
        }

        # Apply mappings
        for old_name, new_name in column_mappings.items():
            if old_name in standardized.columns:
                standardized[new_name] = standardized[old_name]

        # Add data source
        standardized['data_source'] = 'IMF'

        # Categorize data type
        if 'category' in standardized.columns:
            standardized['data_type'] = standardized['category'].map({
                'REVENUE': 'revenue',
                'EXPENDITURE': 'expenditure',
                'DEFICIT': 'deficit'
            })

        # Ensure required columns
        required_cols = ['country_code', 'country_name', 'year', 'value']
        for col in required_cols:
            if col not in standardized.columns:
                logger.warning(f"Missing required column: {col}")
                return pd.DataFrame()

        # Clean data
        standardized = standardized.dropna(subset=required_cols)
        standardized['year'] = pd.to_numeric(standardized['year'], errors='coerce')
        standardized['value'] = pd.to_numeric(standardized['value'], errors='coerce')

        return standardized[required_cols + ['data_source', 'data_type', 'indicator_name']]

    def calculate_fiscal_balances(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate fiscal balances for all countries"""
        logger.info("Calculating fiscal balances...")

        if len(df) == 0:
            return pd.DataFrame()

        # Pivot data to have indicators as columns
        pivot_df = df.pivot_table(
            index=['country_code', 'country_name', 'year'],
            columns='indicator_name',
            values='value',
            aggfunc='mean'  # Average if multiple sources
        ).reset_index()

        logger.info(f"Pivoted data shape: {pivot_df.shape}")

        # Calculate derived indicators
        results = []

        for _, row in pivot_df.iterrows():
            country_code = row['country_code']
            country_name = row['country_name']
            year = row['year']

            # Extract revenue and expenditure values
            revenue = self.extract_indicator_value(row, 'revenue')
            expenditure = self.extract_indicator_value(row, 'expenditure')
            deficit = self.extract_indicator_value(row, 'deficit')
            debt = self.extract_indicator_value(row, 'debt')

            # Calculate fiscal balance if not directly available
            calculated_deficit = None
            if revenue is not None and expenditure is not None:
                calculated_deficit = revenue - expenditure

            # Use actual deficit if available, otherwise calculated
            final_deficit = deficit if deficit is not None else calculated_deficit

            # Determine sustainability indicators
            sustainability = self.assess_sustainability(
                revenue, expenditure, final_deficit, debt
            )

            # Classify income group
            income_group = self.classify_income_group(country_code)

            result = {
                'country_code': country_code,
                'country_name': country_name,
                'year': year,
                'income_group': income_group,
                'revenue_pct_gdp': revenue,
                'expenditure_pct_gdp': expenditure,
                'deficit_pct_gdp': final_deficit,
                'debt_pct_gdp': debt,
                'calculated_deficit': calculated_deficit,
                'primary_balance_pct_gdp': self.calculate_primary_balance(revenue, expenditure, debt),
                **sustainability
            }

            results.append(result)

        results_df = pd.DataFrame(results)
        logger.info(f"✅ Calculated balances for {len(results_df)} country-year observations")

        return results_df

    def extract_indicator_value(self, row: pd.Series, indicator_type: str) -> Optional[float]:
        """Extract indicator value from row using multiple possible column names"""
        possible_names = self.fiscal_indicators[indicator_type]['sources']

        for name in possible_names:
            if name in row and pd.notna(row[name]):
                return float(row[name])

        return None

    def calculate_primary_balance(self, revenue: Optional[float], expenditure: Optional[float],
                                 debt: Optional[float]) -> Optional[float]:
        """Calculate primary balance (revenue - non-interest expenditure)"""
        if revenue is None or expenditure is None:
            return None

        # Estimate interest payments (rough approximation: 5% of debt)
        interest_payments = debt * 0.05 if debt is not None else 0

        primary_balance = revenue - (expenditure - interest_payments)
        return primary_balance

    def assess_sustainability(self, revenue: Optional[float], expenditure: Optional[float],
                            deficit: Optional[float], debt: Optional[float]) -> Dict:
        """Assess fiscal sustainability"""
        sustainability = {
            'deficit_status': 'unknown',
            'debt_status': 'unknown',
            'overall_sustainability': 'unknown',
            'sustainability_score': 0.0,
            'warnings': []
        }

        # Assess deficit
        if deficit is not None:
            if deficit <= self.sustainability_thresholds['deficit_critical']:
                sustainability['deficit_status'] = 'critical'
                sustainability['warnings'].append('Critical deficit level')
            elif deficit <= self.sustainability_thresholds['deficit_warning']:
                sustainability['deficit_status'] = 'warning'
                sustainability['warnings'].append('High deficit level')
            elif deficit >= 0:
                sustainability['deficit_status'] = 'surplus'
            else:
                sustainability['deficit_status'] = 'sustainable'

        # Assess debt
        if debt is not None:
            if debt >= self.sustainability_thresholds['debt_critical']:
                sustainability['debt_status'] = 'critical'
                sustainability['warnings'].append('Critical debt level')
            elif debt >= self.sustainability_thresholds['debt_warning']:
                sustainability['debt_status'] = 'warning'
                sustainability['warnings'].append('High debt level')
            elif debt < 30:
                sustainability['debt_status'] = 'low'
            else:
                sustainability['debt_status'] = 'sustainable'

        # Calculate overall sustainability score
        score = 100.0

        if deficit is not None and deficit < 0:
            score -= abs(deficit) * 10  # Penalize deficits

        if debt is not None:
            if debt > 60:
                score -= (debt - 60) * 2  # Penalize high debt

        if revenue is not None and revenue < self.sustainability_thresholds['revenue_min']:
            score -= (self.sustainability_thresholds['revenue_min'] - revenue) * 5
            sustainability['warnings'].append('Low revenue base')

        sustainability['sustainability_score'] = max(0, min(100, score))

        # Overall sustainability
        if sustainability['deficit_status'] == 'critical' or sustainability['debt_status'] == 'critical':
            sustainability['overall_sustainability'] = 'critical'
        elif 'warning' in [sustainability['deficit_status'], sustainability['debt_status']]:
            sustainability['overall_sustainability'] = 'warning'
        elif sustainability['deficit_status'] == 'surplus':
            sustainability['overall_sustainability'] = 'excellent'
        else:
            sustainability['overall_sustainability'] = 'sustainable'

        return sustainability

    def classify_income_group(self, country_code: str) -> str:
        """Classify country by income group"""
        for group, countries in self.income_groups.items():
            if country_code in countries:
                return group
        return 'unknown'

    def create_country_trends(self, df: pd.DataFrame) -> Dict:
        """Create fiscal trend analysis for each country"""
        logger.info("Creating country trend analysis...")

        trends = {}

        for country_code in df['country_code'].unique():
            country_data = df[df['country_code'] == country_code].sort_values('year')

            if len(country_data) < 2:
                continue

            country_name = country_data['country_name'].iloc[0]

            # Calculate trends
            trend_data = {
                'country_code': country_code,
                'country_name': country_name,
                'data_points': len(country_data),
                'year_range': {
                    'start': int(country_data['year'].min()),
                    'end': int(country_data['year'].max())
                },
                'trends': {}
            }

            # Revenue trend
            if 'revenue_pct_gdp' in country_data.columns:
                revenue_trend = self.calculate_trend(country_data, 'revenue_pct_gdp')
                trend_data['trends']['revenue'] = revenue_trend

            # Expenditure trend
            if 'expenditure_pct_gdp' in country_data.columns:
                expenditure_trend = self.calculate_trend(country_data, 'expenditure_pct_gdp')
                trend_data['trends']['expenditure'] = expenditure_trend

            # Deficit trend
            if 'deficit_pct_gdp' in country_data.columns:
                deficit_trend = self.calculate_trend(country_data, 'deficit_pct_gdp')
                trend_data['trends']['deficit'] = deficit_trend

            # Debt trend
            if 'debt_pct_gdp' in country_data.columns:
                debt_trend = self.calculate_trend(country_data, 'debt_pct_gdp')
                trend_data['trends']['debt'] = debt_trend

            # Latest sustainability status
            latest_data = country_data.iloc[-1]
            trend_data['latest_status'] = {
                'year': int(latest_data['year']),
                'sustainability_score': latest_data.get('sustainability_score', 0),
                'overall_sustainability': latest_data.get('overall_sustainability', 'unknown')
            }

            trends[country_code] = trend_data

        logger.info(f"✅ Created trends for {len(trends)} countries")
        return trends

    def calculate_trend(self, df: pd.DataFrame, column: str) -> Dict:
        """Calculate trend statistics for a variable"""
        if column not in df.columns or len(df) < 2:
            return {}

        data = df[column].dropna()
        if len(data) < 2:
            return {}

        # Linear regression to calculate trend
        x = np.arange(len(data))
        y = data.values

        # Calculate slope (trend per year)
        slope, intercept = np.polyfit(x, y, 1)

        # Calculate average annual change
        annual_change = slope

        # Calculate volatility
        volatility = y.std()

        # Calculate change over period
        total_change = y[-1] - y[0]

        trend_info = {
            'annual_change': float(annual_change),
            'total_change': float(total_change),
            'volatility': float(volatility),
            'start_value': float(y[0]),
            'end_value': float(y[-1]),
            'trend_direction': 'increasing' if annual_change > 0.01 else 'decreasing' if annual_change < -0.01 else 'stable'
        }

        return trend_info

    def save_results(self, df: pd.DataFrame, trends: Dict):
        """Save analysis results"""
        logger.info("Saving analysis results...")

        # Save main results
        results_file = self.results_dir / "fiscal_balances_master_dataset.xlsx"
        write_single_sheet_excel(df, results_file)

        results_csv = results_file.with_suffix('.csv')
        df.to_csv(results_csv, index=False)

        # Save trends
        trends_file = self.results_dir / "fiscal_trends_by_country.json"
        with open(trends_file, 'w', encoding='utf-8') as f:
            json.dump(trends, f, indent=2)

        # Create summary statistics
        summary_file = self.results_dir / "fiscal_balance_summary.json"
        summary = self.create_summary_statistics(df, trends)
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"✅ Results saved to {self.results_dir}")

    def create_summary_statistics(self, df: pd.DataFrame, trends: Dict) -> Dict:
        """Create summary statistics of fiscal balances"""
        summary = {
            'analysis_date': datetime.now().isoformat(),
            'total_observations': len(df),
            'countries_covered': df['country_code'].nunique(),
            'year_range': {
                'start': int(df['year'].min()),
                'end': int(df['year'].max())
            },
            'global_averages': {},
            'sustainability_distribution': {},
            'regional_analysis': {},
            'critical_countries': []
        }

        # Calculate global averages
        numeric_cols = ['revenue_pct_gdp', 'expenditure_pct_gdp', 'deficit_pct_gdp', 'debt_pct_gdp', 'sustainability_score']
        for col in numeric_cols:
            if col in df.columns:
                summary['global_averages'][col] = float(df[col].mean())

        # Sustainability distribution
        if 'overall_sustainability' in df.columns:
            sus_dist = df['overall_sustainability'].value_counts().to_dict()
            summary['sustainability_distribution'] = sus_dist

        # Find critical countries (latest year)
        latest_year = df['year'].max()
        latest_data = df[df['year'] == latest_year]

        critical_countries = latest_data[latest_data['overall_sustainability'] == 'critical']
        summary['critical_countries'] = critical_countries[['country_code', 'country_name', 'sustainability_score']].to_dict('records')

        # Income group analysis
        if 'income_group' in df.columns:
            income_analysis = df.groupby('income_group')['sustainability_score'].mean().to_dict()
            summary['income_group_analysis'] = income_analysis

        return summary

    def run_analysis(self):
        """Run complete fiscal balance analysis"""
        logger.info("🚀 Starting fiscal balance analysis...")

        # Merge data sources
        merged_df = self.merge_data_sources()

        if len(merged_df) == 0:
            logger.error("No data available for analysis")
            return None, None, None

        # Calculate fiscal balances
        balances_df = self.calculate_fiscal_balances(merged_df)

        if len(balances_df) == 0:
            logger.error("No fiscal balance calculations completed")
            return None, None, None

        # Create trends
        trends = self.create_country_trends(balances_df)

        # Save results
        self.save_results(balances_df, trends)

        logger.info("✅ Fiscal balance analysis complete!")
        logger.info(f"Analyzed {balances_df['country_code'].nunique()} countries")
        logger.info(f"Total observations: {len(balances_df)}")

        return balances_df, trends, self.create_summary_statistics(balances_df, trends)

def main():
    """Main execution function"""
    # File paths
    base_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir = base_dir

    # Create calculator
    calculator = FiscalBalanceCalculator(base_dir, output_dir)

    # Run analysis
    results = calculator.run_analysis()

    if results:
        balances_df, trends, summary = results
        logger.info("✅ Fiscal balance analysis completed successfully")
    else:
        logger.error("❌ Fiscal balance analysis failed")

    return results

if __name__ == "__main__":
    results = main()