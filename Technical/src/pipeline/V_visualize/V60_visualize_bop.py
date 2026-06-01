"""
Pipeline: Visualize Balance of Payments
Creates charts showing twin deficits, FDI vs tax, and remittance rankings.
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
    "id": "V60",
    "name": "Visualize Balance of Payments",
    "stage": "V",
    "description": "Creates PNG visualizations of BoP: twin deficits scatter, FDI vs tax, remittance top 20.",
    "depends_on": ["A110"],
    "inputs": [
        {"path": "Output/Data/bop_panel.xlsx", "required": True, "description": "Balance of payments panel"},
        {"path": "Output/Data/master_fiscal_panel.xlsx", "required": True, "description": "Master panel with fiscal_balance, region"},
    ],
    "outputs": [
        {"path": "Output/PDFs/bop_twin_deficits_scatter.png", "description": "Twin deficits scatter plot"},
        {"path": "Output/PDFs/bop_fdi_vs_tax.png", "description": "FDI inflows vs tax revenue scatter"},
        {"path": "Output/PDFs/bop_remittance_top20.png", "description": "Top 20 remittance recipients"},
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

    bop = read_excel_safe(out_data / 'bop_panel.xlsx')
    master = read_excel_safe(out_data / 'master_fiscal_panel.xlsx')

    if bop.empty or master.empty:
        logger.warning("Required data not found, skipping")
        return

    charts_created = 0

    # ── Chart 1: Twin deficits scatter ──────────────────────────────────
    try:
        # Get latest year per country from master (has fiscal_balance_pct_gdp)
        m_latest = master.dropna(subset=['fiscal_balance_pct_gdp', 'region']).copy()
        m_latest = m_latest.sort_values('year').groupby('country_code').last().reset_index()

        # Get latest current_account from bop
        b_latest = bop.dropna(subset=['current_account_pct_gdp']).copy()
        b_latest = b_latest.sort_values('year').groupby('country_code').last().reset_index()

        twin = m_latest[['country_code', 'fiscal_balance_pct_gdp', 'region']].merge(
            b_latest[['country_code', 'current_account_pct_gdp']], on='country_code', how='inner')

        if len(twin) > 5:
            fig, ax = plt.subplots(figsize=(12, 9))
            regions = twin['region'].unique()
            palette = sns.color_palette('Set2', len(regions))
            region_colors = dict(zip(regions, palette))

            for region in regions:
                subset = twin[twin['region'] == region]
                ax.scatter(subset['fiscal_balance_pct_gdp'], subset['current_account_pct_gdp'],
                           c=[region_colors[region]], label=region, alpha=0.7, s=50, edgecolors='white')

            # Regression line
            x_vals = twin['fiscal_balance_pct_gdp'].values
            y_vals = twin['current_account_pct_gdp'].values
            mask = np.isfinite(x_vals) & np.isfinite(y_vals)
            if mask.sum() > 3:
                z = np.polyfit(x_vals[mask], y_vals[mask], 1)
                p = np.poly1d(z)
                x_line = np.linspace(x_vals[mask].min(), x_vals[mask].max(), 100)
                ax.plot(x_line, p(x_line), '--', color='gray', linewidth=1.5, alpha=0.7, label=f'OLS (slope={z[0]:.2f})')

            ax.axhline(0, color='black', linewidth=0.5, alpha=0.5)
            ax.axvline(0, color='black', linewidth=0.5, alpha=0.5)
            ax.set_xlabel('Fiscal Balance (% of GDP)', fontweight='bold')
            ax.set_ylabel('Current Account (% of GDP)', fontweight='bold')
            ax.set_title('Twin Deficits Hypothesis\nFiscal Balance vs Current Account (latest year, by region)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.legend(fontsize=8, frameon=True, loc='best')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'bop_twin_deficits_scatter.png', dpi=300, bbox_inches='tight')
            logger.info("Saved bop_twin_deficits_scatter.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 1 failed: {e}")

    # ── Chart 2: FDI vs tax scatter ─────────────────────────────────────
    try:
        b_fdi = bop.dropna(subset=['fdi_inflows_pct_gdp']).copy()
        b_fdi = b_fdi.sort_values('year').groupby('country_code').last().reset_index()

        m_tax = master.dropna(subset=['tax_revenue_pct_gdp', 'gdp_current_usd']).copy()
        m_tax = m_tax.sort_values('year').groupby('country_code').last().reset_index()

        fdi_tax = b_fdi[['country_code', 'fdi_inflows_pct_gdp']].merge(
            m_tax[['country_code', 'tax_revenue_pct_gdp', 'gdp_current_usd', 'income_group']], on='country_code', how='inner')
        fdi_tax = fdi_tax.dropna()
        # Clamp extreme FDI outliers for readability
        fdi_tax = fdi_tax[(fdi_tax['fdi_inflows_pct_gdp'] > -20) & (fdi_tax['fdi_inflows_pct_gdp'] < 50)]

        if len(fdi_tax) > 5:
            fig, ax = plt.subplots(figsize=(12, 9))
            sizes = np.log10(fdi_tax['gdp_current_usd'].clip(lower=1e8)) * 15

            ig_groups = fdi_tax['income_group'].fillna('Unknown').unique()
            palette = sns.color_palette('Set1', len(ig_groups))
            ig_colors = dict(zip(ig_groups, palette))

            for ig in ig_groups:
                subset = fdi_tax[fdi_tax['income_group'].fillna('Unknown') == ig]
                ax.scatter(subset['tax_revenue_pct_gdp'], subset['fdi_inflows_pct_gdp'],
                           s=np.log10(subset['gdp_current_usd'].clip(lower=1e8)) * 15,
                           c=[ig_colors[ig]], label=ig, alpha=0.6, edgecolors='white')

            ax.set_xlabel('Tax Revenue (% of GDP)', fontweight='bold')
            ax.set_ylabel('FDI Inflows (% of GDP)', fontweight='bold')
            ax.set_title('FDI Inflows vs Tax Revenue\n(Bubble size = log GDP)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.legend(fontsize=8, frameon=True, loc='upper right')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            fig.savefig(out_pdfs / 'bop_fdi_vs_tax.png', dpi=300, bbox_inches='tight')
            logger.info("Saved bop_fdi_vs_tax.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 2 failed: {e}")

    # ── Chart 3: Top remittance countries ───────────────────────────────
    try:
        rem = bop.dropna(subset=['remittances_pct_gdp']).copy()
        rem_latest = rem.sort_values('year').groupby('country_code').last().reset_index()
        top20 = rem_latest.nlargest(20, 'remittances_pct_gdp')

        if len(top20) > 0:
            fig, ax = plt.subplots(figsize=(12, 8))
            top20_sorted = top20.sort_values('remittances_pct_gdp', ascending=True)
            colors = plt.cm.YlOrRd(np.linspace(0.3, 0.9, len(top20_sorted)))
            ax.barh(range(len(top20_sorted)), top20_sorted['remittances_pct_gdp'].values,
                    color=colors, edgecolor='white')
            ax.set_yticks(range(len(top20_sorted)))
            ax.set_yticklabels(top20_sorted['country_name'].values, fontsize=9)
            ax.set_xlabel('Remittances Received (% of GDP)', fontweight='bold')
            ax.set_title('Top 20 Remittance-Receiving Countries\n(% of GDP, latest available year)',
                          fontsize=14, fontweight='bold', pad=15)
            ax.grid(axis='x', alpha=0.3)

            for i, v in enumerate(top20_sorted['remittances_pct_gdp'].values):
                ax.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=8)

            plt.tight_layout()
            fig.savefig(out_pdfs / 'bop_remittance_top20.png', dpi=300, bbox_inches='tight')
            logger.info("Saved bop_remittance_top20.png")
            charts_created += 1
            plt.close(fig)
    except Exception as e:
        logger.error(f"Chart 3 failed: {e}")

    logger.info(f"[V60] Complete: {charts_created}/3 charts created")
    plt.close('all')


if __name__ == "__main__":
    run()
