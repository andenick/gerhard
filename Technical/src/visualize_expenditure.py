"""
Government Expenditure Visualization Script
==========================================

Creates publication-quality visualizations of government expenditure data.

Generates:
- 10-12 charts at 300 DPI
- Comparative analysis across countries
- Time series and cross-sectional views
- Regional and income-level comparisons

Created: October 10, 2025
Project: Gerhard - Fiscal Analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from pathlib import Path
import sys
import json

# Use non-interactive backend
matplotlib.use('Agg')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_pdfs_dir
from utils.config import project_root

logger = setup_logging(__name__)

# Base directories
WB_DATA_DIR = raw_data_dir() / "worldbank" / "expenditure"
OUTPUT_DIR = output_pdfs_dir()


class ExpenditureVisualizer:
    """Create government expenditure visualizations"""

    def __init__(self):
        self.wide_data = None
        self.combined_data = None
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Chart counter
        self.charts_created = 0

    def load_data(self):
        """Load World Bank expenditure data"""
        logger.info("="*80)
        logger.info("Loading World Bank Expenditure Data for Visualization")
        logger.info("="*80)

        # Load wide format
        wide_file = WB_DATA_DIR / "wb_expenditure_wide.csv"
        if wide_file.exists():
            self.wide_data = pd.read_excel(wide_file) if wide_file.suffix == '.xlsx' else pd.read_csv(wide_file)
            logger.info(f"✅ Loaded wide format: {len(self.wide_data):,} observations")

        # Load combined format
        combined_file = WB_DATA_DIR / "wb_expenditure_combined.csv"
        if combined_file.exists():
            self.combined_data = pd.read_csv(combined_file)
            logger.info(f"✅ Loaded combined format: {len(self.combined_data):,} observations")

        return self.wide_data is not None

    def create_global_expenditure_trend(self):
        """Chart 1: Global Government Expenditure Trend (1960-2024)"""
        logger.info("\n[1/12] Creating global expenditure trend chart...")

        # Get world/global aggregate if available
        global_data = self.wide_data[
            (self.wide_data['country_code'] == '1W') |
            (self.wide_data['country_name'].str.contains('World', case=False, na=False))
        ].copy()

        if len(global_data) == 0:
            logger.warning("  No global aggregate data found, skipping...")
            return

        global_data = global_data.sort_values('year')

        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot total expenditure
        ax.plot(global_data['year'], global_data['gov_expenditure_gdp'],
                linewidth=2.5, color='#2E86AB', label='Total Government Expenditure')

        ax.set_title('Global Government Expenditure Trend (1960-2024)',
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Government Expenditure (% of GDP)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=11)

        plt.tight_layout()
        output_file = self.output_dir / "01_global_expenditure_trend.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_top_bottom_countries(self):
        """Chart 2: Top & Bottom 20 Countries by Total Expenditure"""
        logger.info("\n[2/12] Creating top/bottom countries chart...")

        # Get latest year data for each country
        latest_year = self.wide_data['year'].max()
        latest_data = self.wide_data[self.wide_data['year'] == latest_year].copy()

        # Filter out aggregates (typically 2+ char codes that are not countries)
        latest_data = latest_data[
            (latest_data['country_code'].str.len() == 3) |
            ((latest_data['country_code'].str.len() == 2) & ~latest_data['country_code'].str.contains('[0-9]', na=False))
        ]

        # Remove NA values
        latest_data = latest_data[latest_data['gov_expenditure_gdp'].notna()]

        # Get top and bottom 20
        top_20 = latest_data.nlargest(20, 'gov_expenditure_gdp')
        bottom_20 = latest_data.nsmallest(20, 'gov_expenditure_gdp')

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10))

        # Top 20
        ax1.barh(range(len(top_20)), top_20['gov_expenditure_gdp'].values, color='#06A77D')
        ax1.set_yticks(range(len(top_20)))
        ax1.set_yticklabels(top_20['country_name'].values, fontsize=9)
        ax1.set_xlabel('Government Expenditure (% of GDP)', fontsize=11)
        ax1.set_title(f'Top 20 Countries - Highest Expenditure ({latest_year})',
                      fontsize=13, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.invert_yaxis()

        # Bottom 20
        ax2.barh(range(len(bottom_20)), bottom_20['gov_expenditure_gdp'].values, color='#D62828')
        ax2.set_yticks(range(len(bottom_20)))
        ax2.set_yticklabels(bottom_20['country_name'].values, fontsize=9)
        ax2.set_xlabel('Government Expenditure (% of GDP)', fontsize=11)
        ax2.set_title(f'Bottom 20 Countries - Lowest Expenditure ({latest_year})',
                      fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.invert_yaxis()

        plt.tight_layout()
        output_file = self.output_dir / "02_top_bottom_expenditure_countries.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_education_comparison(self):
        """Chart 3: Education Expenditure Comparison"""
        logger.info("\n[3/12] Creating education expenditure comparison...")

        latest_year = self.wide_data['year'].max()
        latest_data = self.wide_data[
            (self.wide_data['year'] == latest_year) &
            (self.wide_data['education_expenditure'].notna())
        ].copy()

        # Filter real countries
        latest_data = latest_data[
            (latest_data['country_code'].str.len() == 3) |
            ((latest_data['country_code'].str.len() == 2) & ~latest_data['country_code'].str.contains('[0-9]', na=False))
        ]

        top_20 = latest_data.nlargest(20, 'education_expenditure')

        fig, ax = plt.subplots(figsize=(14, 10))
        bars = ax.barh(range(len(top_20)), top_20['education_expenditure'].values, color='#F77F00')
        ax.set_yticks(range(len(top_20)))
        ax.set_yticklabels(top_20['country_name'].values, fontsize=10)
        ax.set_xlabel('Education Expenditure (% of GDP)', fontsize=12)
        ax.set_title(f'Top 20 Countries - Education Expenditure ({latest_year})',
                     fontsize=15, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

        plt.tight_layout()
        output_file = self.output_dir / "03_education_expenditure_top20.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_health_comparison(self):
        """Chart 4: Health Expenditure Comparison"""
        logger.info("\n[4/12] Creating health expenditure comparison...")

        latest_year = self.wide_data['year'].max()
        latest_data = self.wide_data[
            (self.wide_data['year'] == latest_year) &
            (self.wide_data['health_expenditure'].notna())
        ].copy()

        # Filter real countries
        latest_data = latest_data[
            (latest_data['country_code'].str.len() == 3) |
            ((latest_data['country_code'].str.len() == 2) & ~latest_data['country_code'].str.contains('[0-9]', na=False))
        ]

        top_20 = latest_data.nlargest(20, 'health_expenditure')

        fig, ax = plt.subplots(figsize=(14, 10))
        bars = ax.barh(range(len(top_20)), top_20['health_expenditure'].values, color='#06A77D')
        ax.set_yticks(range(len(top_20)))
        ax.set_yticklabels(top_20['country_name'].values, fontsize=10)
        ax.set_xlabel('Health Expenditure (% of GDP)', fontsize=12)
        ax.set_title(f'Top 20 Countries - Health Expenditure ({latest_year})',
                     fontsize=15, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

        plt.tight_layout()
        output_file = self.output_dir / "04_health_expenditure_top20.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_military_comparison(self):
        """Chart 5: Military Expenditure Comparison"""
        logger.info("\n[5/12] Creating military expenditure comparison...")

        latest_year = self.wide_data['year'].max()
        latest_data = self.wide_data[
            (self.wide_data['year'] == latest_year) &
            (self.wide_data['military_expenditure'].notna())
        ].copy()

        # Filter real countries
        latest_data = latest_data[
            (latest_data['country_code'].str.len() == 3) |
            ((latest_data['country_code'].str.len() == 2) & ~latest_data['country_code'].str.contains('[0-9]', na=False))
        ]

        top_20 = latest_data.nlargest(20, 'military_expenditure')

        fig, ax = plt.subplots(figsize=(14, 10))
        bars = ax.barh(range(len(top_20)), top_20['military_expenditure'].values, color='#D62828')
        ax.set_yticks(range(len(top_20)))
        ax.set_yticklabels(top_20['country_name'].values, fontsize=10)
        ax.set_xlabel('Military Expenditure (% of GDP)', fontsize=12)
        ax.set_title(f'Top 20 Countries - Military Expenditure ({latest_year})',
                     fontsize=15, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='x')
        ax.invert_yaxis()

        plt.tight_layout()
        output_file = self.output_dir / "05_military_expenditure_top20.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_sectoral_breakdown(self):
        """Chart 6: Sectoral Expenditure Breakdown (Top 10 Countries)"""
        logger.info("\n[6/12] Creating sectoral breakdown chart...")

        latest_year = self.wide_data['year'].max()
        latest_data = self.wide_data[self.wide_data['year'] == latest_year].copy()

        # Get top 10 countries by total expenditure with all sector data
        latest_data = latest_data[
            (latest_data['gov_expenditure_gdp'].notna()) &
            (latest_data['education_expenditure'].notna()) &
            (latest_data['health_expenditure'].notna()) &
            (latest_data['military_expenditure'].notna())
        ]

        top_10 = latest_data.nlargest(10, 'gov_expenditure_gdp')

        fig, ax = plt.subplots(figsize=(14, 10))

        countries = top_10['country_name'].values
        edu = top_10['education_expenditure'].values
        health = top_10['health_expenditure'].values
        military = top_10['military_expenditure'].values

        x = np.arange(len(countries))
        width = 0.25

        bars1 = ax.bar(x - width, edu, width, label='Education', color='#F77F00')
        bars2 = ax.bar(x, health, width, label='Health', color='#06A77D')
        bars3 = ax.bar(x + width, military, width, label='Military', color='#D62828')

        ax.set_xlabel('Country', fontsize=12)
        ax.set_ylabel('Expenditure (% of GDP)', fontsize=12)
        ax.set_title(f'Sectoral Expenditure Breakdown - Top 10 Countries ({latest_year})',
                     fontsize=15, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(countries, rotation=45, ha='right', fontsize=10)
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        output_file = self.output_dir / "06_sectoral_expenditure_breakdown.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_expenditure_time_series_major_economies(self):
        """Chart 7: Expenditure Trends for Major Economies"""
        logger.info("\n[7/12] Creating major economies time series...")

        # Major economies
        major_economies = {
            'USA': 'United States',
            'CHN': 'China',
            'JPN': 'Japan',
            'DEU': 'Germany',
            'GBR': 'United Kingdom',
            'FRA': 'France',
            'IND': 'India',
            'BRA': 'Brazil'
        }

        fig, ax = plt.subplots(figsize=(16, 10))

        colors = plt.cm.tab10(np.linspace(0, 1, len(major_economies)))

        for (code, name), color in zip(major_economies.items(), colors):
            country_data = self.wide_data[self.wide_data['country_code'] == code].copy()
            if len(country_data) > 0:
                country_data = country_data.sort_values('year')
                ax.plot(country_data['year'], country_data['gov_expenditure_gdp'],
                       linewidth=2, label=name, color=color, marker='o', markersize=3, alpha=0.8)

        ax.set_title('Government Expenditure Trends - Major Economies (1960-2024)',
                     fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Government Expenditure (% of GDP)', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10, ncol=2)

        plt.tight_layout()
        output_file = self.output_dir / "07_major_economies_expenditure_trends.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def create_scatter_expenditure_vs_tax(self):
        """Chart 8: Government Expenditure vs Tax Revenue Scatter Plot"""
        logger.info("\n[8/12] Creating expenditure vs tax scatter plot...")

        # Load tax data if available
        tax_file = project_root() / "Output" / "Data" / "unified_international_tax_data.xlsx"
        if not tax_file.exists():
            logger.warning("  Tax data not found, skipping scatter plot...")
            return

        tax_data = pd.read_excel(tax_file)
        latest_year = min(self.wide_data['year'].max(), tax_data['year'].max())

        # Merge expenditure and tax data
        exp_latest = self.wide_data[self.wide_data['year'] == latest_year][
            ['country_code', 'country_name', 'gov_expenditure_gdp']
        ]
        tax_latest = tax_data[tax_data['year'] == latest_year][
            ['country_code', 'tax_revenue_pct_gdp']
        ]

        merged = exp_latest.merge(tax_latest, on='country_code', how='inner')
        merged = merged[(merged['gov_expenditure_gdp'].notna()) & (merged['tax_revenue_pct_gdp'].notna())]

        fig, ax = plt.subplots(figsize=(14, 10))

        scatter = ax.scatter(merged['tax_revenue_pct_gdp'], merged['gov_expenditure_gdp'],
                            s=100, alpha=0.6, c='#2E86AB', edgecolors='black', linewidth=0.5)

        # Add reference line (45 degree)
        max_val = max(merged['tax_revenue_pct_gdp'].max(), merged['gov_expenditure_gdp'].max())
        ax.plot([0, max_val], [0, max_val], 'r--', linewidth=1.5, alpha=0.5, label='Tax = Expenditure')

        ax.set_xlabel('Tax Revenue (% of GDP)', fontsize=12)
        ax.set_ylabel('Government Expenditure (% of GDP)', fontsize=12)
        ax.set_title(f'Government Expenditure vs Tax Revenue ({latest_year})',
                     fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        # Add annotations for extreme cases
        for _, row in merged.nlargest(5, 'gov_expenditure_gdp').iterrows():
            ax.annotate(row['country_name'],
                       (row['tax_revenue_pct_gdp'], row['gov_expenditure_gdp']),
                       fontsize=8, alpha=0.7)

        plt.tight_layout()
        output_file = self.output_dir / "08_expenditure_vs_tax_scatter.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"  ✅ Saved: {output_file.name}")
        self.charts_created += 1

    def generate_all_visualizations(self):
        """Generate all expenditure visualizations"""
        logger.info("\n" + "="*80)
        logger.info("Generating Expenditure Visualizations")
        logger.info("="*80 + "\n")

        self.create_global_expenditure_trend()
        self.create_top_bottom_countries()
        self.create_education_comparison()
        self.create_health_comparison()
        self.create_military_comparison()
        self.create_sectoral_breakdown()
        self.create_expenditure_time_series_major_economies()
        self.create_scatter_expenditure_vs_tax()

        logger.info("\n" + "="*80)
        logger.info(f"✅ Visualization Complete! Created {self.charts_created} charts")
        logger.info("="*80)
        logger.info(f"Charts saved to: {self.output_dir}")
        logger.info("\nAll charts are 300 DPI publication quality")


def main():
    logger.info("Government Expenditure Visualization")
    logger.info("Project: Gerhard - Fiscal Analysis\n")

    visualizer = ExpenditureVisualizer()

    if not visualizer.load_data():
        logger.error("Failed to load expenditure data. Exiting.")
        return

    visualizer.generate_all_visualizations()

    logger.info("\n✅ Visualization complete!")


if __name__ == "__main__":
    main()
