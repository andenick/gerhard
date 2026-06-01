"""
Pipeline: Visualize Revenue Composition
Creates charts showing tax revenue structure by income group and over time.
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
    "id": "V50",
    "name": "Visualize Revenue Composition",
    "stage": "V",
    "description": "Creates PNG visualizations of tax revenue structure by income group, direct vs indirect tax trends, and diversification.",
    "depends_on": ["A100"],
    "inputs": [
        {"path": "Output/Data/revenue_composition_panel.xlsx", "required": True, "description": "Tax revenue breakdown by type"},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True, "description": "Master panel with income_group"},
    ],
    "outputs": [
        {"path": "Output/PDFs/revenue_tax_structure_by_income_group.png", "description": "Stacked bar of tax type shares by income group"},
        {"path": "Output/PDFs/revenue_direct_vs_indirect_g7.png", "description": "Direct vs indirect tax trends for G7"},
        {"path": "Output/PDFs/revenue_diversification_boxplot.png", "description": "Tax diversification index by income group"},
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

    rev = read_excel_safe(out_data / 'revenue_composition_panel.xlsx')
    master = read_excel_safe(out_data / 'master_fiscal_panel.xlsx')

    if rev.empty or master.empty:
        logger.warning("Required data not found, skipping")
        return

    # Merge income_group from master
    ig_map = master[['country_code', 'income_group']].drop_duplicates('country_code')
    rev = rev.merge(ig_map, on='country_code', how='left')

    charts_created = 0

    # ── Chart 1: Stacked bar — tax type shares by income group ──────────
    try:
        latest = rev.dropna(subset=['income_group']).copy()
        latest = latest.sort_values('year').groupby('country_code').last().reset_index()

        # Compute means by income group
        group_order = ['High income', 'Upper middle income', 'Lower middle income', 'Low income']
        agg = latest.groupby('income_group').agg(
            income_tax=('income_tax_pct_revenue', 'mean'),
            goods_services=('goods_services_tax_pct_revenue', 'mean'),
            trade_tax=('trade_tax_pct_revenue', 'mean'),
            other=('other_tax_pct_revenue', 'mean'),
        ).reindex([g for g in group_order if g in latest['income_group'].unique()])

        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(agg))
        width = 0.55
        colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6']
        labels = ['Income Tax', 'Goods & Services', 'Trade Tax', 'Other']

        bottom = np.zeros(len(agg))
        for col, color, label in zip(['income_tax', 'goods_services', 'trade_tax', 'other'], colors, labels):
            vals = agg[col].values
            ax.bar(x, vals, width, bottom=bottom, label=label, color=color, alpha=0.9)
            bottom += vals

        ax.set_xticks(x)
        ax.set_xticklabels(agg.index, fontsize=11)
        ax.set_ylabel('Share of Revenue (%)', fontweight='bold')
        ax.set_title('Tax Revenue Structure by Income Group\n(Mean shares, latest available year per country)',
                      fontsize=14, fontweight='bold', pad=15)
        ax.legend(frameon=True, shadow=True)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'revenue_tax_structure_by_income_group.png', dpi=300, bbox_inches='tight')
        logger.info("Saved revenue_tax_structure_by_income_group.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 1 failed: {e}")

    # ── Chart 2: Direct vs indirect for G7 ──────────────────────────────
    try:
        g7_codes = ['USA', 'GBR', 'DEU', 'FRA', 'JPN', 'CAN', 'ITA']
        g7 = rev[rev['country_code'].isin(g7_codes)].copy()
        g7['indirect_pct'] = 100 - g7['income_tax_pct_revenue']

        fig, ax = plt.subplots(figsize=(14, 7))
        for code in g7_codes:
            subset = g7[g7['country_code'] == code].sort_values('year')
            if subset.empty:
                continue
            ax.plot(subset['year'], subset['income_tax_pct_revenue'],
                    marker='o', markersize=3, linewidth=1.5, label=f'{code} direct')

        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Direct Tax Share of Revenue (%)', fontweight='bold')
        ax.set_title('Direct Tax Share of Revenue — G7 Countries',
                      fontsize=14, fontweight='bold', pad=15)
        ax.legend(ncol=2, fontsize=9, frameon=True)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'revenue_direct_vs_indirect_g7.png', dpi=300, bbox_inches='tight')
        logger.info("Saved revenue_direct_vs_indirect_g7.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 2 failed: {e}")

    # ── Chart 3: Diversification index box plot ─────────────────────────
    try:
        div_data = rev.dropna(subset=['tax_diversification_index', 'income_group']).copy()
        latest_div = div_data.sort_values('year').groupby('country_code').last().reset_index()

        group_order = ['High income', 'Upper middle income', 'Lower middle income', 'Low income']
        ordered = [g for g in group_order if g in latest_div['income_group'].unique()]

        fig, ax = plt.subplots(figsize=(12, 7))
        bp_data = [latest_div[latest_div['income_group'] == g]['tax_diversification_index'].dropna().values
                   for g in ordered]
        bp = ax.boxplot(bp_data, tick_labels=[g.replace(' income', '') for g in ordered],
                        patch_artist=True, widths=0.5)
        colors = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']
        for patch, color in zip(bp['boxes'], colors[:len(bp['boxes'])]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_ylabel('Tax Diversification Index', fontweight='bold')
        ax.set_title('Tax Revenue Diversification by Income Group\n(Higher = more diversified revenue base)',
                      fontsize=14, fontweight='bold', pad=15)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'revenue_diversification_boxplot.png', dpi=300, bbox_inches='tight')
        logger.info("Saved revenue_diversification_boxplot.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 3 failed: {e}")

    logger.info(f"[V50] Complete: {charts_created}/3 charts created")
    plt.close('all')


if __name__ == "__main__":
    run()
