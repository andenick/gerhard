"""
Country Fiscal Report Visualization Module
Generates standardized charts for individual country fiscal reports

Part of Gerhard - Global Fiscal Analysis Platform
Publication-quality output (300 DPI)
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

class CountryFiscalVisualizer:
    """Generate all visualizations for a country fiscal report"""

    def __init__(self, country_code, country_name, output_dir):
        """
        Initialize visualizer

        Args:
            country_code: ISO alpha-2 code
            country_name: Full country name
            output_dir: Directory to save charts
        """
        self.country_code = country_code
        self.country_name = country_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_tax_revenue_trend(self, tax_data):
        """
        Chart 1: Tax Revenue Trend Over Time

        Args:
            tax_data: DataFrame with columns: year, tax_revenue_pct_gdp
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot trend
        ax.plot(tax_data['year'], tax_data['tax_revenue_pct_gdp'],
                linewidth=2.5, color='#2c3e50', marker='o', markersize=4)

        # Add trend line
        z = np.polyfit(tax_data['year'], tax_data['tax_revenue_pct_gdp'], 1)
        p = np.poly1d(z)
        ax.plot(tax_data['year'], p(tax_data['year']),
                "--", color='#e74c3c', linewidth=2, alpha=0.7, label='Trend')

        # Formatting
        ax.set_xlabel('Year', fontweight='bold', fontsize=12)
        ax.set_ylabel('Tax Revenue (% of GDP)', fontweight='bold', fontsize=12)
        ax.set_title(f'{self.country_name} - Tax Revenue Over Time',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # Add latest value annotation
        latest_year = tax_data['year'].iloc[-1]
        latest_value = tax_data['tax_revenue_pct_gdp'].iloc[-1]
        ax.annotate(f'{latest_value:.1f}%',
                   xy=(latest_year, latest_value),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=11, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3))

        plt.tight_layout()
        plt.savefig(self.output_dir / '01_tax_revenue_trend.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '01_tax_revenue_trend.png')

    def create_expenditure_by_sector(self, exp_data_latest):
        """
        Chart 2: Expenditure by Sector (Latest Year)

        Args:
            exp_data_latest: Dict with sector names and values
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Filter out null values
        sectors = {k: v for k, v in exp_data_latest.items() if v is not None and v > 0}

        if not sectors:
            # No data available
            fig.text(0.5, 0.5, 'No expenditure data available',
                    ha='center', va='center', fontsize=16)
        else:
            # Bar chart
            names = list(sectors.keys())
            values = list(sectors.values())
            colors = plt.cm.Set3(range(len(names)))

            ax1.barh(names, values, color=colors)
            ax1.set_xlabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
            ax1.set_title(f'{self.country_name} - Expenditure by Sector\n(Latest Year)',
                         fontsize=14, fontweight='bold', pad=20)
            ax1.grid(True, alpha=0.3, axis='x')

            # Add value labels
            for i, v in enumerate(values):
                ax1.text(v + 0.1, i, f'{v:.2f}%', va='center', fontweight='bold')

            # Pie chart
            ax2.pie(values, labels=names, autopct='%1.1f%%', startangle=90, colors=colors)
            ax2.set_title(f'Sectoral Distribution\n(% of Total Measured)',
                         fontsize=14, fontweight='bold', pad=20)

        plt.tight_layout()
        plt.savefig(self.output_dir / '02_expenditure_by_sector.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '02_expenditure_by_sector.png')

    def create_sectoral_trends(self, exp_data):
        """
        Chart 3: Trends for Major Expenditure Sectors

        Args:
            exp_data: DataFrame with columns: year, education_gdp, health_gdp, military_gdp, rd_gdp
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Plot each sector
        sectors = {
            'education_gdp': ('Education', '#3498db'),
            'health_govt_gdp': ('Health', '#2ecc71'),
            'military_gdp': ('Military', '#e74c3c'),
            'rd_gdp': ('R&D', '#9b59b6')
        }

        plotted = False
        for col, (label, color) in sectors.items():
            if col in exp_data.columns:
                # Filter out nulls
                data = exp_data[['year', col]].dropna()
                if len(data) > 0:
                    ax.plot(data['year'], data[col],
                           linewidth=2.5, marker='o', markersize=4,
                           label=label, color=color)
                    plotted = True

        if plotted:
            ax.set_xlabel('Year', fontweight='bold', fontsize=12)
            ax.set_ylabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
            ax.set_title(f'{self.country_name} - Sectoral Expenditure Trends',
                        fontsize=16, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.3)
            ax.legend(loc='best', fontsize=11)
        else:
            ax.text(0.5, 0.5, 'Insufficient data for trend analysis',
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)

        plt.tight_layout()
        plt.savefig(self.output_dir / '03_sectoral_trends.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '03_sectoral_trends.png')

    def create_fiscal_balance(self, tax_data, exp_data):
        """
        Chart 4: Revenue vs Expenditure (Fiscal Balance)

        Args:
            tax_data: DataFrame with year, tax_revenue_pct_gdp
            exp_data: DataFrame with year and total expenditure estimate
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Merge on year
        merged = pd.merge(tax_data, exp_data, on='year', how='outer').sort_values('year')

        # Calculate total measured expenditure (sum of available sectors)
        exp_cols = [c for c in exp_data.columns if c != 'year' and c.endswith('_gdp')]
        merged['total_exp_measured'] = merged[exp_cols].sum(axis=1, skipna=True)

        # Plot
        if 'tax_revenue_pct_gdp' in merged.columns:
            ax.plot(merged['year'], merged['tax_revenue_pct_gdp'],
                   linewidth=2.5, marker='o', markersize=4,
                   label='Tax Revenue', color='#27ae60')

        if 'total_exp_measured' in merged.columns and merged['total_exp_measured'].notna().any():
            ax.plot(merged['year'], merged['total_exp_measured'],
                   linewidth=2.5, marker='s', markersize=4,
                   label='Measured Expenditure', color='#e74c3c')

            # Fill area between
            if 'tax_revenue_pct_gdp' in merged.columns:
                ax.fill_between(merged['year'],
                               merged['tax_revenue_pct_gdp'],
                               merged['total_exp_measured'],
                               where=(merged['tax_revenue_pct_gdp'] >= merged['total_exp_measured']),
                               alpha=0.3, color='green', label='Surplus (measured)')
                ax.fill_between(merged['year'],
                               merged['tax_revenue_pct_gdp'],
                               merged['total_exp_measured'],
                               where=(merged['tax_revenue_pct_gdp'] < merged['total_exp_measured']),
                               alpha=0.3, color='red', label='Deficit (measured)')

        ax.set_xlabel('Year', fontweight='bold', fontsize=12)
        ax.set_ylabel('% of GDP', fontweight='bold', fontsize=12)
        ax.set_title(f'{self.country_name} - Fiscal Balance Analysis\n(Tax Revenue vs Measured Expenditure)',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=11)

        # Add note about measured expenditure
        ax.text(0.5, 0.02,
               'Note: Measured expenditure includes only sectors with available data (typically 20-40% of total government spending)',
               ha='center', transform=ax.transAxes, fontsize=9, style='italic')

        plt.tight_layout()
        plt.savefig(self.output_dir / '04_fiscal_balance.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '04_fiscal_balance.png')

    def create_regional_comparison(self, country_value, regional_data, metric_name, region_name):
        """
        Chart 5: Comparison to Regional Peers

        Args:
            country_value: This country's value
            regional_data: Dict of {country_name: value} for region
            metric_name: Name of metric (e.g., "Tax Revenue")
            region_name: Name of region
        """
        fig, ax = plt.subplots(figsize=(14, 10))

        # Sort by value
        sorted_countries = sorted(regional_data.items(), key=lambda x: x[1], reverse=True)
        countries = [c[0] for c in sorted_countries][:20]  # Top 20
        values = [c[1] for c in sorted_countries][:20]

        # Highlight this country
        colors = ['#e74c3c' if c == self.country_name else '#3498db' for c in countries]

        ax.barh(countries, values, color=colors)
        ax.set_xlabel(f'{metric_name} (% of GDP)', fontweight='bold', fontsize=12)
        ax.set_title(f'{self.country_name} - Regional Comparison\n{metric_name} in {region_name}',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, v in enumerate(values):
            ax.text(v + 0.2, i, f'{v:.1f}%', va='center', fontsize=10)

        # Add rank
        try:
            rank = countries.index(self.country_name) + 1
            ax.text(0.02, 0.98, f'{self.country_name} Rank: #{rank} of {len(regional_data)}',
                   transform=ax.transAxes, fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
                   verticalalignment='top')
        except ValueError:
            pass

        plt.tight_layout()
        plt.savefig(self.output_dir / '05_regional_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '05_regional_comparison.png')

    def create_income_level_comparison(self, country_value, income_data, metric_name, income_level):
        """
        Chart 6: Comparison to Income-Level Peers

        Args:
            country_value: This country's value
            income_data: Dict of {country_name: value} for income level
            metric_name: Name of metric
            income_level: Income level category
        """
        fig, ax = plt.subplots(figsize=(14, 10))

        # Sort by value
        sorted_countries = sorted(income_data.items(), key=lambda x: x[1], reverse=True)
        countries = [c[0] for c in sorted_countries][:20]  # Top 20
        values = [c[1] for c in sorted_countries][:20]

        # Highlight this country
        colors = ['#e74c3c' if c == self.country_name else '#2ecc71' for c in countries]

        ax.barh(countries, values, color=colors)
        ax.set_xlabel(f'{metric_name} (% of GDP)', fontweight='bold', fontsize=12)
        ax.set_title(f'{self.country_name} - Income-Level Comparison\n{metric_name} in {income_level} Countries',
                    fontsize=16, fontweight='bold', pad=20)
        ax.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, v in enumerate(values):
            ax.text(v + 0.2, i, f'{v:.1f}%', va='center', fontsize=10)

        # Add rank
        try:
            rank = countries.index(self.country_name) + 1
            ax.text(0.02, 0.98, f'{self.country_name} Rank: #{rank} of {len(income_data)}',
                   transform=ax.transAxes, fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.5),
                   verticalalignment='top')
        except ValueError:
            pass

        plt.tight_layout()
        plt.savefig(self.output_dir / '06_income_level_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '06_income_level_comparison.png')

    def create_expenditure_evolution(self, exp_data):
        """
        Chart 7: Expenditure Composition Evolution (Area Chart)

        Args:
            exp_data: DataFrame with year and sector columns
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Prepare data
        sectors = {
            'education_gdp': 'Education',
            'health_govt_gdp': 'Health',
            'military_gdp': 'Military',
            'rd_gdp': 'R&D'
        }

        plot_data = exp_data[['year'] + [c for c in sectors.keys() if c in exp_data.columns]].copy()
        plot_data = plot_data.dropna(subset=['year']).sort_values('year')

        # Fill NaNs with 0 for stacking
        for col in sectors.keys():
            if col in plot_data.columns:
                plot_data[col] = plot_data[col].fillna(0)

        if len(plot_data) > 0:
            # Stacked area plot
            available_sectors = [sectors[c] for c in sectors.keys() if c in plot_data.columns]
            ax.stackplot(plot_data['year'],
                        *[plot_data[c] for c in sectors.keys() if c in plot_data.columns],
                        labels=available_sectors,
                        alpha=0.7)

            ax.set_xlabel('Year', fontweight='bold', fontsize=12)
            ax.set_ylabel('Expenditure (% of GDP)', fontweight='bold', fontsize=12)
            ax.set_title(f'{self.country_name} - Expenditure Composition Evolution',
                        fontsize=16, fontweight='bold', pad=20)
            ax.legend(loc='upper left', fontsize=11)
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Insufficient data for evolution analysis',
                   ha='center', va='center', transform=ax.transAxes, fontsize=14)

        plt.tight_layout()
        plt.savefig(self.output_dir / '07_expenditure_evolution.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '07_expenditure_evolution.png')

    def create_key_metrics_dashboard(self, metrics):
        """
        Chart 8: Key Fiscal Metrics Dashboard

        Args:
            metrics: Dict with key metrics to display
        """
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(3, 3, hspace=0.4, wspace=0.3)

        # Title
        fig.suptitle(f'{self.country_name} - Key Fiscal Metrics Dashboard',
                    fontsize=18, fontweight='bold', y=0.98)

        # Define metrics to display
        metric_positions = [
            ('Tax Revenue\n(% GDP)', metrics.get('tax_revenue', 'N/A'), (0, 0)),
            ('Education\n(% GDP)', metrics.get('education', 'N/A'), (0, 1)),
            ('Health\n(% GDP)', metrics.get('health', 'N/A'), (0, 2)),
            ('Military\n(% GDP)', metrics.get('military', 'N/A'), (1, 0)),
            ('R&D\n(% GDP)', metrics.get('rd', 'N/A'), (1, 1)),
            ('Data Coverage\n(years)', metrics.get('coverage_years', 'N/A'), (1, 2)),
            ('Tier', metrics.get('tier', 'N/A'), (2, 0)),
            ('Region', metrics.get('region', 'N/A'), (2, 1), True),  # Text instead of number
            ('Income Level', metrics.get('income_level', 'N/A'), (2, 2), True)
        ]

        for item in metric_positions:
            if len(item) == 4:
                label, value, pos, is_text = item
            else:
                label, value, pos = item
                is_text = False

            ax = fig.add_subplot(gs[pos[0], pos[1]])
            ax.axis('off')

            # Draw box
            box = plt.Rectangle((0.1, 0.1), 0.8, 0.8, fill=True,
                               facecolor='#ecf0f1', edgecolor='#34495e', linewidth=2)
            ax.add_patch(box)

            # Add label
            ax.text(0.5, 0.7, label, ha='center', va='center',
                   fontsize=12, fontweight='bold', transform=ax.transAxes)

            # Add value
            if is_text or value == 'N/A':
                value_str = str(value)
                fontsize = 14 if len(value_str) < 15 else 11
            else:
                value_str = f'{value:.1f}%' if isinstance(value, (int, float)) else str(value)
                fontsize = 18

            ax.text(0.5, 0.3, value_str, ha='center', va='center',
                   fontsize=fontsize, fontweight='bold', transform=ax.transAxes,
                   color='#2c3e50')

        plt.savefig(self.output_dir / '08_key_metrics_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()

        return str(self.output_dir / '08_key_metrics_dashboard.png')

    def generate_all_charts(self, tax_data, exp_data, comparison_data, metrics):
        """
        Generate all 8 charts for a country report

        Args:
            tax_data: DataFrame with tax revenue time series
            exp_data: DataFrame with expenditure time series
            comparison_data: Dict with regional and income-level comparison data
            metrics: Dict with key metrics for dashboard

        Returns:
            List of paths to generated charts
        """
        charts = []

        print(f"  Generating charts for {self.country_name}...")

        # Chart 1: Tax Revenue Trend
        if tax_data is not None and len(tax_data) > 0:
            charts.append(self.create_tax_revenue_trend(tax_data))
            print("    [OK] Tax revenue trend")

        # Chart 2: Expenditure by Sector
        if exp_data is not None and len(exp_data) > 0:
            latest = exp_data.iloc[-1]
            exp_dict = {
                'Education': latest.get('education_gdp'),
                'Health': latest.get('health_govt_gdp'),
                'Military': latest.get('military_gdp'),
                'R&D': latest.get('rd_gdp')
            }
            charts.append(self.create_expenditure_by_sector(exp_dict))
            print("    [OK] Expenditure by sector")

        # Chart 3: Sectoral Trends
        if exp_data is not None and len(exp_data) > 0:
            charts.append(self.create_sectoral_trends(exp_data))
            print("    [OK] Sectoral trends")

        # Chart 4: Fiscal Balance
        if tax_data is not None and exp_data is not None:
            charts.append(self.create_fiscal_balance(tax_data, exp_data))
            print("    [OK] Fiscal balance")

        # Chart 5: Regional Comparison
        if comparison_data.get('regional'):
            charts.append(self.create_regional_comparison(
                metrics.get('tax_revenue'),
                comparison_data['regional'],
                'Tax Revenue',
                metrics.get('region', 'Region')
            ))
            print("    [OK] Regional comparison")

        # Chart 6: Income-Level Comparison
        if comparison_data.get('income_level'):
            charts.append(self.create_income_level_comparison(
                metrics.get('tax_revenue'),
                comparison_data['income_level'],
                'Tax Revenue',
                metrics.get('income_level', 'Income Level')
            ))
            print("    [OK] Income-level comparison")

        # Chart 7: Expenditure Evolution
        if exp_data is not None and len(exp_data) > 0:
            charts.append(self.create_expenditure_evolution(exp_data))
            print("    [OK] Expenditure evolution")

        # Chart 8: Key Metrics Dashboard
        charts.append(self.create_key_metrics_dashboard(metrics))
        print("    [OK] Key metrics dashboard")

        return charts
