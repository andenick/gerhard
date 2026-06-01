"""
Create Visualizations for US DINA Distributional Data
Generate charts showing income and wealth inequality trends

Project: Gerhard - US DINA Visualization
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import countries_dir, ensure_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

US_DATA = countries_dir() / "US" / "Output" / "Data"
US_CHARTS = ensure_dir(countries_dir() / "US" / "Output" / "Charts")

# Set style
plt.style.use('seaborn-v0_8-darkgrid')


class DINAVisualizer:
    """Create DINA visualizations"""

    def __init__(self):
        self.data_file = US_DATA / "us_top_income_shares.xlsx"
        self.full_data_file = US_DATA / "us_dina_distributional_data.xlsx"

    def plot_top_income_shares_pretax(self):
        """Plot top income shares (pre-tax) over time"""
        logger.info("Creating Top Income Shares (Pre-Tax) chart...")

        # Read data
        df = pd.read_excel(self.data_file, sheet_name='PreTax')

        # Drop NaN rows
        df = df.dropna()

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot lines
        ax.plot(df['Year'], df['Top 10%'] * 100, label='Top 10%', linewidth=2.5, color='#e74c3c')
        ax.plot(df['Year'], df['Top 1%'] * 100, label='Top 1%', linewidth=2.5, color='#3498db')
        ax.plot(df['Year'], df['Top 0.1%'] * 100, label='Top 0.1%', linewidth=2.5, color='#2ecc71')

        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Share of Total Pre-Tax Income (%)', fontsize=12, fontweight='bold')
        ax.set_title('Top Income Shares in the United States (1913-2019)\nPre-Tax National Income',
                     fontsize=14, fontweight='bold', pad=20)

        ax.legend(loc='best', fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3)

        # Add reference lines for major events
        ax.axvline(1929, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(1929, ax.get_ylim()[1] * 0.95, 'Great\nDepression',
                fontsize=9, ha='center', va='top', color='gray')

        ax.axvline(1945, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(1945, ax.get_ylim()[1] * 0.95, 'WWII\nEnds',
                fontsize=9, ha='center', va='top', color='gray')

        ax.axvline(1980, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(1980, ax.get_ylim()[1] * 0.95, 'Reagan\nEra',
                fontsize=9, ha='center', va='top', color='gray')

        plt.tight_layout()

        # Save
        output_file = US_CHARTS / "us_top_income_shares_pretax.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✅ Saved: {output_file.name}")

        plt.close()

        return output_file

    def plot_pretax_vs_posttax(self):
        """Compare pre-tax vs post-tax top 1% share"""
        logger.info("Creating Pre-Tax vs Post-Tax comparison chart...")

        # Read data
        pretax_df = pd.read_excel(self.data_file, sheet_name='PreTax')
        posttax_df = pd.read_excel(self.data_file, sheet_name='PostTax')

        # Drop NaN
        pretax_df = pretax_df.dropna()
        posttax_df = posttax_df.dropna()

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot lines
        ax.plot(pretax_df['Year'], pretax_df['Top 1%'] * 100,
                label='Top 1% Pre-Tax Income Share', linewidth=2.5, color='#e74c3c')
        ax.plot(posttax_df['Year'], posttax_df['Top 1%'] * 100,
                label='Top 1% Post-Tax Income Share', linewidth=2.5, color='#3498db')

        # Calculate and plot redistribution (difference)
        merged = pretax_df.merge(posttax_df, on='Year', suffixes=('_pre', '_post'))
        redistribution = (merged['Top 1%_pre'] - merged['Top 1%_post']) * 100

        ax2 = ax.twinx()
        ax2.fill_between(merged['Year'], 0, redistribution,
                         alpha=0.3, color='#95a5a6', label='Tax Redistribution')
        ax2.set_ylabel('Redistribution from Top 1% (% points)', fontsize=11, fontweight='bold')
        ax2.set_ylim(0, max(redistribution) * 1.5)

        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Share of Total Income (%)', fontsize=12, fontweight='bold')
        ax.set_title('Tax Progressivity: Pre-Tax vs Post-Tax Top 1% Income Share\nUnited States (1913-2019)',
                     fontsize=14, fontweight='bold', pad=20)

        # Combine legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=11, framealpha=0.9)

        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save
        output_file = US_CHARTS / "us_tax_progressivity.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✅ Saved: {output_file.name}")

        plt.close()

        return output_file

    def plot_wealth_concentration(self):
        """Plot wealth concentration over time"""
        logger.info("Creating Wealth Concentration chart...")

        # Read data
        df = pd.read_excel(self.full_data_file, sheet_name='TE1')

        # Drop NaN rows
        df = df.dropna()

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot lines
        ax.plot(df['Year'], df['Top 10%'] * 100, label='Top 10%', linewidth=2.5, color='#e74c3c')
        ax.plot(df['Year'], df['Top 1%'] * 100, label='Top 1%', linewidth=2.5, color='#3498db')

        if 'Top 0.1%' in df.columns:
            ax.plot(df['Year'], df['Top 0.1%'] * 100, label='Top 0.1%', linewidth=2.5, color='#2ecc71')

        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Share of Total Wealth (%)', fontsize=12, fontweight='bold')
        ax.set_title('Wealth Concentration in the United States (1913-2019)\nShare of Total Household Wealth',
                     fontsize=14, fontweight='bold', pad=20)

        ax.legend(loc='best', fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # Save
        output_file = US_CHARTS / "us_wealth_concentration.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✅ Saved: {output_file.name}")

        plt.close()

        return output_file

    def plot_income_composition(self):
        """Plot income vs wealth shares comparison"""
        logger.info("Creating Income vs Wealth comparison chart...")

        # Read data
        income_df = pd.read_excel(self.data_file, sheet_name='PreTax')
        wealth_df = pd.read_excel(self.full_data_file, sheet_name='TE1')

        # Drop NaN
        income_df = income_df.dropna()
        wealth_df = wealth_df.dropna()

        # Create figure
        fig, ax = plt.subplots(figsize=(12, 7))

        # Plot Top 1% income and wealth
        ax.plot(income_df['Year'], income_df['Top 1%'] * 100,
                label='Top 1% Income Share', linewidth=2.5, color='#e74c3c', linestyle='-')
        ax.plot(wealth_df['Year'], wealth_df['Top 1%'] * 100,
                label='Top 1% Wealth Share', linewidth=2.5, color='#3498db', linestyle='--')

        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Share of Total (%)', fontsize=12, fontweight='bold')
        ax.set_title('Income vs Wealth Concentration: Top 1% in the United States\n(1913-2019)',
                     fontsize=14, fontweight='bold', pad=20)

        ax.legend(loc='best', fontsize=11, framealpha=0.9)
        ax.grid(True, alpha=0.3)

        # Add note
        ax.text(0.02, 0.02, 'Note: Wealth is always more concentrated than income',
                transform=ax.transAxes, fontsize=9, style='italic',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()

        # Save
        output_file = US_CHARTS / "us_income_vs_wealth.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✅ Saved: {output_file.name}")

        plt.close()

        return output_file

    def create_summary_stats(self):
        """Create summary statistics table"""
        logger.info("Creating summary statistics...")

        # Read data
        pretax_df = pd.read_excel(self.data_file, sheet_name='PreTax')
        posttax_df = pd.read_excel(self.data_file, sheet_name='PostTax')
        wealth_df = pd.read_excel(self.full_data_file, sheet_name='TE1')

        # Get latest year (before NaN)
        pretax_latest = pretax_df.dropna().iloc[-1]
        posttax_latest = posttax_df.dropna().iloc[-1]
        wealth_latest = wealth_df.dropna().iloc[-1]

        # Get 1980 for comparison
        pretax_1980 = pretax_df[pretax_df['Year'] == 1980].iloc[0]
        pretax_1950 = pretax_df[pretax_df['Year'] == 1950].iloc[0]

        summary = {
            'Latest Year': int(pretax_latest['Year']),
            'Pre-Tax Top 10%': f"{pretax_latest['Top 10%'] * 100:.1f}%",
            'Pre-Tax Top 1%': f"{pretax_latest['Top 1%'] * 100:.1f}%",
            'Pre-Tax Top 0.1%': f"{pretax_latest['Top 0.1%'] * 100:.1f}%",
            'Post-Tax Top 1%': f"{posttax_latest['Top 1%'] * 100:.1f}%",
            'Wealth Top 1%': f"{wealth_latest['Top 1%'] * 100:.1f}%",
            'Tax Redistribution (Top 1%)': f"{(pretax_latest['Top 1%'] - posttax_latest['Top 1%']) * 100:.1f}%",
            '': '',
            'Change since 1980': '',
            'Top 1% Income (1980)': f"{pretax_1980['Top 1%'] * 100:.1f}%",
            'Top 1% Income (Latest)': f"{pretax_latest['Top 1%'] * 100:.1f}%",
            'Increase': f"+{(pretax_latest['Top 1%'] - pretax_1980['Top 1%']) * 100:.1f} percentage points",
            '  ': '',
            'Change since 1950': '',
            'Top 1% Income (1950)': f"{pretax_1950['Top 1%'] * 100:.1f}%",
            'Relative to 1950': f"{(pretax_latest['Top 1%'] / pretax_1950['Top 1%'] - 1) * 100:.0f}% higher",
        }

        # Create DataFrame
        summary_df = pd.DataFrame(list(summary.items()), columns=['Metric', 'Value'])

        # Save
        output_file = US_DATA / "us_dina_summary_stats.xlsx"
        write_single_sheet_excel(summary_df, output_file, sheet_name='Summary_Stats')
        logger.info(f"  ✅ Saved: {output_file.name}")

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("US DINA Summary Statistics")
        logger.info("=" * 60)
        for metric, value in summary.items():
            if value:
                logger.info(f"  {metric}: {value}")
        logger.info("=" * 60)

        return summary_df

    def run(self):
        """Create all visualizations"""
        logger.info("🇺🇸 US DINA Visualization")
        logger.info("=" * 60)
        logger.info("")

        # Create charts
        self.plot_top_income_shares_pretax()
        self.plot_pretax_vs_posttax()
        self.plot_wealth_concentration()
        self.plot_income_composition()

        # Create summary stats
        self.create_summary_stats()

        logger.info("\n" + "=" * 60)
        logger.info("✅ All Visualizations Created!")
        logger.info("=" * 60)
        logger.info(f"Charts saved to: {US_CHARTS}")
        logger.info(f"Files created:")
        for chart_file in US_CHARTS.glob("us_*.png"):
            logger.info(f"  - {chart_file.name}")
        logger.info("")


def main():
    visualizer = DINAVisualizer()
    visualizer.run()


if __name__ == "__main__":
    main()
