#!/usr/bin/env python3
"""
V102: Visualize Financial-Fiscal Nexus
Credit gap vs fiscal balance scatter, financial depth vs tax capacity,
and crowding out trend for major economies.
Stage: V | ID: V102
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V102",
    "name": "Visualize Financial-Fiscal Nexus",
    "stage": "V",
    "description": "Credit gap, financial depth, crowding out visualizations",
    "depends_on": ["A196"],
    "inputs": [
        {"path": "Output/Data/fiscal_financial_nexus.xlsx", "required": True},
        {"path": "Output/Data/fiscal_ratios_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/PDFs/financial_fiscal_credit_gap.png"},
        {"path": "Output/PDFs/financial_fiscal_depth_tax.png"},
        {"path": "Output/PDFs/financial_fiscal_crowding.png"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}

plt.style.use("seaborn-v0_8-whitegrid")
DPI = 300

IG_COLORS = {
    "High income": "#1f77b4",
    "Upper middle income": "#ff7f0e",
    "Lower middle income": "#2ca02c",
    "Low income": "#d62728",
}


def ensure_pdf_dir():
    pdf_dir = project_root() / "Output" / "PDFs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir


def chart_credit_gap_scatter(nexus_file, ratios, pdf_dir):
    """Chart 1: Credit gap vs fiscal balance scatter."""
    logger.info("Chart 1: Credit gap vs fiscal balance...")

    # Load credit_gap sheet
    try:
        credit = pd.read_excel(nexus_file, sheet_name="credit_gap")
    except Exception:
        logger.warning("No credit_gap sheet found")
        return

    if credit.empty or "credit_gap" not in credit.columns:
        logger.warning("credit_gap data missing")
        return

    # Merge fiscal balance from ratios
    if not ratios.empty and "fiscal_balance" in ratios.columns:
        latest_fiscal = (
            ratios.dropna(subset=["fiscal_balance"])
            .sort_values("year")
            .groupby("country_code")
            .last()
            .reset_index()[["country_code", "fiscal_balance"]]
        )
        plot_data = credit.merge(latest_fiscal, on="country_code", how="inner")
    else:
        plot_data = credit.copy()
        if "fiscal_balance" not in plot_data.columns:
            logger.warning("No fiscal_balance for scatter")
            return

    fig, ax = plt.subplots(figsize=(12, 8))

    for ig, color in IG_COLORS.items():
        mask = plot_data.get("income_group") == ig
        if mask.any():
            subset = plot_data[mask]
            ax.scatter(subset["credit_gap"], subset["fiscal_balance"],
                       c=color, label=ig, alpha=0.7, s=60, edgecolors="white", linewidth=0.5)

    # Quadrant lines
    ax.axhline(0, color="gray", linestyle="--", linewidth=0.8)
    ax.axvline(0, color="gray", linestyle="--", linewidth=0.8)

    # Label outliers
    for _, row in plot_data.nlargest(5, "credit_gap").iterrows():
        ax.annotate(row["country_code"], (row["credit_gap"], row["fiscal_balance"]),
                    fontsize=7, alpha=0.8)

    ax.set_xlabel("Credit-to-GDP Gap (pp above 10yr MA)", fontsize=12)
    ax.set_ylabel("Fiscal Balance (% GDP)", fontsize=12)
    ax.set_title("Credit Gap vs Fiscal Balance", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(pdf_dir / "financial_fiscal_credit_gap.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved financial_fiscal_credit_gap.png")


def chart_depth_tax(nexus_file, pdf_dir):
    """Chart 2: Financial depth vs tax capacity scatter."""
    logger.info("Chart 2: Financial depth vs tax capacity...")

    try:
        depth = pd.read_excel(nexus_file, sheet_name="depth_vs_tax")
    except Exception:
        logger.warning("No depth_vs_tax sheet found")
        return

    if depth.empty:
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    for ig, color in IG_COLORS.items():
        mask = depth.get("income_group") == ig
        if mask is not None and mask.any():
            subset = depth[mask]
            ax.scatter(subset["financial_depth_index"], subset["tax_revenue_pct_gdp"],
                       c=color, label=ig, alpha=0.7, s=60, edgecolors="white", linewidth=0.5)

    # Add regression line
    if "predicted_tax" in depth.columns:
        sorted_d = depth.sort_values("financial_depth_index")
        ax.plot(sorted_d["financial_depth_index"], sorted_d["predicted_tax"],
                color="black", linestyle="--", linewidth=1.5, alpha=0.6, label="OLS fit")

    # Label notable outliers (high residual)
    if "residual" in depth.columns:
        for _, row in depth.nlargest(5, "residual").iterrows():
            ax.annotate(row["country_code"],
                        (row["financial_depth_index"], row["tax_revenue_pct_gdp"]),
                        fontsize=7, alpha=0.8, color="green")
        for _, row in depth.nsmallest(5, "residual").iterrows():
            ax.annotate(row["country_code"],
                        (row["financial_depth_index"], row["tax_revenue_pct_gdp"]),
                        fontsize=7, alpha=0.8, color="red")

    ax.set_xlabel("Financial Depth Index", fontsize=12)
    ax.set_ylabel("Tax Revenue (% GDP)", fontsize=12)
    ax.set_title("Financial Depth vs Tax Capacity", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.savefig(pdf_dir / "financial_fiscal_depth_tax.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved financial_fiscal_depth_tax.png")


def chart_crowding_out(nexus_file, pdf_dir):
    """Chart 3: Crowding out trend for major economies."""
    logger.info("Chart 3: Crowding out trend...")

    try:
        crowding = pd.read_excel(nexus_file, sheet_name="crowding_out")
    except Exception:
        logger.warning("No crowding_out sheet found")
        return

    if crowding.empty or "mean_crowding" not in crowding.columns:
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    for ig, color in IG_COLORS.items():
        mask = crowding["income_group"] == ig
        if mask.any():
            subset = crowding[mask].sort_values("year")
            ax.plot(subset["year"], subset["mean_crowding"],
                    linewidth=2.5, color=color, label=ig)

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Crowding Out Ratio (%)", fontsize=12)
    ax.set_title("Government Crowding Out of Private Credit by Income Group",
                 fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(pdf_dir / "financial_fiscal_crowding.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved financial_fiscal_crowding.png")


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    pdf_dir = ensure_pdf_dir()
    out = output_data_dir()

    nexus_file = out / "fiscal_financial_nexus.xlsx"
    ratios = read_excel_safe(out / "fiscal_ratios_panel.xlsx")

    if not nexus_file.exists():
        logger.error("fiscal_financial_nexus.xlsx not found; aborting.")
        return

    chart_credit_gap_scatter(nexus_file, ratios, pdf_dir)
    chart_depth_tax(nexus_file, pdf_dir)
    chart_crowding_out(nexus_file, pdf_dir)

    charts = list(pdf_dir.glob("financial_fiscal_*.png"))
    logger.info(f"[{MANIFEST['id']}] Done. Generated {len(charts)} charts")


if __name__ == "__main__":
    run()
