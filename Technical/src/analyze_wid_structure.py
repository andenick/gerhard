"""
Analyze WID.world Data Structure
Understand variables, coverage, and prepare for integration

Project: Gerhard - Enhanced with Distributional Data
"""

import pandas as pd
import json
from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir

logger = setup_logging(__name__)

WID_DIR = raw_data_dir() / "wid"
OUTPUT_DIR = output_data_dir()


class WIDAnalyzer:
    """Analyze WID.world data structure"""

    def __init__(self):
        self.countries_file = WID_DIR / "WID_countries.csv"
        self.summary = defaultdict(dict)

    def load_countries(self):
        """Load WID countries list"""
        logger.info("=" * 60)
        logger.info("Loading WID.world Countries")
        logger.info("=" * 60)

        df = pd.read_csv(self.countries_file, sep=';')
        logger.info(f"Total countries: {len(df)}")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info("")

        # Show sample
        logger.info("Sample countries:")
        for _, row in df.head(10).iterrows():
            logger.info(f"  {row['alpha2']}: {row['shortname']} ({row['region2']})")

        self.summary['total_countries'] = len(df)
        self.summary['countries'] = df.to_dict('records')

        return df

    def analyze_sample_country(self, country_code='US'):
        """Analyze a sample country's data structure"""
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Analyzing Sample Country: {country_code}")
        logger.info("=" * 60)

        data_file = WID_DIR / f"WID_data_{country_code}.csv"

        if not data_file.exists():
            logger.warning(f"File not found: {data_file}")
            return None

        logger.info(f"Loading {data_file.name}...")
        df = pd.read_csv(data_file, sep=';')

        logger.info(f"Total rows: {len(df):,}")
        logger.info(f"Columns: {df.columns.tolist()}")
        logger.info("")

        # Analyze variables
        variables = df['variable'].unique()
        logger.info(f"Variables: {len(variables)}")
        logger.info("Sample variables:")
        for var in list(variables)[:20]:
            logger.info(f"  {var}")

        # Analyze percentiles
        percentiles = df['percentile'].unique()
        logger.info("")
        logger.info(f"Percentiles: {len(percentiles)}")
        logger.info("Available percentiles:")
        for pct in sorted(percentiles)[:20]:
            logger.info(f"  {pct}")

        # Analyze years
        years = df['year'].unique()
        logger.info("")
        logger.info(f"Years: {min(years)} to {max(years)} ({len(years)} years)")

        # Sample data
        logger.info("")
        logger.info("Sample data:")
        print(df.head(10).to_string())

        return df

    def identify_key_variables(self):
        """Identify key variables for tax/income distribution"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Key Variables for Integration")
        logger.info("=" * 60)

        # WID variable naming convention
        # First letter: metric type
        # s = share, a = average, t = threshold, m = minimum
        # Next letters: concept
        # ptinc = pre-tax national income
        # diinc = post-tax disposable income
        # hweal = net wealth
        # fiinc = fiscal income
        # Last 3 digits: population code
        # 992 = tax unit
        # 999 = equal-split adults

        key_variables = {
            'top_income_shares': {
                'sptinc992j': 'Top 10% pre-tax income share',
                'sptinc992i': 'Top 1% pre-tax income share',
                'sptinc992t': 'Top 0.1% pre-tax income share',
                'sptinc992u': 'Top 0.01% pre-tax income share',
                'sdiinc992j': 'Top 10% post-tax income share',
                'sdiinc992i': 'Top 1% post-tax income share',
            },
            'middle_bottom_shares': {
                'sptinc992m': 'Middle 40% pre-tax income share',
                'sptinc992n': 'Bottom 50% pre-tax income share',
                'sdiinc992m': 'Middle 40% post-tax income share',
                'sdiinc992n': 'Bottom 50% post-tax income share',
            },
            'wealth_shares': {
                'shweal992j': 'Top 10% wealth share',
                'shweal992i': 'Top 1% wealth share',
                'shweal992t': 'Top 0.1% wealth share',
            },
            'average_income': {
                'aptinc992j': 'Average income of top 10%',
                'aptinc992i': 'Average income of top 1%',
                'adiinc992j': 'Average post-tax income of top 10%',
                'adiinc992i': 'Average post-tax income of top 1%',
            },
            'income_thresholds': {
                'tptinc992j': 'Income threshold for top 10%',
                'tptinc992i': 'Income threshold for top 1%',
                'tdiinc992j': 'Post-tax threshold for top 10%',
                'tdiinc992i': 'Post-tax threshold for top 1%',
            }
        }

        logger.info("Variables to integrate:")
        for category, vars in key_variables.items():
            logger.info(f"\n{category.upper().replace('_', ' ')}:")
            for var_code, description in vars.items():
                logger.info(f"  {var_code}: {description}")

        self.summary['key_variables'] = key_variables

        return key_variables

    def check_country_coverage(self):
        """Check which countries have which variables"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Checking Country Coverage")
        logger.info("=" * 60)

        coverage = {}

        # Sample 20 major countries
        major_countries = ['US', 'GB', 'FR', 'DE', 'JP', 'CN', 'IN', 'BR',
                          'CA', 'AU', 'IT', 'ES', 'MX', 'KR', 'RU',
                          'NL', 'CH', 'SE', 'NO', 'DK']

        for country in major_countries:
            data_file = WID_DIR / f"WID_data_{country}.csv"

            if not data_file.exists():
                continue

            try:
                df = pd.read_csv(data_file, sep=';', nrows=10000)  # Sample for speed
                variables = set(df['variable'].unique())
                years = df['year'].unique()

                coverage[country] = {
                    'variables': len(variables),
                    'years_range': f"{min(years)}-{max(years)}",
                    'years_count': len(years),
                    'has_top1_income': 'sptinc992i' in variables,
                    'has_top10_income': 'sptinc992j' in variables,
                    'has_wealth': 'shweal992i' in variables,
                }

                logger.info(f"{country}: {coverage[country]['years_count']} years, "
                          f"{coverage[country]['variables']} variables, "
                          f"Top 1% Income: {coverage[country]['has_top1_income']}, "
                          f"Wealth: {coverage[country]['has_wealth']}")

            except Exception as e:
                logger.warning(f"Error processing {country}: {e}")

        self.summary['coverage'] = coverage

        return coverage

    def create_integration_plan(self):
        """Create plan for integrating WID data"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Integration Plan")
        logger.info("=" * 60)

        plan = {
            'phase_1': {
                'name': 'Extract Core Variables',
                'tasks': [
                    'Extract top 1%, 10% income shares for all countries',
                    'Extract bottom 50%, middle 40% shares where available',
                    'Extract wealth shares (top 1%, 10%) where available',
                    'Create country-specific Excel files with distributional data'
                ]
            },
            'phase_2': {
                'name': 'Integrate with Existing Data',
                'tasks': [
                    'Match WID country codes to our ISO codes',
                    'Merge WID distributional data with tax-to-GDP data',
                    'Add new variables to country analysis JSON',
                    'Update country data files with inequality metrics'
                ]
            },
            'phase_3': {
                'name': 'Enhance Analyses',
                'tasks': [
                    'Add inequality visualizations to country reports',
                    'Create top income share time series charts',
                    'Add wealth distribution charts where available',
                    'Update PDF reports with distributional analysis'
                ]
            },
            'phase_4': {
                'name': 'US State-Level Integration',
                'tasks': [
                    'Extract US state data (50 states available)',
                    'Create state-level directories',
                    'Generate state-specific reports',
                    'Add US regional comparison'
                ]
            }
        }

        logger.info("Four-Phase Integration:")
        for phase_key, phase_info in plan.items():
            logger.info(f"\n{phase_key.upper()}: {phase_info['name']}")
            for i, task in enumerate(phase_info['tasks'], 1):
                logger.info(f"  {i}. {task}")

        self.summary['integration_plan'] = plan

        return plan

    def save_summary(self):
        """Save analysis summary"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("Saving Analysis Summary")
        logger.info("=" * 60)

        summary_file = WID_DIR / "wid_analysis_summary.json"

        with open(summary_file, 'w') as f:
            json.dump(self.summary, f, indent=2, default=str)

        logger.info(f"✅ Summary saved to: {summary_file}")

        # Also create human-readable version
        readme_file = WID_DIR / "WID_DATA_README.md"

        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write("# WID.world Data Analysis Summary\n\n")
            f.write(f"**Total Countries:** {self.summary.get('total_countries', 'N/A')}\n\n")

            f.write("## Key Variables Available\n\n")
            for category, vars in self.summary.get('key_variables', {}).items():
                f.write(f"### {category.replace('_', ' ').title()}\n\n")
                for var_code, description in vars.items():
                    f.write(f"- `{var_code}`: {description}\n")
                f.write("\n")

            f.write("## Major Country Coverage\n\n")
            for country, info in self.summary.get('coverage', {}).items():
                f.write(f"**{country}**: {info['years_count']} years ({info['years_range']}), "
                       f"{info['variables']} variables\n")
                f.write(f"  - Top 1% Income Share: {'✅' if info['has_top1_income'] else '❌'}\n")
                f.write(f"  - Wealth Data: {'✅' if info['has_wealth'] else '❌'}\n\n")

        logger.info(f"✅ README saved to: {readme_file}")

    def run_full_analysis(self):
        """Run complete WID analysis"""
        logger.info("🔍 WID.world Data Structure Analysis")
        logger.info("")

        # Step 1: Load countries
        countries = self.load_countries()

        # Step 2: Analyze sample country
        sample_data = self.analyze_sample_country('US')

        # Step 3: Identify key variables
        key_vars = self.identify_key_variables()

        # Step 4: Check coverage
        coverage = self.check_country_coverage()

        # Step 5: Create integration plan
        plan = self.create_integration_plan()

        # Step 6: Save summary
        self.save_summary()

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ WID Analysis Complete!")
        logger.info("=" * 60)
        logger.info(f"Countries: {self.summary['total_countries']}")
        logger.info(f"Key variable categories: {len(key_vars)}")
        logger.info(f"Countries checked: {len(coverage)}")
        logger.info("")


def main():
    analyzer = WIDAnalyzer()
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
