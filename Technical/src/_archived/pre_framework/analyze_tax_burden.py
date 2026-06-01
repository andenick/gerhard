"""
Tax Burden Analysis Script
Comprehensive analysis of who pays taxes by income class internationally
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir

logger = setup_logging(__name__)

# Define paths
DATA_DIR = output_data_dir()
OUTPUT_DIR = output_data_dir()


class TaxBurdenAnalyzer:
    """Analyzes tax burden distribution across income classes"""

    def __init__(self):
        self.data = {}
        self.results = {}

    def load_all_data(self):
        """Load all available tax datasets"""
        logger.info("Loading all tax datasets...")

        datasets = {
            'us_percentile': 'us_tax_distribution_by_income_percentile.xlsx',
            'us_quintile': 'us_tax_distribution_by_income_quintile.xlsx',
            'us_tax_type': 'us_tax_burden_by_tax_type.xlsx',
            'us_historical': 'us_tax_distribution_historical_trends.xlsx',
            'world_bank': 'world_bank_tax_revenue.xlsx',
            'unified_intl': 'unified_international_tax_data.xlsx'
        }

        for name, filename in datasets.items():
            file_path = DATA_DIR / filename
            if file_path.exists():
                self.data[name] = pd.read_excel(file_path)
                logger.info(f"  Loaded {name}: {len(self.data[name])} records")
            else:
                logger.warning(f"  {name} not found at {file_path}")

        return self.data

    def analyze_us_tax_distribution(self) -> pd.DataFrame:
        """Analyze US tax distribution by income percentile"""
        logger.info("Analyzing US tax distribution...")

        if 'us_percentile' not in self.data:
            logger.warning("US percentile data not available")
            return None

        df = self.data['us_percentile'].copy()

        # Key findings
        findings = []

        # Who pays what share
        for _, row in df.iterrows():
            finding = {
                'income_group': row['income_percentile'],
                'agi_threshold': row['agi_threshold'],
                'share_of_taxes_paid': row['share_of_total_taxes_percent'],
                'share_of_income': row['share_of_total_agi_percent'],
                'average_tax_rate': row['average_tax_rate_percent'],
                'tax_share_vs_income_share_ratio': row['share_of_total_taxes_percent'] / row['share_of_total_agi_percent'] if row['share_of_total_agi_percent'] > 0 else 0
            }
            findings.append(finding)

        results_df = pd.DataFrame(findings)

        # Add analysis
        results_df['progressivity'] = results_df['tax_share_vs_income_share_ratio'].apply(
            lambda x: 'Progressive' if x > 1.0 else 'Regressive' if x < 1.0 else 'Neutral'
        )

        # Save results
        output_file = OUTPUT_DIR / "analysis_us_tax_burden_distribution.xlsx"
        results_df.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"US tax burden analysis saved to {output_file}")

        self.results['us_distribution'] = results_df
        return results_df

    def analyze_tax_progressivity(self) -> pd.DataFrame:
        """Analyze how progressive the US tax system is"""
        logger.info("Analyzing tax progressivity...")

        if 'us_quintile' not in self.data:
            logger.warning("US quintile data not available")
            return None

        df = self.data['us_quintile'].copy()

        # Calculate progressivity metrics
        progressivity = []

        for _, row in df.iterrows():
            metric = {
                'income_group': row['income_quintile'],
                'market_income_share': row['market_income_share_percent'],
                'after_tax_income_share': row['after_tax_income_share_percent'],
                'tax_share': row['federal_tax_share_percent'],
                'average_tax_rate': row['average_federal_tax_rate_percent'],
                'income_redistribution': row['after_tax_income_share_percent'] - row['market_income_share_percent'],
                'tax_burden_ratio': row['federal_tax_share_percent'] / row['market_income_share_percent'] if row['market_income_share_percent'] > 0 else 0
            }
            progressivity.append(metric)

        results_df = pd.DataFrame(progressivity)

        # Save results
        output_file = OUTPUT_DIR / "analysis_tax_progressivity.xlsx"
        results_df.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Tax progressivity analysis saved to {output_file}")

        self.results['progressivity'] = results_df
        return results_df

    def analyze_international_comparison(self) -> pd.DataFrame:
        """Compare tax revenue across countries by income level"""
        logger.info("Analyzing international tax comparisons...")

        if 'world_bank' not in self.data:
            logger.warning("World Bank data not available")
            return None

        df = self.data['world_bank'].copy()

        # Get most recent year for each country
        df_recent = df.sort_values('year').groupby('country_code').tail(1)

        # Calculate summary statistics
        summary = df_recent.groupby('country_code').agg({
            'country_name': 'first',
            'tax_revenue_pct_gdp': 'mean',
            'year': 'max'
        }).reset_index()

        summary = summary.sort_values('tax_revenue_pct_gdp', ascending=False)

        # Categorize countries
        summary['tax_level_category'] = pd.cut(
            summary['tax_revenue_pct_gdp'],
            bins=[0, 15, 20, 25, 30, 100],
            labels=['Very Low (<15%)', 'Low (15-20%)', 'Medium (20-25%)', 'High (25-30%)', 'Very High (>30%)']
        )

        # Save results
        output_file = OUTPUT_DIR / "analysis_international_tax_levels.xlsx"
        summary.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"International comparison saved to {output_file}")
        logger.info(f"  Countries analyzed: {len(summary)}")

        self.results['international'] = summary
        return summary

    def analyze_tax_by_type(self) -> pd.DataFrame:
        """Analyze what types of taxes different income groups pay"""
        logger.info("Analyzing tax burden by tax type...")

        if 'us_tax_type' not in self.data:
            logger.warning("US tax type data not available")
            return None

        df = self.data['us_tax_type'].copy()

        # Calculate shares
        results = df.copy()

        # Identify which tax type is largest for each group
        tax_cols = ['individual_income_tax_rate', 'payroll_tax_rate',
                    'corporate_income_tax_rate', 'excise_estate_other_tax_rate']

        results['largest_tax_type'] = results[tax_cols].idxmax(axis=1).str.replace('_rate', '')
        results['largest_tax_rate'] = results[tax_cols].max(axis=1)

        # Save results
        output_file = OUTPUT_DIR / "analysis_tax_burden_by_type.xlsx"
        results.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Tax type analysis saved to {output_file}")

        self.results['tax_type'] = results
        return results

    def create_summary_findings(self) -> pd.DataFrame:
        """Create high-level summary of key findings"""
        logger.info("Creating summary findings...")

        findings = []

        # US tax concentration
        if 'us_distribution' in self.results:
            df = self.results['us_distribution']
            top1 = df[df['income_group'] == 'Top 1%'].iloc[0]
            bottom50 = df[df['income_group'] == 'Bottom 50%'].iloc[0]

            findings.extend([
                {
                    'finding_category': 'Tax Concentration',
                    'metric': 'Top 1% share of taxes',
                    'value': f"{top1['share_of_taxes_paid']:.1f}%",
                    'context': f"despite earning {top1['share_of_income']:.1f}% of income"
                },
                {
                    'finding_category': 'Tax Concentration',
                    'metric': 'Bottom 50% share of taxes',
                    'value': f"{bottom50['share_of_taxes_paid']:.1f}%",
                    'context': f"while earning {bottom50['share_of_income']:.1f}% of income"
                }
            ])

        # Progressivity
        if 'progressivity' in self.results:
            df = self.results['progressivity']
            highest_q = df[df['income_group'] == 'Highest (5th) Quintile'].iloc[0]
            lowest_q = df[df['income_group'] == 'Lowest (1st) Quintile'].iloc[0]

            findings.append({
                'finding_category': 'Progressivity',
                'metric': 'Tax rate difference (highest vs lowest quintile)',
                'value': f"{highest_q['average_tax_rate'] - lowest_q['average_tax_rate']:.1f} percentage points",
                'context': f"{highest_q['average_tax_rate']:.1f}% vs {lowest_q['average_tax_rate']:.1f}%"
            })

        # International
        if 'international' in self.results:
            df = self.results['international']
            findings.extend([
                {
                    'finding_category': 'International',
                    'metric': 'Countries analyzed',
                    'value': str(len(df)),
                    'context': 'with tax revenue data'
                },
                {
                    'finding_category': 'International',
                    'metric': 'Median tax-to-GDP ratio',
                    'value': f"{df['tax_revenue_pct_gdp'].median():.1f}%",
                    'context': f"Range: {df['tax_revenue_pct_gdp'].min():.1f}% to {df['tax_revenue_pct_gdp'].max():.1f}%"
                }
            ])

        findings_df = pd.DataFrame(findings)

        # Save results
        output_file = OUTPUT_DIR / "analysis_summary_findings.xlsx"
        findings_df.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Summary findings saved to {output_file}")

        return findings_df

    def run_all_analyses(self):
        """Run all analyses"""
        logger.info("=" * 60)
        logger.info("Running Comprehensive Tax Burden Analysis")
        logger.info("=" * 60)

        # Load data
        self.load_all_data()

        # Run analyses
        self.analyze_us_tax_distribution()
        self.analyze_tax_progressivity()
        self.analyze_international_comparison()
        self.analyze_tax_by_type()
        findings = self.create_summary_findings()

        logger.info("\n" + "=" * 60)
        logger.info("Analysis Complete!")
        logger.info("=" * 60)
        logger.info(f"\nKey Findings:\n")
        if findings is not None:
            for _, row in findings.iterrows():
                logger.info(f"{row['finding_category']:20s} | {row['metric']}: {row['value']}")
                logger.info(f"{'':20s} | {row['context']}")
                logger.info("")

        logger.info(f"\nAll analysis files saved to: {OUTPUT_DIR}")

        return self.results


def main():
    """Main execution function"""
    logger.info("Tax Burden Analysis - Gerhard Project")

    analyzer = TaxBurdenAnalyzer()
    results = analyzer.run_all_analyses()

    logger.info("\n" + "=" * 60)
    logger.info("Next: Run visualization script to create charts")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
