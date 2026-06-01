"""
Global Comparative Analysis
Creates summary analysis across all countries
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, countries_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()
OUTPUT_DIR = output_data_dir()


class GlobalAnalyzer:
    """Creates global comparative analysis"""

    def __init__(self):
        self.all_data = []
        self.all_analysis = []
        self.load_all_countries()

    def load_all_countries(self):
        """Load data and analysis from all countries"""
        logger.info("Loading data from all countries...")

        for country_dir in sorted(COUNTRIES_DIR.iterdir()):
            if country_dir.is_dir():
                # Load config
                config_file = country_dir / "Technical" / "data" / "config.json"
                if not config_file.exists():
                    continue

                with open(config_file, 'r') as f:
                    config = json.load(f)

                # Load analysis
                analysis_file = country_dir / "Technical" / "data" / "analysis_results.json"
                if analysis_file.exists():
                    with open(analysis_file, 'r') as f:
                        analysis = json.load(f)
                        analysis['country_code'] = config['country_code']
                        analysis['country_name'] = config['country_name']
                        analysis['tier'] = config.get('tier', 3)
                        self.all_analysis.append(analysis)

                # Load data
                data_file = country_dir / "Output" / "Data" / f"{config['country_code'].lower()}_national_tax_data.xlsx"
                if data_file.exists():
                    df = pd.read_excel(data_file)
                    df['tier'] = config.get('tier', 3)
                    self.all_data.append(df)

        logger.info(f"Loaded {len(self.all_analysis)} countries")

    def create_global_rankings(self):
        """Create global rankings by tax level"""
        logger.info("Creating global rankings...")

        rankings = []
        for analysis in self.all_analysis:
            if 'global_comparison' in analysis and 'summary_statistics' in analysis:
                comp = analysis['global_comparison']
                stats = analysis['summary_statistics']
                rankings.append({
                    'Country': analysis['country_name'],
                    'Code': analysis['country_code'],
                    'Tier': analysis['tier'],
                    'Latest_Tax_PCT_GDP': comp.get('country_value', 0),
                    'Average_Tax_PCT_GDP': stats.get('mean', 0),
                    'Latest_Year': comp.get('comparison_year', 'N/A'),
                    'Years_of_Data': stats.get('total_years', 0),
                    'Trend': analysis.get('trends', {}).get('trend_direction', 'N/A')
                })

        df_rankings = pd.DataFrame(rankings)
        df_rankings = df_rankings.sort_values('Latest_Tax_PCT_GDP', ascending=False)

        # Add ranking
        df_rankings['Rank'] = range(1, len(df_rankings) + 1)

        # Reorder columns
        df_rankings = df_rankings[['Rank', 'Country', 'Code', 'Latest_Tax_PCT_GDP',
                                   'Average_Tax_PCT_GDP', 'Tier', 'Trend',
                                   'Years_of_Data', 'Latest_Year']]

        output_file = OUTPUT_DIR / "global_tax_rankings.xlsx"
        write_single_sheet_excel(df_rankings, output_file, sheet_name='Rankings')
        logger.info(f"Created global rankings with {len(df_rankings)} countries")

        return df_rankings

    def create_tier_comparison(self):
        """Compare statistics by tier"""
        logger.info("Creating tier comparison...")

        tier_stats = []
        for tier in [1, 2, 3]:
            tier_analysis = [a for a in self.all_analysis if a.get('tier') == tier]

            if tier_analysis:
                avg_tax = np.mean([a.get('summary_statistics', {}).get('mean', 0)
                                  for a in tier_analysis])
                avg_years = np.mean([a.get('summary_statistics', {}).get('total_years', 0)
                                    for a in tier_analysis])

                increasing = sum(1 for a in tier_analysis
                               if a.get('trends', {}).get('trend_direction') == 'Increasing')
                decreasing = sum(1 for a in tier_analysis
                               if a.get('trends', {}).get('trend_direction') == 'Decreasing')
                stable = sum(1 for a in tier_analysis
                           if a.get('trends', {}).get('trend_direction') == 'Stable')

                tier_stats.append({
                    'Tier': tier,
                    'Tier_Name': 'Comprehensive' if tier == 1 else 'Standard' if tier == 2 else 'Basic',
                    'Countries': len(tier_analysis),
                    'Avg_Tax_PCT_GDP': round(avg_tax, 2),
                    'Avg_Years_Data': round(avg_years, 1),
                    'Increasing_Trend': increasing,
                    'Decreasing_Trend': decreasing,
                    'Stable_Trend': stable
                })

        df_tiers = pd.DataFrame(tier_stats)

        output_file = OUTPUT_DIR / "tier_comparison.xlsx"
        write_single_sheet_excel(df_tiers, output_file, sheet_name='Tiers')
        logger.info("Created tier comparison")

        return df_tiers

    def create_regional_analysis(self):
        """Create regional groupings and analysis"""
        logger.info("Creating regional analysis...")

        # Define regional groupings
        regions = {
            'North America': ['US', 'CA', 'MX'],
            'Western Europe': ['GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'BE', 'SE', 'NO', 'DK', 'FI', 'CH', 'AT', 'IE', 'PT', 'GR'],
            'Eastern Europe': ['PL', 'CZ', 'HU', 'RO', 'BG', 'HR', 'SK', 'SI', 'EE', 'LT', 'LV'],
            'Asia-Pacific Developed': ['JP', 'KR', 'AU', 'NZ', 'SG'],
            'Asia Emerging': ['CN', 'IN', 'ID', 'TH', 'MY', 'PH', 'VN', 'PK', 'BD'],
            'Latin America': ['BR', 'AR', 'CL', 'CO', 'PE', 'EC', 'UY', 'PY', 'BO'],
            'Middle East': ['TR', 'IL', 'SA', 'AE', 'KW', 'EG', 'JO'],
            'Sub-Saharan Africa': ['ZA', 'ET', 'GH', 'KE', 'TZ', 'UG', 'NG', 'SN', 'RW']
        }

        regional_stats = []
        for region_name, country_codes in regions.items():
            region_analysis = [a for a in self.all_analysis if a.get('country_code') in country_codes]

            if region_analysis:
                avg_tax = np.mean([a.get('summary_statistics', {}).get('mean', 0)
                                  for a in region_analysis])
                min_tax = min([a.get('summary_statistics', {}).get('mean', 0)
                              for a in region_analysis])
                max_tax = max([a.get('summary_statistics', {}).get('mean', 0)
                              for a in region_analysis])

                regional_stats.append({
                    'Region': region_name,
                    'Countries': len(region_analysis),
                    'Avg_Tax_PCT_GDP': round(avg_tax, 2),
                    'Min_Tax_PCT_GDP': round(min_tax, 2),
                    'Max_Tax_PCT_GDP': round(max_tax, 2),
                    'Range': round(max_tax - min_tax, 2)
                })

        df_regions = pd.DataFrame(regional_stats)
        df_regions = df_regions.sort_values('Avg_Tax_PCT_GDP', ascending=False)

        output_file = OUTPUT_DIR / "regional_comparison.xlsx"
        write_single_sheet_excel(df_regions, output_file, sheet_name='Regions')
        logger.info("Created regional analysis")

        return df_regions

    def create_trend_analysis(self):
        """Analyze global trends"""
        logger.info("Creating trend analysis...")

        trend_summary = []
        for direction in ['Increasing', 'Decreasing', 'Stable']:
            trend_countries = [a for a in self.all_analysis
                             if a.get('trends', {}).get('trend_direction') == direction]

            if trend_countries:
                avg_change = np.mean([a.get('trends', {}).get('percent_change', 0)
                                    for a in trend_countries])

                trend_summary.append({
                    'Trend_Direction': direction,
                    'Countries': len(trend_countries),
                    'Percentage_of_Total': round(len(trend_countries) / len(self.all_analysis) * 100, 1),
                    'Avg_Percent_Change': round(avg_change, 1)
                })

        df_trends = pd.DataFrame(trend_summary)

        output_file = OUTPUT_DIR / "global_trend_summary.xlsx"
        write_single_sheet_excel(df_trends, output_file, sheet_name='Trends')
        logger.info("Created trend analysis")

        return df_trends

    def create_key_findings(self):
        """Create summary of key findings"""
        logger.info("Creating key findings summary...")

        findings = {
            'global_statistics': {
                'total_countries': len(self.all_analysis),
                'total_years_data': sum([a.get('summary_statistics', {}).get('total_years', 0)
                                        for a in self.all_analysis]),
                'avg_years_per_country': round(np.mean([a.get('summary_statistics', {}).get('total_years', 0)
                                                        for a in self.all_analysis]), 1),
                'global_avg_tax': round(np.mean([a.get('summary_statistics', {}).get('mean', 0)
                                                 for a in self.all_analysis]), 2),
                'global_median_tax': round(np.median([a.get('summary_statistics', {}).get('mean', 0)
                                                      for a in self.all_analysis]), 2)
            },
            'extremes': {
                'highest_tax': max([(a.get('country_name'), a.get('summary_statistics', {}).get('mean', 0))
                                   for a in self.all_analysis], key=lambda x: x[1]),
                'lowest_tax': min([(a.get('country_name'), a.get('summary_statistics', {}).get('mean', 0))
                                  for a in self.all_analysis], key=lambda x: x[1]),
                'longest_series': max([(a.get('country_name'), a.get('summary_statistics', {}).get('total_years', 0))
                                      for a in self.all_analysis], key=lambda x: x[1])
            },
            'trends': {
                'increasing': sum(1 for a in self.all_analysis
                                if a.get('trends', {}).get('trend_direction') == 'Increasing'),
                'decreasing': sum(1 for a in self.all_analysis
                                if a.get('trends', {}).get('trend_direction') == 'Decreasing'),
                'stable': sum(1 for a in self.all_analysis
                            if a.get('trends', {}).get('trend_direction') == 'Stable')
            }
        }

        output_file = OUTPUT_DIR / "key_findings_summary.json"
        with open(output_file, 'w') as f:
            json.dump(findings, f, indent=2)
        logger.info("Created key findings summary")

        return findings

    def generate_all(self):
        """Generate all global analyses"""
        logger.info("=" * 60)
        logger.info("Generating Global Comparative Analysis")
        logger.info("=" * 60)

        rankings = self.create_global_rankings()
        tiers = self.create_tier_comparison()
        regions = self.create_regional_analysis()
        trends = self.create_trend_analysis()
        findings = self.create_key_findings()

        logger.info("\n" + "=" * 60)
        logger.info("Global Analysis Complete!")
        logger.info("=" * 60)
        logger.info("Created:")
        logger.info("  - global_tax_rankings.xlsx")
        logger.info("  - tier_comparison.xlsx")
        logger.info("  - regional_comparison.xlsx")
        logger.info("  - global_trend_summary.xlsx")
        logger.info("  - key_findings_summary.json")

        # Print key insights
        logger.info("\nKey Insights:")
        logger.info(f"  Global Average Tax: {findings['global_statistics']['global_avg_tax']}% of GDP")
        logger.info(f"  Highest: {findings['extremes']['highest_tax'][0]} ({findings['extremes']['highest_tax'][1]:.2f}%)")
        logger.info(f"  Lowest: {findings['extremes']['lowest_tax'][0]} ({findings['extremes']['lowest_tax'][1]:.2f}%)")
        logger.info(f"  Trends: {findings['trends']['increasing']} increasing, {findings['trends']['decreasing']} decreasing, {findings['trends']['stable']} stable")


def main():
    logger.info("Global Comparative Analysis - Gerhard Project")

    analyzer = GlobalAnalyzer()
    analyzer.generate_all()

    logger.info("\nAnalysis complete! Check Output/Data/ for results")


if __name__ == "__main__":
    main()
