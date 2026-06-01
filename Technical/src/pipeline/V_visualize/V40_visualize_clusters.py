#!/usr/bin/env python3
"""
V40: Cluster Visualizations
Scatter plots and profiles for fiscal clusters.
Stage: V | ID: V40
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
    "id": "V40",
    "name": "Cluster Visualizations",
    "stage": "V",
    "description": "Scatter plots and profiles for fiscal clusters",
    "depends_on": ["A88"],
    "inputs": [{"path": "Output/Data/fiscal_clusters.xlsx", "required": True}],
    "outputs": [],
    "timeout": 120,
    "parallel_safe": True,
}

sns.set_style("whitegrid")
plt.rcParams.update({
    'figure.figsize': (12, 8),
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 300,
})

DATA_DIR = output_data_dir()
VIZ_DIR = output_pdfs_dir()

# Major economies to label
MAJOR_ECONOMIES = {
    "USA", "GBR", "DEU", "FRA", "JPN", "CAN", "ITA", "CHN", "IND", "BRA",
    "RUS", "AUS", "KOR", "MEX", "IDN", "TUR", "SAU", "ZAF", "ARG", "NGA",
}


def plot_cluster_scatter(df):
    """2D scatter: tax vs expenditure, colored by cluster."""
    logger.info("Creating cluster scatter plot...")

    # Identify columns
    cluster_col = None
    for c in df.columns:
        if "cluster" in c.lower():
            cluster_col = c
            break
    if cluster_col is None:
        logger.warning("No cluster column found")
        return

    tax_col = None
    exp_col = None
    for c in df.columns:
        cl = c.lower()
        if "tax" in cl and ("pct" in cl or "gdp" in cl):
            tax_col = c
        if "expend" in cl and ("pct" in cl or "gdp" in cl):
            exp_col = c

    if tax_col is None:
        logger.warning("No tax column found for scatter")
        return

    # If no expenditure, use another numeric column
    if exp_col is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != tax_col and c != cluster_col]
        if numeric_cols:
            exp_col = numeric_cols[0]
            logger.info(f"Using '{exp_col}' as y-axis (no expenditure column found)")
        else:
            logger.warning("No suitable y-axis column")
            return

    fig, ax = plt.subplots(figsize=(12, 9))

    clusters = df[cluster_col].unique()
    n_clusters = len(clusters)
    # Use grayscale-friendly markers and shades
    markers = ["o", "s", "^", "D", "v", "P", "X", "*"]
    grays = [str(0.2 + 0.6 * i / max(n_clusters - 1, 1)) for i in range(n_clusters)]

    for i, cl in enumerate(sorted(clusters)):
        mask = df[cluster_col] == cl
        subset = df[mask]
        ax.scatter(
            subset[tax_col], subset[exp_col],
            c=grays[i % len(grays)],
            marker=markers[i % len(markers)],
            edgecolors="black", linewidths=0.5,
            s=60, alpha=0.7,
            label=f"Cluster {cl} (n={len(subset)})",
        )

    # Label major economies
    country_col = "country_code" if "country_code" in df.columns else None
    if country_col:
        for _, row in df.iterrows():
            if row[country_col] in MAJOR_ECONOMIES:
                ax.annotate(
                    row[country_col],
                    (row[tax_col], row[exp_col]),
                    fontsize=7, ha="left", va="bottom",
                    xytext=(3, 3), textcoords="offset points",
                )

    ax.set_xlabel(tax_col.replace("_", " ").title())
    ax.set_ylabel(exp_col.replace("_", " ").title())
    ax.set_title("Fiscal Clusters: Tax vs Expenditure", fontweight="bold")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "cluster_scatter.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_cluster_profiles(df):
    """Grouped bar chart: mean values per cluster for each feature."""
    logger.info("Creating cluster profiles plot...")

    cluster_col = None
    for c in df.columns:
        if "cluster" in c.lower():
            cluster_col = c
            break
    if cluster_col is None:
        logger.warning("No cluster column found")
        return

    # Select numeric feature columns (exclude cluster itself and identifiers)
    exclude = {cluster_col, "country_code", "country_name", "year", "n_years"}
    feature_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                    if c not in exclude and c != cluster_col]

    if not feature_cols:
        logger.warning("No numeric feature columns for profile chart")
        return

    # Limit to most relevant features (max 8)
    feature_cols = feature_cols[:8]

    # Compute cluster means
    means = df.groupby(cluster_col)[feature_cols].mean()

    fig, ax = plt.subplots(figsize=(14, 8))

    n_clusters = len(means)
    n_features = len(feature_cols)
    x = np.arange(n_features)
    width = 0.8 / n_clusters

    grays = [str(0.2 + 0.6 * i / max(n_clusters - 1, 1)) for i in range(n_clusters)]

    for i, (cl, row) in enumerate(means.iterrows()):
        offset = (i - n_clusters / 2 + 0.5) * width
        ax.bar(x + offset, row.values, width, label=f"Cluster {cl}",
               color=grays[i % len(grays)], edgecolor="black", linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in feature_cols], fontsize=9, rotation=30, ha="right")
    ax.set_ylabel("Mean Value")
    ax.set_title("Cluster Profiles: Mean Feature Values by Cluster", fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "cluster_profiles.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    df = read_excel_safe(DATA_DIR / "fiscal_clusters.xlsx")
    if df.empty:
        logger.error("fiscal_clusters.xlsx not found or empty")
        return

    logger.info(f"Loaded fiscal_clusters: {len(df)} rows, {len(df.columns)} cols")

    charts_created = 0

    try:
        plot_cluster_scatter(df)
        charts_created += 1
    except Exception as e:
        logger.warning(f"Cluster scatter failed: {e}")

    try:
        plot_cluster_profiles(df)
        charts_created += 1
    except Exception as e:
        logger.warning(f"Cluster profiles failed: {e}")

    logger.info(f"\nCreated {charts_created} cluster visualizations")
    plt.close("all")


if __name__ == "__main__":
    run()
