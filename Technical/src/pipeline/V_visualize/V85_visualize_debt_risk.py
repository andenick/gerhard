#!/usr/bin/env python3
"""
V85: Visualize Debt Early Warning
Risk ranking bar chart and feature importance plot.
Stage: V | ID: V85
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
    "id": "V85",
    "name": "Visualize Debt Risk",
    "stage": "V",
    "description": "Risk ranking and feature importance visualizations",
    "depends_on": ["A145"],
    "inputs": [
        {"path": "Output/Data/debt_early_warning_model.xlsx", "required": True},
        {"path": "Output/Data/debt_early_warning_diagnostics.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/PDFs/debt_warning_risk_ranking.png"},
        {"path": "Output/PDFs/debt_warning_feature_importance.png"},
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

    model = read_excel_safe(out_data / "debt_early_warning_model.xlsx")
    diag = read_excel_safe(out_data / "debt_early_warning_diagnostics.xlsx")

    if model.empty:
        logger.error("Cannot load debt_early_warning_model.xlsx; aborting.")
        return

    # ── 1. Risk Ranking: Top 20 highest-risk countries ──
    # Determine the risk column
    risk_col = None
    for col in ['ensemble_prob', 'rf_crisis_prob', 'debt_risk_score']:
        if col in model.columns:
            risk_col = col
            break

    if risk_col is None:
        logger.error("No risk score column found in model output.")
        return

    top20 = model.nlargest(20, risk_col).copy()

    fig, ax = plt.subplots(figsize=(10, 8))

    # Color by risk level
    colors = []
    for val in top20[risk_col]:
        if risk_col == 'ensemble_prob' or risk_col == 'rf_crisis_prob':
            if val > 0.5:
                colors.append('#d62728')
            elif val > 0.3:
                colors.append('#ff7f0e')
            else:
                colors.append('#2ca02c')
        else:
            pct = val / top20[risk_col].max() if top20[risk_col].max() > 0 else 0
            if pct > 0.7:
                colors.append('#d62728')
            elif pct > 0.4:
                colors.append('#ff7f0e')
            else:
                colors.append('#2ca02c')

    y_pos = np.arange(len(top20))
    labels = top20['country_name'].fillna(top20['country_code']).tolist()

    ax.barh(y_pos, top20[risk_col].values, color=colors, alpha=0.8,
            edgecolor='black', linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()

    risk_label = {
        'ensemble_prob': 'Crisis Probability',
        'rf_crisis_prob': 'RF Crisis Probability',
        'debt_risk_score': 'Debt Risk Score',
    }.get(risk_col, risk_col)

    ax.set_xlabel(risk_label)
    ax.set_title('Top 20 Countries by Debt Crisis Risk', fontsize=14, fontweight='bold')

    # Add value labels
    for i, (val, label) in enumerate(zip(top20[risk_col].values, labels)):
        ax.text(val + 0.01 * top20[risk_col].max(), i, f'{val:.2f}',
                va='center', fontsize=8)

    plt.tight_layout()
    fig.savefig(out_pdfs / "debt_warning_risk_ranking.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved debt_warning_risk_ranking.png")

    # ── 2. Feature Importance ──
    if diag.empty:
        logger.warning("No diagnostics data; skipping feature importance chart.")
        return

    # Extract feature importances from diagnostics
    fi_rows = diag[diag['metric'].str.startswith('fi_', na=False)].copy()

    if fi_rows.empty:
        logger.warning("No feature importance data in diagnostics; skipping.")
        # Try to create a simple AUC comparison instead
        auc_rows = diag[diag['metric'].str.contains('auc', na=False)]
        if not auc_rows.empty:
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.barh(auc_rows['metric'], auc_rows['value'], color='steelblue', alpha=0.8)
            ax.set_xlabel('AUC Score')
            ax.set_title('Model Performance (AUC)', fontsize=14, fontweight='bold')
            ax.set_xlim(0, 1)
            plt.tight_layout()
            fig.savefig(out_pdfs / "debt_warning_feature_importance.png", dpi=150, bbox_inches='tight')
            plt.close(fig)
            logger.info("Saved debt_warning_feature_importance.png (AUC only)")
        return

    fi_rows['feature'] = fi_rows['metric'].str.replace('fi_', '', regex=False)
    fi_rows = fi_rows.sort_values('value', ascending=True)

    # Show top 10
    fi_top = fi_rows.tail(10)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(fi_top['feature'], fi_top['value'], color='steelblue', alpha=0.8,
            edgecolor='black', linewidth=0.5)
    ax.set_xlabel('Feature Importance (Random Forest)')
    ax.set_title('Top Predictive Features for Debt Crisis', fontsize=14, fontweight='bold')

    # Add AUC annotation
    lr_auc = diag[diag['metric'] == 'lr_auc']['value'].values
    rf_auc = diag[diag['metric'] == 'rf_auc']['value'].values
    auc_text = []
    if len(lr_auc) > 0:
        auc_text.append(f"LR AUC: {lr_auc[0]:.3f}")
    if len(rf_auc) > 0:
        auc_text.append(f"RF AUC: {rf_auc[0]:.3f}")
    if auc_text:
        ax.text(0.95, 0.05, '\n'.join(auc_text), transform=ax.transAxes,
                fontsize=11, va='bottom', ha='right',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    plt.tight_layout()
    fig.savefig(out_pdfs / "debt_warning_feature_importance.png", dpi=150, bbox_inches='tight')
    plt.close(fig)
    logger.info("Saved debt_warning_feature_importance.png")

    logger.info(f"[{MANIFEST['id']}] Complete")


if __name__ == "__main__":
    run()
