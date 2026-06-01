#!/usr/bin/env python3
"""
V104: Visualize US Fiscal Deep Dive
US receipt decomposition, outlay decomposition, and interest cost charts.
Stage: V | ID: V104
Project: Gerhard
"""
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V104",
    "name": "Visualize US Fiscal",
    "stage": "V",
    "description": "US receipt/outlay decomposition and interest cost charts",
    "depends_on": ["A202"],
    "inputs": [
        {"path": "Output/Data/us_fiscal_deep_dive.xlsx", "required": True},
        {"path": "Output/Data/us_mts_panel.xlsx", "required": False},
    ],
    "outputs": [
        {"path": "Output/PDFs/us_fiscal_receipts.png"},
        {"path": "Output/PDFs/us_fiscal_outlays.png"},
        {"path": "Output/PDFs/us_fiscal_interest_cost.png"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}

plt.style.use("seaborn-v0_8-whitegrid")
DPI = 300


def ensure_pdf_dir():
    pdf_dir = project_root() / "Output" / "PDFs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir


def chart_receipts(mts, pdf_dir):
    """Chart 1: US receipt decomposition stacked area (monthly)."""
    logger.info("Chart 1: US receipts decomposition...")

    if mts.empty:
        logger.warning("No MTS data")
        return

    mts["record_date"] = pd.to_datetime(mts["record_date"])
    mts = mts.sort_values("record_date")

    # Find receipt columns (rolling 12m for smoothing)
    receipt_cols = [c for c in mts.columns if c.startswith("rolling12m_") and "receipt" in c.lower()]
    if not receipt_cols:
        # Fallback to monthly columns
        receipt_cols = [c for c in mts.columns if c.startswith("monthly_") and "receipt" in c.lower()]

    if not receipt_cols:
        # Use any available monthly columns (first half)
        all_monthly = sorted([c for c in mts.columns if c.startswith("monthly_")])
        receipt_cols = all_monthly[:min(5, len(all_monthly))]

    if not receipt_cols:
        logger.warning("No receipt columns found")
        return

    # Clean labels
    labels = [c.replace("rolling12m_", "").replace("monthly_", "").replace("_", " ").title()
              for c in receipt_cols]

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = plt.cm.Set2(np.linspace(0, 1, len(receipt_cols)))

    plot_data = mts[receipt_cols].fillna(0).clip(lower=0)
    ax.stackplot(mts["record_date"], *[plot_data[c] for c in receipt_cols],
                 labels=labels, colors=colors, alpha=0.85)

    ax.set_title("U.S. Federal Receipts by Source (12-Month Rolling Avg)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Monthly Avg ($ Millions)", fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "us_fiscal_receipts.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved us_fiscal_receipts.png")


def chart_outlays(mts, pdf_dir):
    """Chart 2: US outlay decomposition stacked area (monthly)."""
    logger.info("Chart 2: US outlays decomposition...")

    if mts.empty:
        return

    mts["record_date"] = pd.to_datetime(mts["record_date"])
    mts = mts.sort_values("record_date")

    outlay_cols = [c for c in mts.columns if c.startswith("rolling12m_") and "outlay" in c.lower()]
    if not outlay_cols:
        outlay_cols = [c for c in mts.columns if c.startswith("monthly_") and "outlay" in c.lower()]

    if not outlay_cols:
        all_monthly = sorted([c for c in mts.columns if c.startswith("monthly_")])
        outlay_cols = all_monthly[len(all_monthly)//2:len(all_monthly)//2 + 5]

    if not outlay_cols:
        logger.warning("No outlay columns found")
        return

    labels = [c.replace("rolling12m_", "").replace("monthly_", "").replace("_", " ").title()
              for c in outlay_cols]

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = plt.cm.Set1(np.linspace(0, 1, len(outlay_cols)))

    plot_data = mts[outlay_cols].fillna(0).abs()
    ax.stackplot(mts["record_date"], *[plot_data[c] for c in outlay_cols],
                 labels=labels, colors=colors, alpha=0.85)

    ax.set_title("U.S. Federal Outlays by Function (12-Month Rolling Avg)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Monthly Avg ($ Millions)", fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}M"))
    ax.legend(fontsize=8, loc="upper left", ncol=2)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "us_fiscal_outlays.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved us_fiscal_outlays.png")


def chart_interest_cost(deep_dive_file, pdf_dir):
    """Chart 3: US interest cost as % of receipts over time."""
    logger.info("Chart 3: US interest cost...")

    # Try to load interest_cost sheet
    try:
        interest = pd.read_excel(deep_dive_file, sheet_name="interest_cost")
    except Exception:
        logger.warning("No interest_cost sheet; trying refinancing_risk")
        try:
            interest = pd.read_excel(deep_dive_file, sheet_name="refinancing_risk")
        except Exception:
            logger.warning("No interest data available")
            return

    if interest.empty:
        return

    fig, ax = plt.subplots(figsize=(14, 7))

    if "record_date" in interest.columns:
        interest["record_date"] = pd.to_datetime(interest["record_date"])
        x_col = "record_date"
    elif "date" in interest.columns:
        interest["date"] = pd.to_datetime(interest["date"])
        x_col = "date"
    else:
        logger.warning("No date column in interest data")
        return

    interest = interest.sort_values(x_col)

    # Plot available rate columns
    rate_cols = [c for c in interest.columns if c.startswith("rate_")]
    if rate_cols:
        for col in rate_cols[:5]:
            label = col.replace("rate_", "").replace("_", " ").title()
            ax.plot(interest[x_col], interest[col], linewidth=1.5, label=label, alpha=0.8)
        ax.set_ylabel("Interest Rate (%)", fontsize=12)
        ax.set_title("U.S. Treasury Average Interest Rates by Security Type",
                     fontsize=14, fontweight="bold")
    elif "pct_maturing_1yr" in interest.columns:
        ax.plot(interest[x_col], interest["pct_maturing_1yr"],
                linewidth=2, color="#d62728", label="Maturing within 1yr")
        if "pct_maturing_2yr" in interest.columns:
            ax.plot(interest[x_col], interest["pct_maturing_2yr"],
                    linewidth=2, color="#ff7f0e", label="Maturing within 2yr")
        ax.set_ylabel("% of Outstanding", fontsize=12)
        ax.set_title("U.S. Treasury Refinancing Risk", fontsize=14, fontweight="bold")
    else:
        logger.warning("No plottable columns in interest data")
        return

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.legend(fontsize=10)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "us_fiscal_interest_cost.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved us_fiscal_interest_cost.png")


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    pdf_dir = ensure_pdf_dir()
    out = output_data_dir()

    deep_dive_file = out / "us_fiscal_deep_dive.xlsx"
    mts = read_excel_safe(out / "us_mts_panel.xlsx")

    chart_receipts(mts, pdf_dir)
    chart_outlays(mts, pdf_dir)

    if deep_dive_file.exists():
        chart_interest_cost(deep_dive_file, pdf_dir)
    else:
        logger.warning("us_fiscal_deep_dive.xlsx not found; skipping interest cost chart")

    charts = list(pdf_dir.glob("us_fiscal_*.png"))
    logger.info(f"[{MANIFEST['id']}] Done. Generated {len(charts)} charts")


if __name__ == "__main__":
    run()
