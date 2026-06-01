"""
Country Analysis Script
Analyzes tax data for individual countries
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, countries_dir

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()
DATA_DIR = output_data_dir()


class CountryAnalyzer:
    """Analyzes tax data for individual countries"""

    def __init__(self, country_code, country_name):
        self.country_code = country_code
        self.country_name = country_name
        self.country_dir = COUNTRIES_DIR / country_code
        self.data = None
        self.config = None
        self.analysis_results = {}

    def load_data(self):
        """Load country data and configuration"""
        # Load country data
        data_file = self.country_dir / "Output" / "Data" / f"{self.country_code.lower()}_national_tax_data.xlsx"
        if data_file.exists():
            self.data = pd.read_excel(data_file)
            logger.info(f"  Loaded {len(self.data)} years of data")
        else:
            logger.warning(f"  No data file found")
            return False

        # Load config
        config_file = self.country_dir / "Technical" / "data" / "config.json"
        with open(config_file, 'r') as f:
            self.config = json.load(f)

        return True

    def calculate_summary_statistics(self):
        """Calculate summary statistics"""
        if self.data is None or len(self.data) == 0:
            return

        tax_data = self.data['tax_revenue_pct_gdp'].dropna()

        summary = {
            'mean': float(tax_data.mean()),
            'median': float(tax_data.median()),
            'std': float(tax_data.std()),
            'min': float(tax_data.min()),
            'max': float(tax_data.max()),
            'first_year': int(self.data['year'].min()),
            'last_year': int(self.data['year'].max()),
            'total_years': len(self.data),
            'data_points': int(tax_data.count())
        }

        self.analysis_results['summary_statistics'] = summary
        logger.info(f"  Mean tax: {summary['mean']:.2f}% of GDP")

    def calculate_trends(self):
        """Calculate trends over time"""
        if self.data is None or len(self.data) < 2:
            return

        # Overall trend
        tax_data = self.data[['year', 'tax_revenue_pct_gdp']].dropna()

        if len(tax_data) >= 2:
            # Linear regression
            coefficients = np.polyfit(tax_data['year'], tax_data['tax_revenue_pct_gdp'], 1)
            slope = coefficients[0]

            # Change over time
            first_value = tax_data.iloc[0]['tax_revenue_pct_gdp']
            last_value = tax_data.iloc[-1]['tax_revenue_pct_gdp']
            total_change = last_value - first_value
            pct_change = (total_change / first_value * 100) if first_value != 0 else 0

            trends = {
                'slope': float(slope),
                'trend_direction': 'Increasing' if slope > 0.05 else 'Decreasing' if slope < -0.05 else 'Stable',
                'first_value': float(first_value),
                'last_value': float(last_value),
                'total_change': float(total_change),
                'percent_change': float(pct_change)
            }

            self.analysis_results['trends'] = trends
            logger.info(f"  Trend: {trends['trend_direction']} ({trends['percent_change']:.1f}% change)")

    def calculate_decade_analysis(self):
        """Analyze by decade"""
        if self.data is None or len(self.data) == 0:
            return

        self.data['decade'] = (self.data['year'] // 10) * 10
        decade_stats = self.data.groupby('decade')['tax_revenue_pct_gdp'].agg(['mean', 'count']).reset_index()

        decades = []
        for _, row in decade_stats.iterrows():
            decades.append({
                'decade': int(row['decade']),
                'average_tax_pct_gdp': float(row['mean']),
                'years_available': int(row['count'])
            })

        self.analysis_results['decade_analysis'] = decades

    def compare_to_global(self):
        """Compare to global averages"""
        # Load global/world data for comparison
        world_file = COUNTRIES_DIR / "1W" / "Output" / "Data" / "1w_national_tax_data.xlsx"
        if world_file.exists() and self.data is not None:
            world_data = pd.read_excel(world_file)

            # Get latest year comparison
            latest_year = int(self.data['year'].max())
            country_latest = self.data[self.data['year'] == latest_year]['tax_revenue_pct_gdp'].iloc[0]

            world_latest = world_data[world_data['year'] == latest_year]['tax_revenue_pct_gdp']
            if len(world_latest) > 0:
                world_value = float(world_latest.iloc[0])
                difference = country_latest - world_value

                comparison = {
                    'country_value': float(country_latest),
                    'world_value': world_value,
                    'difference': float(difference),
                    'comparison_year': latest_year,
                    'relative_position': 'Above world average' if difference > 0 else 'Below world average'
                }

                self.analysis_results['global_comparison'] = comparison
                logger.info(f"  {comparison['relative_position']} by {abs(difference):.2f}pp")

    def identify_significant_changes(self):
        """Identify significant year-over-year changes"""
        if self.data is None or len(self.data) < 2:
            return

        self.data = self.data.sort_values('year')
        self.data['change'] = self.data['tax_revenue_pct_gdp'].diff()

        # Identify significant changes (> 2 percentage points)
        significant = self.data[abs(self.data['change']) > 2.0].copy()

        changes = []
        for _, row in significant.iterrows():
            changes.append({
                'year': int(row['year']),
                'change': float(row['change']),
                'new_value': float(row['tax_revenue_pct_gdp'])
            })

        if changes:
            self.analysis_results['significant_changes'] = changes
            logger.info(f"  Found {len(changes)} significant changes")

    def save_analysis(self):
        """Save analysis results"""
        # Save as Excel
        output_file = self.country_dir / "Output" / "Data" / f"{self.country_code.lower()}_analysis_summary.xlsx"

        # Create summary DataFrame
        summary_data = []
        if 'summary_statistics' in self.analysis_results:
            stats = self.analysis_results['summary_statistics']
            summary_data.append({
                'Metric': 'Average Tax (% GDP)',
                'Value': f"{stats['mean']:.2f}%"
            })
            summary_data.append({
                'Metric': 'Median Tax (% GDP)',
                'Value': f"{stats['median']:.2f}%"
            })
            summary_data.append({
                'Metric': 'Minimum',
                'Value': f"{stats['min']:.2f}%"
            })
            summary_data.append({
                'Metric': 'Maximum',
                'Value': f"{stats['max']:.2f}%"
            })
            summary_data.append({
                'Metric': 'Coverage Years',
                'Value': f"{stats['first_year']}-{stats['last_year']}"
            })
            summary_data.append({
                'Metric': 'Total Years',
                'Value': stats['total_years']
            })

        if 'trends' in self.analysis_results:
            trends = self.analysis_results['trends']
            summary_data.append({
                'Metric': 'Trend Direction',
                'Value': trends['trend_direction']
            })
            summary_data.append({
                'Metric': 'Total Change',
                'Value': f"{trends['percent_change']:.1f}%"
            })

        if 'global_comparison' in self.analysis_results:
            comp = self.analysis_results['global_comparison']
            summary_data.append({
                'Metric': 'vs World Average',
                'Value': comp['relative_position']
            })
            summary_data.append({
                'Metric': 'Difference',
                'Value': f"{comp['difference']:.2f}pp"
            })

        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(output_file, index=False, sheet_name='Summary')

        # Save JSON for programmatic access
        json_file = self.country_dir / "Technical" / "data" / "analysis_results.json"
        with open(json_file, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)

        # Update config
        self.config['analysis']['completed'] = True
        self.config['status'] = 'analyzed'

        config_file = self.country_dir / "Technical" / "data" / "config.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

        logger.info(f"  Saved analysis results")

    def analyze(self):
        """Run complete analysis"""
        logger.info(f"Analyzing {self.country_name} ({self.country_code})")

        if not self.load_data():
            return False

        self.calculate_summary_statistics()
        self.calculate_trends()
        self.calculate_decade_analysis()
        self.compare_to_global()
        self.identify_significant_changes()
        self.save_analysis()

        return True


class BulkCountryAnalyzer:
    """Analyze multiple countries"""

    def __init__(self):
        self.countries = self.load_country_list()

    def load_country_list(self):
        """Load list of all countries"""
        countries = []
        for country_dir in sorted(COUNTRIES_DIR.iterdir()):
            if country_dir.is_dir():
                config_file = country_dir / "Technical" / "data" / "config.json"
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                        if config['data_collection']['national_data']:
                            countries.append({
                                'code': config['country_code'],
                                'name': config['country_name'],
                                'tier': config.get('tier', 3)
                            })
        return countries

    def analyze_tier(self, tier):
        """Analyze all countries in a specific tier"""
        logger.info("=" * 60)
        logger.info(f"Analyzing Tier {tier} Countries")
        logger.info("=" * 60)

        tier_countries = [c for c in self.countries if c['tier'] == tier]
        logger.info(f"Found {len(tier_countries)} Tier {tier} countries")

        analyzed = 0
        for country in tier_countries:
            try:
                analyzer = CountryAnalyzer(country['code'], country['name'])
                if analyzer.analyze():
                    analyzed += 1
            except Exception as e:
                logger.error(f"Error analyzing {country['name']}: {e}")

        logger.info(f"\nCompleted analysis for {analyzed}/{len(tier_countries)} countries")
        return analyzed

    def analyze_all(self):
        """Analyze all countries"""
        logger.info("=" * 60)
        logger.info("Analyzing All Countries")
        logger.info("=" * 60)

        total = 0
        total += self.analyze_tier(1)
        total += self.analyze_tier(2)
        total += self.analyze_tier(3)

        logger.info("\n" + "=" * 60)
        logger.info("Analysis Complete!")
        logger.info("=" * 60)
        logger.info(f"Total countries analyzed: {total}")


def main():
    logger.info("Country Analysis - Gerhard Project")

    analyzer = BulkCountryAnalyzer()

    # Start with Tier 1 countries
    logger.info("\nStarting with Tier 1 (Comprehensive) countries...")
    analyzer.analyze_tier(1)

    logger.info("\nTier 1 analysis complete!")
    logger.info("Next: Tier 2 and 3 countries, then report generation")


if __name__ == "__main__":
    main()
