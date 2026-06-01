#!/usr/bin/env python3
"""
V100: Visualize Fiscal Ratios
Heatmap of 30 largest economies, tax structure stacked area for G7,
and interest burden top-10 line chart.
Stage: V | ID: V100
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V100",
    "name": "Visualize Fiscal Ratios",
    "stage": "V",
    "description": "Fiscal ratio heatmap, tax structure, interest burden charts",
    "depends_on": ["A190"],
    "inputs": [
        {"path": "Output/Data/fiscal_ratios_panel.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/PDFs/ratio_heatmap.png"},
        {"path": "Output/PDFs/ratio_tax_structure.png"},
        {"path": "Output/PDFs/ratio_interest_burden.png"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}

plt.style.use("seaborn-v0_8-whitegrid")
DPI = 300

G7 = ["USA", "GBR", "DEU", "FRA", "JPN", "ITA", "CAN"]


def ensure_pdf_dir():
    pdf_dir = project_root() / "Output" / "PDFs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir


def chart_ratio_heatmap(df, pdf_dir):
    """Chart 1: Fiscal ratio heatmap for 30 largest economies."""
    logger.info("Chart 1: Fiscal ratio heatmap...")

    ratio_cols = ["tax_burden", "interest_pct_gdp", "debt_to_revenue",
                  "primary_balance_pct_gdp", "fiscal_balance", "social_spending_pct_gdp"]
    available = [c for c in ratio_cols if c in df.columns]
    if len(available) < 2:
        logger.warning("Too few ratio columns for heatmap")
        return

    # Get 30 largest by GDP
    if "gdp_current_usd" in df.columns:
        latest = df.sort_values("year").groupby("country_code").last().reset_index()
        top30 = latest.nlargest(30, "gdp_current_usd")
    else:
        latest = df.sort_values("year").groupby("country_code").last().reset_index()
        top30 = latest.head(30)

    label_col = "country_name" if "country_name" in top30.columns else "country_code"
    heat_data = top30.set_index(label_col)[available]

    # Normalize each column to 0-1 for heatmap
    heat_norm = (heat_data - heat_data.min()) / (heat_data.max() - heat_data.min() + 1e-10)

    fig, ax = plt.subplots(figsize=(12, 14))
    im = ax.imshow(heat_norm.values, cmap="RdYlGn", aspect="auto")

    ax.set_xticks(range(len(available)))
    ax.set_xticklabels([c.replace("_", " ").title() for c in available], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(heat_norm)))
    ax.set_yticklabels(heat_norm.index, fontsize=8)

    # Add text annotations
    for i in range(len(heat_norm)):
        for j in range(len(available)):
            val = heat_data.iloc[i, j]
            if pd.notna(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=6,
                        color="white" if heat_norm.iloc[i, j] < 0.3 or heat_norm.iloc[i, j] > 0.7 else "black")

    plt.colorbar(im, ax=ax, label="Normalized (0=min, 1=max)", shrink=0.6)
    ax.set_title("Fiscal Ratio Heatmap: 30 Largest Economies", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(pdf_dir / "ratio_heatmap.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved ratio_heatmap.png")


def chart_tax_structure(df, pdf_dir):
    """Chart 2: Tax structure stacked area for G7 over 30 years."""
    logger.info("Chart 2: Tax structure stacked area...")

    g7 = df[df["country_code"].isin(G7)].copy()
    if g7.empty:
        logger.warning("No G7 data")
        return

    share_cols = ["direct_tax_share", "indirect_tax_share", "trade_tax_pct_revenue"]
    avail = [c for c in share_cols if c in g7.columns]
    if len(avail) < 2:
        # Fallback to raw revenue composition columns
        for c in ["income_tax_pct_revenue", "goods_services_tax_pct_revenue"]:
            if c in g7.columns and c not in avail:
                avail.append(c)

    if len(avail) < 2:
        logger.warning("Too few tax share columns")
        return

    # Last 30 years
    max_year = g7["year"].max()
    g7 = g7[g7["year"] >= max_year - 30]

    fig, axes = plt.subplots(2, 4, figsize=(18, 10))
    axes = axes.flatten()

    for i, cc in enumerate(G7):
        ax = axes[i]
        country_data = g7[g7["country_code"] == cc].sort_values("year")
        if country_data.empty:
            ax.set_visible(False)
            continue

        plot_data = country_data[avail].fillna(0)
        labels = [c.replace("_pct_revenue", "").replace("_tax_share", "").replace("_", " ").title()
                  for c in avail]
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"][:len(avail)]

        ax.stackplot(country_data["year"], *[plot_data[c] for c in avail],
                     labels=labels, colors=colors, alpha=0.8)
        name = country_data["country_name"].iloc[0] if "country_name" in country_data.columns else cc
        ax.set_title(name, fontsize=10, fontweight="bold")
        ax.set_ylabel("% of Revenue", fontsize=8)
        if i == 0:
            ax.legend(fontsize=7, loc="upper left")

    # Hide unused subplot
    if len(G7) < len(axes):
        for j in range(len(G7), len(axes)):
            axes[j].set_visible(False)

    fig.suptitle("Tax Structure: Direct vs Indirect (G7, Last 30 Years)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(pdf_dir / "ratio_tax_structure.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved ratio_tax_structure.png")


def chart_interest_burden(df, pdf_dir):
    """Chart 3: Interest burden top 10 line chart over time."""
    logger.info("Chart 3: Interest burden top 10...")

    burden_col = None
    for c in ["interest_pct_gdp", "interest_pct_revenue"]:
        if c in df.columns:
            burden_col = c
            break

    if not burden_col:
        logger.warning("No interest burden column available")
        return

    # Find top 10 countries by latest interest burden
    latest = df.dropna(subset=[burden_col]).sort_values("year").groupby("country_code").last().reset_index()
    top10 = latest.nlargest(10, burden_col)["country_code"].tolist()

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    for i, cc in enumerate(top10):
        cdata = df[df["country_code"] == cc].sort_values("year").dropna(subset=[burden_col])
        if cdata.empty:
            continue
        label = cdata["country_name"].iloc[0] if "country_name" in cdata.columns else cc
        ax.plot(cdata["year"], cdata[burden_col], linewidth=2, color=colors[i],
                label=f"{label} ({cdata[burden_col].iloc[-1]:.1f}%)")

    ax.set_title(f"Interest Burden: Top 10 Countries ({burden_col.replace('_', ' ').title()})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel(burden_col.replace("_", " ").title(), fontsize=12)
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.02, 1))
    plt.tight_layout()
    plt.savefig(pdf_dir / "ratio_interest_burden.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved ratio_interest_burden.png")


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    pdf_dir = ensure_pdf_dir()
    out = output_data_dir()

    df = read_excel_safe(out / "fiscal_ratios_panel.xlsx")
    if df.empty:
        logger.error("Cannot load fiscal_ratios_panel.xlsx; aborting.")
        return

    logger.info(f"Loaded fiscal ratios: {len(df)} rows, {df['country_code'].nunique()} countries")

    chart_ratio_heatmap(df, pdf_dir)
    chart_tax_structure(df, pdf_dir)
    chart_interest_burden(df, pdf_dir)

    charts = list(pdf_dir.glob("ratio_*.png"))
    logger.info(f"[{MANIFEST['id']}] Done. Generated {len(charts)} charts")


if __name__ == "__main__":
    run()
