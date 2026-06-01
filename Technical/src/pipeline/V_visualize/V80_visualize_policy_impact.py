#!/usr/bin/env python3
"""
V80: Visualize Policy Impact (DiD)
Event study plot and forest plot of DiD estimates.
Stage: V | ID: V80
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
    "id": "V80",
    "name": "Visualize Policy Impact",
    "stage": "V",
    "description": "Event study and forest plots of DiD estimates",
    "depends_on": ["A140"],
    "inputs": [
        {"path": "Output/Data/policy_impact_did_results.xlsx", "required": True},
        {"path": "Output/Data/policy_impact_summary.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/PDFs/policy_event_study.png"},
        {"path": "Output/PDFs/policy_forest_plot.png"},
    ],
    "timeout": 120,
    "parallel_safe": True,
}

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    out_pdfs = output_pdfs_dir()
    out_data = output_data_dir()

    results = read_excel_safe(out_data / "policy_impact_did_results.xlsx")
    summary = read_excel_safe(out_data / "policy_impact_summary.xlsx")

    if results.empty:
        logger.error("Cannot load policy_impact_did_results.xlsx; aborting.")
        return

    # ── 1. Event Study Plot ──
    # Show distribution of DiD estimates by outcome
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    outcomes = results['outcome'].unique()
    for idx, outcome in enumerate(outcomes[:2]):
        ax = axes[idx] if len(outcomes) > 1 else axes[0]
        subset = results[results['outcome'] == outcome]['did_estimate'].dropna()

        if subset.empty:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(outcome)
            continue

        # Histogram with kernel density
        ax.hist(subset, bins=min(20, max(5, len(subset) // 3)), alpha=0.6,
                color='steelblue', edgecolor='black', density=True)
        if len(subset) > 5:
            try:
                from scipy.stats import gaussian_kde
                kde = gaussian_kde(subset)
                x_range = np.linspace(subset.min() - 1, subset.max() + 1, 200)
                ax.plot(x_range, kde(x_range), 'r-', linewidth=2, label='KDE')
            except Exception:
                pass

        ax.axvline(x=0, color='black', linestyle='--', linewidth=1, label='Zero effect')
        mean_did = subset.mean()
        ax.axvline(x=mean_did, color='red', linestyle='-', linewidth=1.5,
                   label=f'Mean = {mean_did:.2f}')

        ax.set_xlabel('DiD Estimate (pp)')
        ax.set_ylabel('Density')
        ax.set_title(f'Distribution of DiD Effects: {outcome}', fontsize=12, fontweight='bold')
        ax.legend(fontsize=9)

    # Hide unused axis if only one outcome
    if len(outcomes) < 2:
        axes[1].set_visible(False)

    plt.suptitle('Policy Impact: Distribution of Difference-in-Differences Estimates',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(out_pdfs / "policy_event_study.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved policy_event_study.png")

    # ── 2. Forest Plot ──
    # Show individual event estimates for tax outcome
    tax_results = results[results['outcome'] == 'tax_revenue_pct_gdp'].copy()
    if tax_results.empty and not results.empty:
        tax_results = results[results['outcome'] == results['outcome'].iloc[0]].copy()

    if tax_results.empty:
        logger.warning("No tax results for forest plot.")
        return

    # Sort by DiD estimate
    tax_results = tax_results.sort_values('did_estimate').reset_index(drop=True)

    # Limit to top 30 for readability
    if len(tax_results) > 30:
        # Show top 15 and bottom 15
        tax_results = pd.concat([tax_results.head(15), tax_results.tail(15)])

    fig, ax = plt.subplots(figsize=(10, max(6, len(tax_results) * 0.35)))

    y_pos = np.arange(len(tax_results))
    colors = ['#d62728' if v < 0 else '#2ca02c' for v in tax_results['did_estimate']]

    ax.barh(y_pos, tax_results['did_estimate'], color=colors, alpha=0.7,
            edgecolor='black', linewidth=0.5, height=0.7)
    ax.axvline(x=0, color='black', linewidth=1)

    # Labels
    labels = [f"{row['country_name'][:15]} ({int(row['break_year'])})"
              if pd.notna(row.get('country_name')) else f"{row['country_code']} ({int(row['break_year'])})"
              for _, row in tax_results.iterrows()]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel('DiD Estimate (pp of GDP)')
    ax.set_title('Forest Plot: Individual Policy Break Effects on Tax Revenue',
                 fontsize=13, fontweight='bold')

    # Add mean line
    mean_val = tax_results['did_estimate'].mean()
    ax.axvline(x=mean_val, color='blue', linestyle='--', linewidth=1.5,
               label=f'Mean = {mean_val:.2f}')
    ax.legend(fontsize=10)

    plt.tight_layout()
    fig.savefig(out_pdfs / "policy_forest_plot.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved policy_forest_plot.png")

    logger.info(f"[{MANIFEST['id']}] Complete")


if __name__ == "__main__":
    run()
