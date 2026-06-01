#!/usr/bin/env python3
"""
V90: Visualize Tax Effort Index
Actual vs predicted scatter plot and effort distribution by income group.
Stage: V | ID: V90
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
    "id": "V90",
    "name": "Visualize Tax Effort",
    "stage": "V",
    "description": "Actual vs predicted scatter and effort distribution by income group",
    "depends_on": ["A150"],
    "inputs": [
        {"path": "Output/Data/tax_effort_index.xlsx", "required": True},
        {"path": "Output/Data/tax_effort_summary.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/PDFs/tax_effort_scatter.png"},
        {"path": "Output/PDFs/tax_effort_distribution.png"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


# Income group color map
IG_COLORS = {
    'High income': '#1f77b4',
    'Upper middle income': '#2ca02c',
    'Lower middle income': '#ff7f0e',
    'Low income': '#d62728',
}


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out_pdfs = output_pdfs_dir()
    out_data = output_data_dir()

    effort = read_excel_safe(out_data / "tax_effort_index.xlsx")

    if effort.empty:
        logger.error("Cannot load tax_effort_index.xlsx; aborting.")
        return

    # ── 1. Actual vs Predicted Scatter ──
    fig, ax = plt.subplots(figsize=(10, 10))

    # Plot by income group
    for ig, color in IG_COLORS.items():
        subset = effort[effort['income_group'] == ig]
        if subset.empty:
            continue
        ax.scatter(subset['predicted_tax'], subset['tax_pct_gdp'],
                   c=color, label=ig, alpha=0.7, s=50, edgecolors='black', linewidth=0.3)

    # Countries not in standard income groups
    other = effort[~effort['income_group'].isin(IG_COLORS)]
    if not other.empty:
        ax.scatter(other['predicted_tax'], other['tax_pct_gdp'],
                   c='gray', label='Other', alpha=0.5, s=40, edgecolors='black', linewidth=0.3)

    # 45-degree line
    all_vals = pd.concat([effort['predicted_tax'], effort['tax_pct_gdp']]).dropna()
    if not all_vals.empty:
        lim_min = max(0, all_vals.min() - 2)
        lim_max = all_vals.max() + 2
        ax.plot([lim_min, lim_max], [lim_min, lim_max], 'k--', linewidth=1.5,
                label='45-degree line (effort = 1.0)', alpha=0.6)
        ax.set_xlim(lim_min, lim_max)
        ax.set_ylim(lim_min, lim_max)

    # Label notable outliers
    if 'tax_effort' in effort.columns:
        outliers = effort[
            (effort['tax_effort'] > 1.5) | (effort['tax_effort'] < 0.5)
        ].head(15)
        for _, row in outliers.iterrows():
            label = row.get('country_code', '')
            if pd.notna(row.get('predicted_tax')) and pd.notna(row.get('tax_pct_gdp')):
                ax.annotate(label, (row['predicted_tax'], row['tax_pct_gdp']),
                            fontsize=7, ha='left', va='bottom',
                            xytext=(3, 3), textcoords='offset points')

    ax.set_xlabel('Predicted Tax/GDP (% - based on structural factors)')
    ax.set_ylabel('Actual Tax/GDP (%)')
    ax.set_title('Tax Effort: Actual vs Predicted Tax Revenue',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')

    # Add annotation
    ax.text(0.95, 0.05, 'Above line = overperforming\nBelow line = underperforming',
            transform=ax.transAxes, fontsize=9, va='bottom', ha='right',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig.savefig(out_pdfs / "tax_effort_scatter.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved tax_effort_scatter.png")

    # ── 2. Effort Distribution by Income Group ──
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    income_groups = [ig for ig in IG_COLORS if ig in effort['income_group'].values]
    if not income_groups:
        income_groups = effort['income_group'].dropna().unique().tolist()[:4]

    for idx, ig in enumerate(income_groups[:4]):
        ax = axes[idx]
        subset = effort[effort['income_group'] == ig]['tax_effort'].dropna()

        if subset.empty:
            ax.text(0.5, 0.5, f'{ig}\nNo data', ha='center', va='center',
                    transform=ax.transAxes)
            continue

        color = IG_COLORS.get(ig, 'steelblue')
        ax.hist(subset, bins=min(15, max(5, len(subset) // 3)),
                alpha=0.7, color=color, edgecolor='black')
        ax.axvline(x=1.0, color='red', linestyle='--', linewidth=1.5, label='Effort = 1.0')
        ax.axvline(x=subset.mean(), color='blue', linestyle='-', linewidth=1.5,
                   label=f'Mean = {subset.mean():.2f}')

        ax.set_xlabel('Tax Effort Index')
        ax.set_ylabel('Number of Countries')
        ax.set_title(f'{ig} (n={len(subset)})', fontsize=11, fontweight='bold')
        ax.legend(fontsize=8)

    # Hide unused axes
    for idx in range(len(income_groups), 4):
        axes[idx].set_visible(False)

    plt.suptitle('Tax Effort Distribution by Income Group',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(out_pdfs / "tax_effort_distribution.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved tax_effort_distribution.png")

    logger.info(f"[{MANIFEST['id']}] Complete")


if __name__ == "__main__":
    run()
