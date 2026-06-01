"""
Pipeline: Visualize Exchange Rates and Inflation
Creates charts showing inflation-tax linkage and currency crisis episodes.
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
    "id": "V65",
    "name": "Visualize Exchange Rates",
    "stage": "V",
    "description": "Creates PNG visualizations of inflation-tax linkage and currency crisis frequency.",
    "depends_on": ["A115"],
    "inputs": [
        {"path": "Output/Data/exchange_rate_panel.xlsx", "required": True, "description": "Exchange rate, REER, inflation panel"},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True, "description": "Master panel with tax, income_group"},
    ],
    "outputs": [
        {"path": "Output/PDFs/fx_inflation_vs_tax.png", "description": "Inflation vs tax change scatter"},
        {"path": "Output/PDFs/fx_currency_crises_by_decade.png", "description": "Currency crises by decade bar chart"},
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

    fx = read_excel_safe(out_data / 'exchange_rate_panel.xlsx')
    master = read_excel_safe(out_data / 'master_fiscal_panel.xlsx')

    if fx.empty or master.empty:
        logger.warning("Required data not found, skipping")
        return

    charts_created = 0

    # ── Chart 1: Inflation vs tax change ────────────────────────────────
    try:
        # Compute YoY tax change from master
        m = master[['country_code', 'year', 'tax_revenue_pct_gdp', 'income_group']].dropna(
            subset=['tax_revenue_pct_gdp']).copy()
        m = m.sort_values(['country_code', 'year'])
        m['tax_change'] = m.groupby('country_code')['tax_revenue_pct_gdp'].diff()

        # Merge inflation
        fx_inf = fx[['country_code', 'year', 'inflation_pct']].dropna(subset=['inflation_pct'])
        merged = m.merge(fx_inf, on=['country_code', 'year'], how='inner')
        merged = merged.dropna(subset=['tax_change', 'inflation_pct'])

        # Clamp extremes for readability
        merged = merged[(merged['inflation_pct'].abs() < 100) & (merged['tax_change'].abs() < 10)]

        if len(merged) > 10:
            fig, ax = plt.subplots(figsize=(12, 9))

            ig_groups = merged['income_group'].fillna('Unknown').unique()
            palette = sns.color_palette('Set2', len(ig_groups))
            ig_colors = dict(zip(ig_groups, palette))

            for ig in ig_groups:
                subset = merged[merged['income_group'].fillna('Unknown') == ig]
                ax.scatter(subset['inflation_pct'], subset['tax_change'],
                           c=[ig_colors[ig]], label=ig, alpha=0.3, s=15, edgecolors='none')

            ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
            ax.axvline(0, color='black', linewidth=0.5, alpha=0.5)
            ax.set_xlabel('Inflation (%)', fontweight='bold')
            ax.set_ylabel('YoY Change in Tax Revenue (pp of GDP)', fontweight='bold')
            ax.set_title('Inflation vs Year-over-Year Tax Revenue Change\n(Colored by income group)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.legend(fontsize=8, frameon=True, loc='upper right')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'fx_inflation_vs_tax.png', dpi=300, bbox_inches='tight')
            logger.info("Saved fx_inflation_vs_tax.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 1 failed: {e}")

    # ── Chart 2: Currency crisis timeline by decade ─────────────────────
    try:
        # Crisis = REER drop > 15% in a single year
        crisis = fx.dropna(subset=['reer_change_pct']).copy()
        crisis['is_crisis'] = crisis['reer_change_pct'] < -15
        crisis_events = crisis[crisis['is_crisis']].copy()

        if len(crisis_events) > 0:
            crisis_events['decade'] = (crisis_events['year'] // 10 * 10).astype(int)
            decade_counts = crisis_events.groupby('decade').size().reset_index(name='n_crises')

            fig, ax = plt.subplots(figsize=(12, 7))
            colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(decade_counts)))
            ax.bar(decade_counts['decade'].astype(str) + 's', decade_counts['n_crises'],
                   color=colors, edgecolor='white', width=0.6)

            for i, (_, row) in enumerate(decade_counts.iterrows()):
                ax.text(i, row['n_crises'] + 0.5, str(row['n_crises']),
                        ha='center', va='bottom', fontweight='bold', fontsize=11)

            ax.set_xlabel('Decade', fontweight='bold')
            ax.set_ylabel('Number of Currency Crisis Episodes', fontweight='bold')
            ax.set_title('Currency Crisis Episodes by Decade\n(REER decline > 15% in a single year)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'fx_currency_crises_by_decade.png', dpi=300, bbox_inches='tight')
            logger.info("Saved fx_currency_crises_by_decade.png")
            charts_created += 1
            plt.close(fig)
        else:
            logger.warning("No currency crisis episodes found (REER drop > 15%)")
    except Exception as e:
        logger.error(f"Chart 2 failed: {e}")

    logger.info(f"[V65] Complete: {charts_created}/2 charts created")
    plt.close('all')


if __name__ == "__main__":
    run()
