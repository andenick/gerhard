"""
Historical Trends Analysis
Analyzes how tax burden distribution has evolved over time
Project: Gerhard
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)

DATA_DIR = output_data_dir()
VIZ_DIR = output_pdfs_dir()

class HistoricalTrendsAnalyzer:
    """Analyzes historical evolution of tax systems"""

    def __init__(self):
        self.data = {}

    def load_historical_data(self):
        """Load all historical datasets"""
        logger.info("Loading historical data...")

        datasets = {
            'us_historical': 'us_historical_tax_data_comprehensive.xlsx',
            'intl_historical': 'international_historical_tax_data.xlsx',
            'major_economies': 'major_economies_tax_time_series.xlsx',
        }

        for name, filename in datasets.items():
            file_path = DATA_DIR / filename
            if file_path.exists():
                self.data[name] = pd.read_excel(file_path)
                logger.info(f"  Loaded {name}: {len(self.data[name])} records")

    def analyze_us_historical_evolution(self):
        """Analyze how US tax system has evolved"""
        logger.info("Analyzing US historical evolution...")

        df = self.data['us_historical']

        # Key eras in US tax history
        eras = {
            'Progressive Era': (1913, 1920),
            'Roaring Twenties': (1921, 1929),
            'New Deal': (1933, 1945),
            'Post-War': (1946, 1963),
            'JFK/LBJ Cuts': (1964, 1968),
            '1970s': (1970, 1980),
            'Reagan Era': (1981, 1992),
            'Clinton Era': (1993, 2000),
            '2000s': (2001, 2008),
            'Great Recession': (2009, 2012),
            'Recovery': (2013, 2017),
            'Trump Cuts': (2018, 2021),
        }

        era_analysis = []
        for era_name, (start, end) in eras.items():
            era_data = df[(df['year'] >= start) & (df['year'] <= end)]
            if len(era_data) > 0:
                analysis = {
                    'era': era_name,
                    'years': f"{start}-{end}",
                    'avg_top_marginal_rate': era_data['top_marginal_rate'].mean(),
                    'avg_top1_share': era_data['top_1_percent_share'].mean() if 'top_1_percent_share' in era_data.columns else None,
                    'avg_top1_rate': era_data['top_1_percent_avg_rate'].mean() if 'top_1_percent_avg_rate' in era_data.columns else None,
                    'n_years': len(era_data)
                }
                era_analysis.append(analysis)

        df_eras = pd.DataFrame(era_analysis)

        # Save era analysis
        output_file = DATA_DIR / "us_tax_evolution_by_era.xlsx"
        write_single_sheet_excel(df_eras, output_file)
        logger.info(f"Era analysis saved to {output_file}")

        return df_eras

    def analyze_international_convergence(self):
        """Analyze if countries are converging on similar tax levels"""
        logger.info("Analyzing international convergence...")

        df = self.data['major_economies']

        # Calculate coefficient of variation by year (measure of dispersion)
        convergence = []
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]['tax_revenue_pct_gdp'].dropna()
            if len(year_data) >= 5:  # Need at least 5 countries
                convergence.append({
                    'year': int(year),
                    'mean_tax_rate': year_data.mean(),
                    'std_tax_rate': year_data.std(),
                    'coef_variation': (year_data.std() / year_data.mean()) * 100 if year_data.mean() > 0 else None,
                    'n_countries': len(year_data)
                })

        df_convergence = pd.DataFrame(convergence)

        # Save
        output_file = DATA_DIR / "international_convergence_analysis.xlsx"
        write_single_sheet_excel(df_convergence, output_file)
        logger.info(f"Convergence analysis saved to {output_file}")

        return df_convergence

    def identify_major_shifts(self):
        """Identify major shifts in tax policy"""
        logger.info("Identifying major policy shifts...")

        df = self.data['us_historical']
        df = df.sort_values('year')

        shifts = []

        # Look for large changes in top marginal rate
        df['rate_change'] = df['top_marginal_rate'].diff()

        for idx, row in df.iterrows():
            if abs(row['rate_change']) > 5:  # More than 5 percentage point change
                shifts.append({
                    'year': int(row['year']),
                    'type': 'Marginal Rate Change',
                    'change': f"{row['rate_change']:+.1f} percentage points",
                    'new_rate': row['top_marginal_rate'],
                    'significance': 'Major' if abs(row['rate_change']) > 15 else 'Moderate',
                    'direction': 'Increase' if row['rate_change'] > 0 else 'Decrease'
                })

        # Add known major reforms
        known_reforms = [
            (1913, 'Income Tax Established', 'Federal income tax begins', 'Major'),
            (1917, 'War Revenue Act', 'Dramatic rate increases for WWI', 'Major'),
            (1935, 'Wealth Tax Act', 'New Deal tax increases', 'Major'),
            (1964, 'Revenue Act', 'Kennedy-Johnson tax cuts', 'Major'),
            (1981, 'ERTA', 'Reagan tax cuts begin', 'Major'),
            (1986, 'Tax Reform Act', 'Major reform, lower rates, broader base', 'Major'),
            (1993, 'Omnibus Budget Act', 'Clinton tax increases', 'Moderate'),
            (2001, 'EGTRRA', 'Bush tax cuts', 'Major'),
            (2017, 'TCJA', 'Trump tax cuts', 'Major'),
        ]

        for year, name, desc, sig in known_reforms:
            shifts.append({
                'year': year,
                'type': 'Legislative Reform',
                'change': name,
                'description': desc,
                'significance': sig,
                'direction': 'Reform'
            })

        df_shifts = pd.DataFrame(shifts)
        df_shifts = df_shifts.sort_values('year')

        # Save
        output_file = DATA_DIR / "major_tax_policy_shifts.xlsx"
        write_single_sheet_excel(df_shifts, output_file)
        logger.info(f"Policy shifts saved to {output_file}")

        return df_shifts

    def create_century_overview(self):
        """Create overview of entire 20th/21st century"""
        logger.info("Creating century overview...")

        df = self.data['us_historical']

        # Decade summaries
        decades = []
        for decade_start in range(1910, 2030, 10):
            decade_data = df[(df['year'] >= decade_start) & (df['year'] < decade_start + 10)]
            if len(decade_data) > 0:
                decades.append({
                    'decade': f"{decade_start}s",
                    'start_year': decade_start,
                    'avg_top_marginal_rate': decade_data['top_marginal_rate'].mean(),
                    'max_top_marginal_rate': decade_data['top_marginal_rate'].max(),
                    'min_top_marginal_rate': decade_data['top_marginal_rate'].min(),
                    'avg_top1_share': decade_data['top_1_percent_share'].mean() if 'top_1_percent_share' in decade_data.columns else None,
                    'n_years_data': len(decade_data)
                })

        df_decades = pd.DataFrame(decades)

        # Save
        output_file = DATA_DIR / "us_tax_history_by_decade.xlsx"
        write_single_sheet_excel(df_decades, output_file)
        logger.info(f"Decade overview saved to {output_file}")

        return df_decades

    def create_historical_visualizations(self):
        """Create comprehensive historical visualizations"""
        logger.info("Creating historical visualizations...")

        df_us = self.data['us_historical']

        # 1. Full US history - Top marginal rate
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.plot(df_us['year'], df_us['top_marginal_rate'],
                linewidth=2.5, color='#2c3e50', marker='o', markersize=4)
        ax.fill_between(df_us['year'], df_us['top_marginal_rate'],
                        alpha=0.3, color='#3498db')

        # Annotate major events
        events = [
            (1913, 'Income\nTax\nBegins'),
            (1945, 'WWII\nPeak\n94%'),
            (1964, 'JFK/LBJ\nCuts'),
            (1986, 'Tax\nReform'),
            (2017, 'Trump\nCuts'),
        ]
        for year, label in events:
            if year in df_us['year'].values:
                rate = df_us[df_us['year'] == year]['top_marginal_rate'].values[0]
                ax.annotate(label, xy=(year, rate), xytext=(year, rate + 10),
                           ha='center', fontsize=9, fontweight='bold',
                           arrowprops=dict(arrowstyle='->', lw=1.5))

        ax.set_xlabel('Year', fontweight='bold', fontsize=12)
        ax.set_ylabel('Top Marginal Tax Rate (%)', fontweight='bold', fontsize=12)
        ax.set_title('History of US Top Marginal Income Tax Rate\n1913-2021',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(1910, 2025)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        output_file = VIZ_DIR / "07_us_tax_history_full_timeline.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        plt.close()

        # 2. Detailed modern era (1979-2021) - Top 1% share and rate
        df_modern = df_us[df_us['year'] >= 1979].copy()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))

        # Top 1% share of taxes
        ax1.plot(df_modern['year'], df_modern['top_1_percent_share'],
                linewidth=3, color='#e74c3c', marker='o', markersize=6)
        ax1.fill_between(df_modern['year'], df_modern['top_1_percent_share'],
                        alpha=0.3, color='#e74c3c')
        ax1.set_ylabel('Share of Federal Income Taxes (%)', fontweight='bold', fontsize=11)
        ax1.set_title('Evolution of US Tax Distribution: Top 1% (1979-2021)',
                     fontsize=15, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(1978, 2022)

        # Top 1% average tax rate
        ax2.plot(df_modern['year'], df_modern['top_1_percent_avg_rate'],
                linewidth=3, color='#2ecc71', marker='s', markersize=6)
        ax2.fill_between(df_modern['year'], df_modern['top_1_percent_avg_rate'],
                        alpha=0.3, color='#2ecc71')
        ax2.set_xlabel('Year', fontweight='bold', fontsize=11)
        ax2.set_ylabel('Average Tax Rate (%)', fontweight='bold', fontsize=11)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(1978, 2022)

        plt.tight_layout()
        output_file = VIZ_DIR / "08_us_top1_percent_evolution.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        plt.close()

        # 3. International - Major economies over time
        df_major = self.data['major_economies']

        # Select key countries for cleaner visualization
        key_countries = ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'SWE', 'CHN']
        df_key = df_major[df_major['country_code'].isin(key_countries)].copy()

        fig, ax = plt.subplots(figsize=(16, 10))

        for country in key_countries:
            country_data = df_key[df_key['country_code'] == country]
            if len(country_data) > 10:  # Only plot if sufficient data
                ax.plot(country_data['year'], country_data['tax_revenue_pct_gdp'],
                       linewidth=2, marker='o', markersize=3, label=country, alpha=0.8)

        ax.set_xlabel('Year', fontweight='bold', fontsize=12)
        ax.set_ylabel('Tax Revenue (% of GDP)', fontweight='bold', fontsize=12)
        ax.set_title('Tax Revenue Trends in Major Economies\n1972-2023',
                    fontsize=16, fontweight='bold', pad=20)
        ax.legend(loc='upper left', frameon=True, shadow=True, ncol=2)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_file = VIZ_DIR / "09_major_economies_trends.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        plt.close()

    def run_all_analyses(self):
        """Run all historical analyses"""
        logger.info("=" * 60)
        logger.info("Historical Trends Analysis")
        logger.info("=" * 60)

        self.load_historical_data()

        # Run analyses
        eras = self.analyze_us_historical_evolution()
        convergence = self.analyze_international_convergence()
        shifts = self.identify_major_shifts()
        decades = self.create_century_overview()

        # Create visualizations
        self.create_historical_visualizations()

        logger.info("\n" + "=" * 60)
        logger.info("Historical Analysis Complete!")
        logger.info("=" * 60)
        logger.info(f"US data spans: 1913-2021 (109 years)")
        logger.info(f"International data spans: 1972-2024 (52 years)")
        logger.info(f"Major policy shifts identified: {len(shifts)}")
        logger.info("=" * 60)


def main():
    logger.info("Historical Trends Analysis - Gerhard Project")

    analyzer = HistoricalTrendsAnalyzer()
    analyzer.run_all_analyses()


if __name__ == "__main__":
    main()
