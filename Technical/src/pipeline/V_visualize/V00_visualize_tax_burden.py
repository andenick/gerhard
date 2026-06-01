"""
Pipeline: Visualize Tax Burden Distribution
Creates comprehensive visualizations of tax burden distribution.
Project: Gerhard
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for pipeline use
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V00",
    "name": "Visualize Tax Burden Distribution",
    "stage": "V",
    "description": "Creates PNG visualizations of tax burden distribution analysis.",
    "depends_on": ["A00"],
    "inputs": [
        {"path": "Output/Data/us_tax_distribution_by_income_percentile.xlsx", "required": True, "description": "US tax distribution by percentile"},
        {"path": "Output/Data/us_tax_distribution_by_income_quintile.xlsx", "required": False, "description": "US quintile data"},
        {"path": "Output/Data/us_tax_burden_by_tax_type.xlsx", "required": False, "description": "Tax burden by type"},
        {"path": "Output/Data/us_tax_distribution_historical_trends.xlsx", "required": False, "description": "Historical trends"},
        {"path": "Output/Data/analysis_us_tax_burden_distribution.xlsx", "required": False, "description": "US tax burden analysis"},
        {"path": "Output/Data/analysis_tax_progressivity.xlsx", "required": False, "description": "Tax progressivity analysis"},
        {"path": "Output/Data/analysis_international_tax_levels.xlsx", "required": False, "description": "International tax levels"},
    ],
    "outputs": [
        {"path": "Output/PDFs/01_tax_share_by_income_group.png", "description": "Tax share vs income share chart"},
        {"path": "Output/PDFs/02_effective_tax_rates_by_quintile.png", "description": "Effective tax rates chart"},
        {"path": "Output/PDFs/03_tax_burden_by_type.png", "description": "Tax burden by type chart"},
        {"path": "Output/PDFs/04_historical_trends.png", "description": "Historical trends chart"},
        {"path": "Output/PDFs/05_international_comparison.png", "description": "International comparison chart"},
        {"path": "Output/PDFs/06_income_redistribution.png", "description": "Income redistribution chart"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# Define paths
DATA_DIR = output_data_dir()
VIZ_DIR = output_pdfs_dir()


class TaxVisualization:
    """Creates visualizations for tax burden analysis"""

    def __init__(self):
        self.data = {}
        self.figs = []

    def load_data(self):
        """Load all analysis results"""
        logger.info("Loading analysis data for visualization...")

        datasets = {
            'us_percentile': 'us_tax_distribution_by_income_percentile.xlsx',
            'us_quintile': 'us_tax_distribution_by_income_quintile.xlsx',
            'us_tax_type': 'us_tax_burden_by_tax_type.xlsx',
            'us_historical': 'us_tax_distribution_historical_trends.xlsx',
            'us_analysis': 'analysis_us_tax_burden_distribution.xlsx',
            'progressivity': 'analysis_tax_progressivity.xlsx',
            'international': 'analysis_international_tax_levels.xlsx'
        }

        for name, filename in datasets.items():
            file_path = DATA_DIR / filename
            if file_path.exists():
                self.data[name] = pd.read_excel(file_path)
                logger.info(f"  Loaded {name}")

    def plot_tax_share_by_income_group(self):
        """Visualize tax share vs income share by percentile"""
        logger.info("Creating tax share visualization...")

        if 'us_percentile' not in self.data:
            return

        df = self.data['us_percentile']

        fig, ax = plt.subplots(figsize=(14, 8))

        # Prepare data
        groups = df['income_percentile']
        x = np.arange(len(groups))
        width = 0.35

        # Create bars
        bars1 = ax.bar(x - width/2, df['share_of_total_agi_percent'],
                      width, label='Share of Income', color='#3498db', alpha=0.8)
        bars2 = ax.bar(x + width/2, df['share_of_total_taxes_percent'],
                      width, label='Share of Taxes Paid', color='#e74c3c', alpha=0.8)

        # Formatting
        ax.set_xlabel('Income Group', fontweight='bold')
        ax.set_ylabel('Percentage (%)', fontweight='bold')
        ax.set_title('Who Pays the Taxes in the United States?\nIncome Share vs. Tax Share by Income Percentile (2021)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(groups, rotation=45, ha='right')
        ax.legend(frameon=True, shadow=True, fontsize=11)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        output_file = VIZ_DIR / "01_tax_share_by_income_group.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def plot_effective_tax_rates(self):
        """Visualize effective tax rates across income groups"""
        logger.info("Creating effective tax rates visualization...")

        if 'us_quintile' not in self.data:
            return

        df = self.data['us_quintile']

        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot
        groups = df['income_quintile']
        rates = df['average_federal_tax_rate_percent']

        bars = ax.barh(groups, rates, color='#2ecc71', alpha=0.8, edgecolor='black')

        # Formatting
        ax.set_xlabel('Average Federal Tax Rate (%)', fontweight='bold')
        ax.set_ylabel('Income Group', fontweight='bold')
        ax.set_title('Tax Progressivity in the United States\nAverage Federal Tax Rates by Income Quintile (2021)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(axis='x', alpha=0.3)

        # Add value labels
        for i, (bar, rate) in enumerate(zip(bars, rates)):
            ax.text(rate + 0.5, i, f'{rate:.1f}%', va='center', fontweight='bold')

        plt.tight_layout()
        output_file = VIZ_DIR / "02_effective_tax_rates_by_quintile.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def plot_tax_type_breakdown(self):
        """Visualize tax burden by type (stacked bars)"""
        logger.info("Creating tax type breakdown visualization...")

        if 'us_tax_type' not in self.data:
            return

        df = self.data['us_tax_type']

        fig, ax = plt.subplots(figsize=(14, 8))

        # Prepare data
        groups = df['income_group']
        individual = df['individual_income_tax_rate']
        payroll = df['payroll_tax_rate']
        corporate = df['corporate_income_tax_rate']
        other = df['excise_estate_other_tax_rate']

        x = np.arange(len(groups))
        width = 0.6

        # Create stacked bars
        p1 = ax.bar(x, individual, width, label='Individual Income Tax',
                   color='#3498db', alpha=0.9)
        p2 = ax.bar(x, payroll, width, bottom=individual,
                   label='Payroll Tax', color='#e74c3c', alpha=0.9)
        p3 = ax.bar(x, corporate, width,
                   bottom=individual+payroll,
                   label='Corporate Income Tax', color='#f39c12', alpha=0.9)
        p4 = ax.bar(x, other, width,
                   bottom=individual+payroll+corporate,
                   label='Excise, Estate & Other', color='#9b59b6', alpha=0.9)

        # Formatting
        ax.set_xlabel('Income Group', fontweight='bold')
        ax.set_ylabel('Tax Rate (%)', fontweight='bold')
        ax.set_title('Tax Burden Composition by Income Group\nBreakdown by Type of Tax (2021)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(groups, rotation=45, ha='right')
        ax.legend(loc='upper left', frameon=True, shadow=True)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=0.8)

        plt.tight_layout()
        output_file = VIZ_DIR / "03_tax_burden_by_type.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def plot_historical_trends(self):
        """Visualize historical trends in tax distribution"""
        logger.info("Creating historical trends visualization...")

        if 'us_historical' not in self.data:
            return

        df = self.data['us_historical']

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Tax share over time
        ax1.plot(df['year'], df['top_1_percent_tax_share'],
                marker='o', linewidth=2.5, markersize=8,
                color='#e74c3c', label='Top 1% Tax Share')
        ax1.set_xlabel('Year', fontweight='bold')
        ax1.set_ylabel('Share of Total Federal Taxes (%)', fontweight='bold')
        ax1.set_title('Top 1% Share of Federal Taxes Over Time\n1979-2021',
                     fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Add value labels
        for x, y in zip(df['year'], df['top_1_percent_tax_share']):
            ax1.text(x, y + 0.5, f'{y:.1f}%', ha='center', fontsize=9)

        # Plot 2: Tax rates over time
        ax2.plot(df['year'], df['top_1_percent_avg_tax_rate'],
                marker='s', linewidth=2.5, markersize=8,
                color='#3498db', label='Top 1% Avg Rate')
        ax2.plot(df['year'], df['lowest_quintile_avg_tax_rate'],
                marker='^', linewidth=2.5, markersize=8,
                color='#2ecc71', label='Bottom 20% Avg Rate')
        ax2.set_xlabel('Year', fontweight='bold')
        ax2.set_ylabel('Average Tax Rate (%)', fontweight='bold')
        ax2.set_title('Average Tax Rates by Income Group Over Time\n1979-2021',
                     fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        plt.tight_layout()
        output_file = VIZ_DIR / "04_historical_trends.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def plot_international_comparison(self):
        """Visualize international tax revenue comparison"""
        logger.info("Creating international comparison visualization...")

        if 'international' not in self.data:
            return

        df = self.data['international'].dropna(subset=['tax_revenue_pct_gdp'])

        # Top and bottom 20 countries
        top20 = df.nlargest(20, 'tax_revenue_pct_gdp')
        bottom20 = df.nsmallest(20, 'tax_revenue_pct_gdp')

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10))

        # Plot 1: Highest tax countries
        ax1.barh(range(len(top20)), top20['tax_revenue_pct_gdp'],
                color='#e74c3c', alpha=0.8)
        ax1.set_yticks(range(len(top20)))
        ax1.set_yticklabels(top20['country_name'], fontsize=9)
        ax1.set_xlabel('Tax Revenue (% of GDP)', fontweight='bold')
        ax1.set_title('Countries with Highest Tax Revenue\nTop 20 Countries',
                     fontsize=14, fontweight='bold')
        ax1.grid(axis='x', alpha=0.3)
        ax1.invert_yaxis()

        # Add value labels
        for i, v in enumerate(top20['tax_revenue_pct_gdp']):
            ax1.text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=8)

        # Plot 2: Lowest tax countries
        ax2.barh(range(len(bottom20)), bottom20['tax_revenue_pct_gdp'],
                color='#3498db', alpha=0.8)
        ax2.set_yticks(range(len(bottom20)))
        ax2.set_yticklabels(bottom20['country_name'], fontsize=9)
        ax2.set_xlabel('Tax Revenue (% of GDP)', fontweight='bold')
        ax2.set_title('Countries with Lowest Tax Revenue\nBottom 20 Countries',
                     fontsize=14, fontweight='bold')
        ax2.grid(axis='x', alpha=0.3)
        ax2.invert_yaxis()

        # Add value labels
        for i, v in enumerate(bottom20['tax_revenue_pct_gdp']):
            ax2.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=8)

        plt.tight_layout()
        output_file = VIZ_DIR / "05_international_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def plot_income_redistribution(self):
        """Visualize income redistribution effect"""
        logger.info("Creating income redistribution visualization...")

        if 'progressivity' not in self.data:
            return

        df = self.data['progressivity']
        # Filter to quintiles only (remove Top 10%, etc.)
        df = df[df['income_group'].str.contains('Quintile')]

        fig, ax = plt.subplots(figsize=(14, 8))

        groups = df['income_group']
        x = np.arange(len(groups))
        width = 0.35

        # Create bars
        bars1 = ax.bar(x - width/2, df['market_income_share'],
                      width, label='Before Tax & Transfers', color='#95a5a6', alpha=0.8)
        bars2 = ax.bar(x + width/2, df['after_tax_income_share'],
                      width, label='After Tax & Transfers', color='#27ae60', alpha=0.8)

        # Formatting
        ax.set_xlabel('Income Quintile', fontweight='bold')
        ax.set_ylabel('Share of Total Income (%)', fontweight='bold')
        ax.set_title('Effect of Tax & Transfer System on Income Distribution\nUnited States, 2021',
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(groups, rotation=45, ha='right')
        ax.legend(frameon=True, shadow=True, fontsize=11)
        ax.grid(axis='y', alpha=0.3)

        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}%', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        output_file = VIZ_DIR / "06_income_redistribution.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"Saved: {output_file.name}")
        self.figs.append(fig)

    def create_all_visualizations(self):
        """Create all visualizations"""
        logger.info("=" * 60)
        logger.info("Creating Tax Burden Visualizations")
        logger.info("=" * 60)

        self.load_data()

        self.plot_tax_share_by_income_group()
        self.plot_effective_tax_rates()
        self.plot_tax_type_breakdown()
        self.plot_historical_trends()
        self.plot_international_comparison()
        self.plot_income_redistribution()

        logger.info("\n" + "=" * 60)
        logger.info(f"Created {len(self.figs)} visualizations")
        logger.info(f"Saved to: {VIZ_DIR}")
        logger.info("=" * 60)

        # Close all figures to free memory
        plt.close('all')

        return self.figs


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    viz = TaxVisualization()
    figs = viz.create_all_visualizations()

    logger.info("\nVisualization files created:")
    for file in sorted(VIZ_DIR.glob("*.png")):
        logger.info(f"  - {file.name}")


if __name__ == "__main__":
    run()
