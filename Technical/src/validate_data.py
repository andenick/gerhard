"""
Data Validation Script
Validates all tax data against known benchmarks and performs quality checks
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


class DataValidator:
    """Validates tax data for accuracy and consistency"""

    def __init__(self):
        self.validation_results = []
        self.data = {}

    def load_all_data(self):
        """Load all datasets for validation"""
        logger.info("Loading data for validation...")

        datasets = {
            'us_percentile': 'us_tax_distribution_by_income_percentile.xlsx',
            'us_quintile': 'us_tax_distribution_by_income_quintile.xlsx',
            'us_tax_type': 'us_tax_burden_by_tax_type.xlsx',
            'world_bank': 'world_bank_tax_revenue.xlsx',
        }

        for name, filename in datasets.items():
            file_path = DATA_DIR / filename
            if file_path.exists():
                self.data[name] = pd.read_excel(file_path)
                logger.info(f"  Loaded {name}: {len(self.data[name])} records")

    def validate_us_percentile_data(self) -> Dict:
        """Validate US percentile data against known benchmarks"""
        logger.info("Validating US percentile data...")

        df = self.data['us_percentile']
        validations = []

        # Check 1: Tax shares should sum to 100% (approximately)
        total_tax_share = df['share_of_total_taxes_percent'].sum()
        # Note: Our data has overlapping groups, so we check the top-level values
        top50_tax = df[df['income_percentile'] == 'Top 50%']['share_of_total_taxes_percent'].values[0]
        bottom50_tax = df[df['income_percentile'] == 'Bottom 50%']['share_of_total_taxes_percent'].values[0]

        check1_pass = abs((top50_tax + bottom50_tax) - 100.0) < 0.1
        validations.append({
            'check': 'Tax shares sum to 100%',
            'expected': 100.0,
            'actual': top50_tax + bottom50_tax,
            'pass': check1_pass,
            'notes': 'Top 50% + Bottom 50% should equal 100%'
        })

        # Check 2: Top 1% pays more than bottom 50% (known fact)
        top1_tax = df[df['income_percentile'] == 'Top 1%']['share_of_total_taxes_percent'].values[0]
        check2_pass = top1_tax > bottom50_tax
        validations.append({
            'check': 'Top 1% pays more than Bottom 50%',
            'expected': f'> {bottom50_tax}%',
            'actual': top1_tax,
            'pass': check2_pass,
            'notes': 'Top 1% should pay more in absolute share'
        })

        # Check 3: Average tax rates should increase with income (progressivity)
        rates = df['average_tax_rate_percent'].values
        # Check if generally increasing (allowing for some variation)
        check3_pass = rates[0] > rates[-1]  # Top 1% > Bottom 50%
        validations.append({
            'check': 'Tax rates are progressive',
            'expected': 'Increasing with income',
            'actual': f"Top 1%: {rates[0]}%, Bottom 50%: {rates[-1]}%",
            'pass': check3_pass,
            'notes': 'Higher income should have higher rates'
        })

        # Check 4: Top 1% threshold should be reasonable (IRS data shows ~$550k+)
        top1_threshold = df[df['income_percentile'] == 'Top 1%']['agi_threshold'].values[0]
        check4_pass = 500000 < top1_threshold < 700000
        validations.append({
            'check': 'Top 1% AGI threshold reasonable',
            'expected': '$500k-$700k',
            'actual': f'${top1_threshold:,.0f}',
            'pass': check4_pass,
            'notes': 'Based on IRS 2021 data'
        })

        # Check 5: Tax share should exceed income share for top earners
        top1_data = df[df['income_percentile'] == 'Top 1%'].iloc[0]
        ratio = top1_data['share_of_total_taxes_percent'] / top1_data['share_of_total_agi_percent']
        check5_pass = ratio > 1.0
        validations.append({
            'check': 'Top 1% pays more than proportional share',
            'expected': '> 1.0',
            'actual': f'{ratio:.2f}',
            'pass': check5_pass,
            'notes': 'Tax share / income share ratio > 1 indicates progressivity'
        })

        return {
            'dataset': 'US Percentile Data',
            'total_checks': len(validations),
            'passed': sum(1 for v in validations if v['pass']),
            'validations': validations
        }

    def validate_us_quintile_data(self) -> Dict:
        """Validate US quintile data"""
        logger.info("Validating US quintile data...")

        df = self.data['us_quintile']
        # Filter to just quintiles (not Top 10%, etc.)
        quintiles = df[df['income_quintile'].str.contains('Quintile')]

        validations = []

        # Check 1: Market income shares should sum to 100%
        income_sum = quintiles['market_income_share_percent'].sum()
        check1_pass = abs(income_sum - 100.0) < 0.1
        validations.append({
            'check': 'Market income shares sum to 100%',
            'expected': 100.0,
            'actual': income_sum,
            'pass': check1_pass,
            'notes': 'All quintiles should account for all income'
        })

        # Check 2: Tax shares should sum to 100%
        tax_sum = quintiles['federal_tax_share_percent'].sum()
        check2_pass = abs(tax_sum - 100.0) < 0.1
        validations.append({
            'check': 'Federal tax shares sum to 100%',
            'expected': 100.0,
            'actual': tax_sum,
            'pass': check2_pass,
            'notes': 'All quintiles should account for all taxes'
        })

        # Check 3: After-tax income shares should sum to 100%
        after_tax_sum = quintiles['after_tax_income_share_percent'].sum()
        check3_pass = abs(after_tax_sum - 100.0) < 0.1
        validations.append({
            'check': 'After-tax income shares sum to 100%',
            'expected': 100.0,
            'actual': after_tax_sum,
            'pass': check3_pass,
            'notes': 'Distribution after taxes should be complete'
        })

        # Check 4: Tax rates should be monotonically increasing (progressive)
        rates = quintiles['average_federal_tax_rate_percent'].values
        check4_pass = all(rates[i] < rates[i+1] for i in range(len(rates)-1))
        validations.append({
            'check': 'Tax rates increase with each quintile',
            'expected': 'Monotonic increase',
            'actual': f"Range: {rates[0]:.1f}% to {rates[-1]:.1f}%",
            'pass': check4_pass,
            'notes': 'Progressive tax system'
        })

        # Check 5: Highest quintile should pay majority of taxes
        highest_quintile = quintiles[quintiles['income_quintile'] == 'Highest (5th) Quintile']
        highest_tax_share = highest_quintile['federal_tax_share_percent'].values[0]
        check5_pass = highest_tax_share > 50.0
        validations.append({
            'check': 'Highest quintile pays majority of taxes',
            'expected': '> 50%',
            'actual': f'{highest_tax_share:.1f}%',
            'pass': check5_pass,
            'notes': 'Top 20% should pay more than half of taxes'
        })

        return {
            'dataset': 'US Quintile Data',
            'total_checks': len(validations),
            'passed': sum(1 for v in validations if v['pass']),
            'validations': validations
        }

    def validate_tax_type_data(self) -> Dict:
        """Validate tax type breakdown data"""
        logger.info("Validating tax type data...")

        df = self.data['us_tax_type']
        validations = []

        # Check 1: Total tax rate should equal sum of components
        tax_cols = ['individual_income_tax_rate', 'payroll_tax_rate',
                    'corporate_income_tax_rate', 'excise_estate_other_tax_rate']

        for idx, row in df.iterrows():
            component_sum = sum(row[col] for col in tax_cols)
            total = row['total_federal_tax_rate']
            diff = abs(component_sum - total)

            if diff > 0.5:  # Allow small rounding differences
                validations.append({
                    'check': f"Tax components sum correctly for {row['income_group']}",
                    'expected': total,
                    'actual': component_sum,
                    'pass': False,
                    'notes': f'Difference: {diff:.2f} percentage points'
                })

        # If no failures, add success
        if not validations:
            validations.append({
                'check': 'All tax components sum to total',
                'expected': 'Components = Total',
                'actual': 'All groups validated',
                'pass': True,
                'notes': 'Individual + Payroll + Corporate + Other = Total'
            })

        # Check 2: Payroll taxes should be higher for lower income (regressive)
        lowest = df[df['income_group'] == 'Lowest Quintile']['payroll_tax_rate'].values[0]
        highest = df[df['income_group'] == 'Top 1%']['payroll_tax_rate'].values[0]
        check2_pass = lowest > highest
        validations.append({
            'check': 'Payroll taxes are regressive',
            'expected': 'Higher for low income',
            'actual': f'Lowest: {lowest:.1f}%, Top 1%: {highest:.1f}%',
            'pass': check2_pass,
            'notes': 'Payroll taxes cap at high incomes'
        })

        # Check 3: Income taxes should be higher for higher income (progressive)
        lowest_income_tax = df[df['income_group'] == 'Lowest Quintile']['individual_income_tax_rate'].values[0]
        highest_income_tax = df[df['income_group'] == 'Top 1%']['individual_income_tax_rate'].values[0]
        check3_pass = highest_income_tax > lowest_income_tax
        validations.append({
            'check': 'Income taxes are progressive',
            'expected': 'Higher for high income',
            'actual': f'Lowest: {lowest_income_tax:.1f}%, Top 1%: {highest_income_tax:.1f}%',
            'pass': check3_pass,
            'notes': 'Income tax rates increase with income'
        })

        return {
            'dataset': 'Tax Type Data',
            'total_checks': len(validations),
            'passed': sum(1 for v in validations if v['pass']),
            'validations': validations
        }

    def validate_international_data(self) -> Dict:
        """Validate international data"""
        logger.info("Validating international data...")

        df = self.data['world_bank']
        validations = []

        # Check 1: Tax-to-GDP ratios should be in reasonable range (0-60%)
        min_val = df['tax_revenue_pct_gdp'].min()
        max_val = df['tax_revenue_pct_gdp'].max()
        check1_pass = 0 <= min_val and max_val <= 60
        validations.append({
            'check': 'Tax-to-GDP ratios in reasonable range',
            'expected': '0-60%',
            'actual': f'{min_val:.1f}% to {max_val:.1f}%',
            'pass': check1_pass,
            'notes': 'Historical range for all countries'
        })

        # Check 2: Number of countries should be reasonable
        n_countries = df['country_code'].nunique()
        check2_pass = 150 < n_countries < 250
        validations.append({
            'check': 'Reasonable number of countries',
            'expected': '150-250',
            'actual': n_countries,
            'pass': check2_pass,
            'notes': 'World Bank covers ~200 countries'
        })

        # Check 3: Should have data for major economies
        major_economies = ['USA', 'CHN', 'JPN', 'DEU', 'GBR', 'FRA', 'IND', 'CAN']
        countries_in_data = df['country_code'].unique()
        major_present = [c for c in major_economies if c in countries_in_data]
        check3_pass = len(major_present) >= 6
        validations.append({
            'check': 'Data includes major economies',
            'expected': '6+ of 8',
            'actual': f'{len(major_present)} of 8 (USA, CHN, JPN, DEU, GBR, FRA, IND, CAN)',
            'pass': check3_pass,
            'notes': 'Major economies should be represented'
        })

        # Check 4: Should have recent data (2020+)
        max_year = df['year'].max()
        check4_pass = max_year >= 2020
        validations.append({
            'check': 'Recent data available',
            'expected': '>= 2020',
            'actual': int(max_year),
            'pass': check4_pass,
            'notes': 'Data should be recent'
        })

        # Check 5: No negative tax rates
        negative_count = (df['tax_revenue_pct_gdp'] < 0).sum()
        check5_pass = negative_count == 0
        validations.append({
            'check': 'No negative tax rates',
            'expected': '0',
            'actual': negative_count,
            'pass': check5_pass,
            'notes': 'Tax rates cannot be negative'
        })

        return {
            'dataset': 'International Data',
            'total_checks': len(validations),
            'passed': sum(1 for v in validations if v['pass']),
            'validations': validations
        }

    def generate_validation_report(self) -> pd.DataFrame:
        """Generate comprehensive validation report"""
        logger.info("Generating validation report...")

        all_results = []

        # Run all validations
        results = [
            self.validate_us_percentile_data(),
            self.validate_us_quintile_data(),
            self.validate_tax_type_data(),
            self.validate_international_data()
        ]

        # Compile results
        for result in results:
            for validation in result['validations']:
                all_results.append({
                    'dataset': result['dataset'],
                    'check': validation['check'],
                    'expected': str(validation['expected']),
                    'actual': str(validation['actual']),
                    'status': '✓ PASS' if validation['pass'] else '✗ FAIL',
                    'notes': validation['notes']
                })

        df = pd.DataFrame(all_results)

        # Save report
        output_file = OUTPUT_DIR / "data_validation_report.xlsx"
        df.to_excel(output_file, index=False, sheet_name='Data')
        logger.info(f"Validation report saved to {output_file}")

        # Summary statistics
        total_checks = len(all_results)
        passed = sum(1 for r in all_results if '✓' in r['status'])
        failed = total_checks - passed

        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total checks performed: {total_checks}")
        logger.info(f"Passed: {passed} ({passed/total_checks*100:.1f}%)")
        logger.info(f"Failed: {failed} ({failed/total_checks*100:.1f}%)")
        logger.info("=" * 60)

        # Print failed checks if any
        if failed > 0:
            logger.warning("\nFailed checks:")
            for r in all_results:
                if '✗' in r['status']:
                    logger.warning(f"  - {r['dataset']}: {r['check']}")
                    logger.warning(f"    Expected: {r['expected']}, Actual: {r['actual']}")

        return df

    def run_all_validations(self):
        """Run all validation checks"""
        logger.info("=" * 60)
        logger.info("Starting Data Validation")
        logger.info("=" * 60)

        self.load_all_data()
        report = self.generate_validation_report()

        return report


def main():
    """Main execution function"""
    logger.info("Data Validation Script - Gerhard Project")

    validator = DataValidator()
    report = validator.run_all_validations()

    logger.info("\nValidation complete. Report saved to Output/Data/data_validation_report.xlsx")


if __name__ == "__main__":
    main()
