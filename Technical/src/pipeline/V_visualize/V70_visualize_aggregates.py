"""
Pipeline: Visualize Aggregate Trends
Creates charts showing global fiscal trajectory, regional profiles, and income group convergence.
Project: Gerhard
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir, output_pdfs_dir
from utils.data_io import read_excel_safe

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V70",
    "name": "Visualize Aggregate Trends",
    "stage": "V",
    "description": "Creates PNG visualizations of global fiscal trajectory, regional profiles, and income group convergence.",
    "depends_on": ["A130"],
    "inputs": [
        {"path": "Output/Data/aggregates_panel.xlsx", "required": True, "description": "Regional and income group aggregates"},
    ],
    "outputs": [
        {"path": "Output/PDFs/aggregates_global_trajectory.png", "description": "Global weighted-mean tax, expenditure, balance"},
        {"path": "Output/PDFs/aggregates_regional_profiles.png", "description": "Regional profiles grouped bar"},
        {"path": "Output/PDFs/aggregates_income_group_convergence.png", "description": "Income group tax convergence"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")
    out_pdfs = output_pdfs_dir()
    out_data = output_data_dir()

    agg = read_excel_safe(out_data / 'aggregates_panel.xlsx')

    if agg.empty:
        logger.warning("Aggregates panel not found, skipping")
        return

    charts_created = 0

    # ── Chart 1: Global fiscal trajectory ───────────────────────────────
    try:
        g = agg[agg['aggregate_type'] == 'global'].copy()

        fig, ax = plt.subplots(figsize=(14, 7))
        # Variables live in different source panels
        var_map = {
            ('tax_revenue_pct_gdp', 'revenue_composition'): ('Tax Revenue', '#3498db'),
            ('total_expense_pct_gdp', 'expenditure_composition'): ('Expenditure', '#e74c3c'),
        }

        for (var, src), (label, color) in var_map.items():
            series = g[(g['variable'] == var) & (g['source_panel'] == src)].sort_values('year')
            series = series[(series['year'] >= 1990) & (series['year'] <= 2024)]
            if series.empty:
                continue
            metric = 'weighted_mean' if series['weighted_mean'].notna().any() else 'mean'
            ax.plot(series['year'], series[metric], marker='o', markersize=3,
                    linewidth=2, label=label, color=color)

        ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('% of GDP', fontweight='bold')
        ax.set_title('Global Fiscal Trajectory (1990-2024)\nGDP-weighted means',
                      fontsize=14, fontweight='bold', pad=15)
        ax.legend(frameon=True, shadow=True, fontsize=11)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'aggregates_global_trajectory.png', dpi=300, bbox_inches='tight')
        logger.info("Saved aggregates_global_trajectory.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 1 failed: {e}")

    # ── Chart 2: Regional profiles ──────────────────────────────────────
    try:
        r = agg[agg['aggregate_type'] == 'region'].copy()
        # Combine tax from revenue_composition, expenditure from expenditure_composition
        r_tax = r[(r['source_panel'] == 'revenue_composition') & (r['variable'] == 'tax_revenue_pct_gdp')]
        r_exp = r[(r['source_panel'] == 'expenditure_composition') & (r['variable'] == 'total_expense_pct_gdp')]
        # Use latest year per region
        r_tax_latest = r_tax.sort_values('year').groupby('aggregate_name').last().reset_index()
        r_exp_latest = r_exp.sort_values('year').groupby('aggregate_name').last().reset_index()

        vars_data = [
            (r_tax_latest, 'tax_revenue_pct_gdp', 'Tax Revenue', '#3498db'),
            (r_exp_latest, 'total_expense_pct_gdp', 'Expenditure', '#e74c3c'),
        ]

        regions = sorted(r_tax_latest['aggregate_name'].unique())
        if len(regions) > 0:
            fig, ax = plt.subplots(figsize=(14, 7))
            x = np.arange(len(regions))
            n_bars = len(vars_data)
            width = 0.3

            for i, (df_src, var, label, color) in enumerate(vars_data):
                vals = []
                for region in regions:
                    row = df_src[df_src['aggregate_name'] == region]
                    metric = 'weighted_mean' if row['weighted_mean'].notna().any() else 'mean'
                    vals.append(row[metric].values[0] if len(row) > 0 else 0)
                offset = (i - n_bars / 2 + 0.5) * width
                ax.bar(x + offset, vals, width, label=label, color=color, alpha=0.85)

            ax.set_xticks(x)
            ax.set_xticklabels([r[:20] for r in regions], rotation=45, ha='right', fontsize=9)
            ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
            ax.set_ylabel('% of GDP', fontweight='bold')
            ax.set_title('Fiscal Profiles by Region\n(Latest available year, GDP-weighted means)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.legend(frameon=True, shadow=True)
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'aggregates_regional_profiles.png', dpi=300, bbox_inches='tight')
            logger.info("Saved aggregates_regional_profiles.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 2 failed: {e}")

    # ── Chart 3: Income group convergence ───────────────────────────────
    try:
        ig = agg[(agg['aggregate_type'] == 'income_group') &
                 (agg['source_panel'] == 'revenue_composition') &
                 (agg['variable'] == 'tax_revenue_pct_gdp')].copy()

        if not ig.empty:
            fig, ax = plt.subplots(figsize=(14, 7))
            group_colors = {
                'High income': '#3498db',
                'Upper middle income': '#2ecc71',
                'Lower middle income': '#f39c12',
                'Low income': '#e74c3c',
            }

            for group_name in ig['aggregate_name'].unique():
                subset = ig[ig['aggregate_name'] == group_name].sort_values('year')
                color = group_colors.get(group_name, '#999999')
                metric = 'weighted_mean' if subset['weighted_mean'].notna().any() else 'mean'
                ax.plot(subset['year'], subset[metric], marker='o', markersize=2,
                        linewidth=1.8, label=group_name, color=color)

            ax.set_xlabel('Year', fontweight='bold')
            ax.set_ylabel('Tax Revenue (% of GDP)', fontweight='bold')
            ax.set_title('Tax Revenue by Income Group Over Time\nConvergence or Divergence?',
                          fontsize=14, fontweight='bold', pad=15)
            ax.legend(frameon=True, shadow=True, fontsize=10)
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'aggregates_income_group_convergence.png', dpi=300, bbox_inches='tight')
            logger.info("Saved aggregates_income_group_convergence.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 3 failed: {e}")

    logger.info(f"[V70] Complete: {charts_created}/3 charts created")
    plt.close('all')


if __name__ == "__main__":
    run()
