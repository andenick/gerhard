"""
Pipeline: Visualize Expenditure Composition
Creates charts showing government spending structure by type, COFOG radar, and income group.
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
    "id": "V55",
    "name": "Visualize Expenditure Composition",
    "stage": "V",
    "description": "Creates PNG visualizations of government expenditure structure: interest burden, COFOG radar, spending by income group.",
    "depends_on": ["A105"],
    "inputs": [
        {"path": "Output/Data/expenditure_composition_panel.xlsx", "required": True, "description": "Spending by economic and functional category"},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True, "description": "Master panel with income_group"},
    ],
    "outputs": [
        {"path": "Output/PDFs/expenditure_interest_burden_top10.png", "description": "Interest burden line chart, top 10"},
        {"path": "Output/PDFs/expenditure_cofog_radar_eu5.png", "description": "COFOG radar for EU-5"},
        {"path": "Output/PDFs/expenditure_structure_by_income_group.png", "description": "Spending structure by income group"},
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

    exp = read_excel_safe(out_data / 'expenditure_composition_panel.xlsx')
    master = read_excel_safe(out_data / 'master_fiscal_panel.xlsx')

    if exp.empty or master.empty:
        logger.warning("Required data not found, skipping")
        return

    ig_map = master[['country_code', 'income_group']].drop_duplicates('country_code')
    exp = exp.merge(ig_map, on='country_code', how='left')

    charts_created = 0

    # ── Chart 1: Interest burden top 10 ─────────────────────────────────
    try:
        latest = exp.dropna(subset=['interest_pct_gdp']).copy()
        latest_year = latest.sort_values('year').groupby('country_code').last().reset_index()
        top10_codes = latest_year.nlargest(10, 'interest_pct_gdp')['country_code'].tolist()

        fig, ax = plt.subplots(figsize=(14, 7))
        for code in top10_codes:
            subset = exp[exp['country_code'] == code].sort_values('year')
            subset = subset.dropna(subset=['interest_pct_gdp'])
            if subset.empty:
                continue
            ax.plot(subset['year'], subset['interest_pct_gdp'],
                    marker='o', markersize=3, linewidth=1.5,
                    label=subset['country_name'].iloc[0])

        ax.set_xlabel('Year', fontweight='bold')
        ax.set_ylabel('Interest Payments (% of GDP)', fontweight='bold')
        ax.set_title('Government Interest Burden Over Time\nTop 10 Countries by Current Interest/GDP',
                      fontsize=14, fontweight='bold', pad=15)
        ax.legend(fontsize=8, frameon=True, loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'expenditure_interest_burden_top10.png', dpi=300, bbox_inches='tight')
        logger.info("Saved expenditure_interest_burden_top10.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 1 failed: {e}")

    # ── Chart 2: COFOG radar for EU-5 ──────────────────────────────────
    try:
        eu5_codes = ['DEU', 'FRA', 'ITA', 'ESP', 'SWE']
        cofog_cols = [c for c in exp.columns if c.startswith('cofog_') and c != 'cofog_total']

        eu5 = exp[exp['country_code'].isin(eu5_codes)].copy()
        eu5_latest = eu5.sort_values('year').groupby('country_code').last().reset_index()

        # Only use rows with at least some COFOG data
        eu5_latest = eu5_latest.dropna(subset=cofog_cols, how='all')

        if len(eu5_latest) > 0 and len(cofog_cols) > 0:
            categories = [c.replace('cofog_', '').replace('_', ' ').title() for c in cofog_cols]
            N = len(categories)
            angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
            angles += angles[:1]

            fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
            colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

            for i, (_, row) in enumerate(eu5_latest.iterrows()):
                values = [row[c] if pd.notna(row[c]) else 0 for c in cofog_cols]
                values += values[:1]
                ax.plot(angles, values, 'o-', linewidth=1.5, label=row['country_name'],
                        color=colors[i % len(colors)], markersize=4)
                ax.fill(angles, values, alpha=0.08, color=colors[i % len(colors)])

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, fontsize=8)
            ax.set_title('COFOG Expenditure Profiles — EU-5 Countries\n(% of GDP by functional category)',
                          fontsize=13, fontweight='bold', pad=30)
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'expenditure_cofog_radar_eu5.png', dpi=300, bbox_inches='tight')
            logger.info("Saved expenditure_cofog_radar_eu5.png")
            charts_created += 1
            plt.close(fig)
        else:
            logger.warning("Insufficient COFOG data for EU-5 radar chart")
    except Exception as e:
        logger.error(f"Chart 2 failed: {e}")

    # ── Chart 3: Spending structure by income group ─────────────────────
    try:
        latest_all = exp.dropna(subset=['income_group']).copy()
        latest_all = latest_all.sort_values('year').groupby('country_code').last().reset_index()

        group_order = ['High income', 'Upper middle income', 'Lower middle income', 'Low income']
        spend_cols = {
            'compensation_pct_expense': 'Compensation',
            'interest_pct_expense': 'Interest',
            'transfers_pct_expense': 'Transfers',
            'other_expense_pct_expense': 'Other',
        }

        agg = latest_all.groupby('income_group')[list(spend_cols.keys())].mean()
        agg = agg.reindex([g for g in group_order if g in agg.index])

        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(agg))
        n_bars = len(spend_cols)
        width = 0.18
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6']

        for i, (col, label) in enumerate(spend_cols.items()):
            offset = (i - n_bars / 2 + 0.5) * width
            vals = agg[col].values
            ax.bar(x + offset, vals, width, label=label, color=colors[i], alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels([g.replace(' income', '') for g in agg.index], fontsize=11)
        ax.set_ylabel('Share of Total Expenditure (%)', fontweight='bold')
        ax.set_title('Government Spending Structure by Income Group\n(Mean shares, latest available year)',
                      fontsize=14, fontweight='bold', pad=15)
        ax.legend(frameon=True, shadow=True)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        fig.savefig(out_pdfs / 'expenditure_structure_by_income_group.png', dpi=300, bbox_inches='tight')
        logger.info("Saved expenditure_structure_by_income_group.png")
        charts_created += 1
        plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 3 failed: {e}")

    logger.info(f"[V55] Complete: {charts_created}/3 charts created")
    plt.close('all')


if __name__ == "__main__":
    run()
