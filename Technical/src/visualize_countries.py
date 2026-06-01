"""
Country Visualization Script
Creates charts for individual countries
Project: Gerhard - Country by Country Expansion
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import json
from pathlib import Path
import sys

# Use non-interactive backend
matplotlib.use('Agg')

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils.logging_setup import setup_logging
from utils.paths import countries_dir

logger = setup_logging(__name__)

COUNTRIES_DIR = countries_dir()

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['font.size'] = 10


class CountryVisualizer:
    """Creates visualizations for individual countries"""

    def __init__(self, country_code, country_name, tier):
        self.country_code = country_code
        self.country_name = country_name
        self.tier = tier
        self.country_dir = COUNTRIES_DIR / country_code
        self.data = None
        self.charts_created = []

    def load_data(self):
        """Load country data"""
        data_file = self.country_dir / "Output" / "Data" / f"{self.country_code.lower()}_national_tax_data.xlsx"
        if data_file.exists():
            self.data = pd.read_excel(data_file)
            return True
        return False

    def create_time_series_chart(self):
        """Create main time series chart"""
        if self.data is None or len(self.data) == 0:
            return

        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(self.data['year'], self.data['tax_revenue_pct_gdp'],
                linewidth=2, color='#2C3E50', marker='o', markersize=4)

        ax.set_title(f'{self.country_name}: Tax Revenue as % of GDP\n{int(self.data["year"].min())}-{int(self.data["year"].max())}',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Tax Revenue (% of GDP)', fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add trend line if enough data
        if len(self.data) >= 5:
            z = np.polyfit(self.data['year'], self.data['tax_revenue_pct_gdp'], 1)
            p = np.poly1d(z)
            ax.plot(self.data['year'], p(self.data['year']),
                   "--", alpha=0.5, color='red', linewidth=1.5,
                   label=f'Trend Line')
            ax.legend()

        plt.tight_layout()

        output_file = self.country_dir / "Output" / "PDFs" / f"{self.country_code.lower()}_01_time_series.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        self.charts_created.append('time_series')
        logger.info(f"  Created time series chart")

    def create_decade_comparison(self):
        """Create decade comparison chart"""
        if self.data is None or len(self.data) < 10:
            return

        self.data['decade'] = (self.data['year'] // 10) * 10
        decade_avg = self.data.groupby('decade')['tax_revenue_pct_gdp'].mean().reset_index()

        if len(decade_avg) < 2:
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(decade_avg['decade'].astype(str) + 's',
                     decade_avg['tax_revenue_pct_gdp'],
                     color='#3498DB', edgecolor='black', linewidth=0.5)

        ax.set_title(f'{self.country_name}: Average Tax Revenue by Decade',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Decade', fontsize=12)
        ax.set_ylabel('Average Tax Revenue (% of GDP)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=9)

        plt.tight_layout()

        output_file = self.country_dir / "Output" / "PDFs" / f"{self.country_code.lower()}_02_decade_comparison.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        self.charts_created.append('decade_comparison')
        logger.info(f"  Created decade comparison chart")

    def create_summary_stats_visual(self):
        """Create summary statistics visual"""
        analysis_file = self.country_dir / "Technical" / "data" / "analysis_results.json"
        if not analysis_file.exists():
            return

        with open(analysis_file, 'r') as f:
            analysis = json.load(f)

        if 'summary_statistics' not in analysis:
            return

        stats = analysis['summary_statistics']

        fig, ax = plt.subplots(figsize=(10, 6))

        metrics = ['Mean', 'Median', 'Min', 'Max']
        values = [stats['mean'], stats['median'], stats['min'], stats['max']]
        colors = ['#3498DB', '#2ECC71', '#E74C3C', '#F39C12']

        bars = ax.bar(metrics, values, color=colors, edgecolor='black', linewidth=1)

        ax.set_title(f'{self.country_name}: Tax Revenue Statistics\n{stats["first_year"]}-{stats["last_year"]} ({stats["total_years"]} years)',
                     fontsize=14, fontweight='bold', pad=20)
        ax.set_ylabel('Tax Revenue (% of GDP)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2f}%',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.tight_layout()

        output_file = self.country_dir / "Output" / "PDFs" / f"{self.country_code.lower()}_03_statistics.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        self.charts_created.append('statistics')
        logger.info(f"  Created statistics chart")

    def create_tier1_charts(self):
        """Create additional charts for Tier 1 countries"""
        if self.tier != 1:
            return

        # Year-over-year change chart
        if len(self.data) >= 2:
            self.data = self.data.sort_values('year')
            self.data['yoy_change'] = self.data['tax_revenue_pct_gdp'].diff()

            fig, ax = plt.subplots(figsize=(12, 6))

            colors = ['green' if x >= 0 else 'red' for x in self.data['yoy_change']]
            ax.bar(self.data['year'], self.data['yoy_change'],
                  color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)

            ax.set_title(f'{self.country_name}: Year-over-Year Change in Tax Revenue',
                        fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('Year', fontsize=12)
            ax.set_ylabel('Change in Tax Revenue (pp)', fontsize=12)
            ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()

            output_file = self.country_dir / "Output" / "PDFs" / f"{self.country_code.lower()}_04_yoy_change.png"
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()

            self.charts_created.append('yoy_change')
            logger.info(f"  Created YoY change chart (Tier 1)")

    def visualize(self):
        """Create all visualizations for country"""
        logger.info(f"Creating visualizations for {self.country_name} ({self.country_code})")

        if not self.load_data():
            logger.warning(f"  No data available")
            return False

        # Create charts based on tier
        self.create_time_series_chart()
        self.create_decade_comparison()
        self.create_summary_stats_visual()

        if self.tier == 1:
            self.create_tier1_charts()

        # Update config
        config_file = self.country_dir / "Technical" / "data" / "config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)

        config['analysis']['visualizations_created'] = True
        config['status'] = 'visualized'

        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"  Created {len(self.charts_created)} visualizations")
        return True


class BulkCountryVisualizer:
    """Visualize multiple countries"""

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

    def visualize_tier(self, tier):
        """Visualize all countries in a specific tier"""
        logger.info("=" * 60)
        logger.info(f"Visualizing Tier {tier} Countries")
        logger.info("=" * 60)

        tier_countries = [c for c in self.countries if c['tier'] == tier]
        logger.info(f"Found {len(tier_countries)} Tier {tier} countries")

        visualized = 0
        for country in tier_countries:
            try:
                viz = CountryVisualizer(country['code'], country['name'], country['tier'])
                if viz.visualize():
                    visualized += 1
            except Exception as e:
                logger.error(f"Error visualizing {country['name']}: {e}")

        logger.info(f"\nCompleted visualizations for {visualized}/{len(tier_countries)} countries")
        return visualized


def main():
    logger.info("Country Visualization - Gerhard Project")

    visualizer = BulkCountryVisualizer()

    # Start with Tier 1 countries
    logger.info("\nStarting with Tier 1 (Comprehensive) countries...")
    visualizer.visualize_tier(1)

    logger.info("\nTier 1 visualizations complete!")
    logger.info("Next: Tier 2 and 3 visualizations, then report generation")


if __name__ == "__main__":
    main()
