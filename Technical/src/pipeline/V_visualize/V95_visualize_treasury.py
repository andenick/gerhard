#!/usr/bin/env python3
"""
V95: Visualize Treasury
Generate 6 key charts for Treasury market analysis.
Stage: V | ID: V95
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
from utils.paths import output_data_dir, raw_data_dir
from utils.data_io import read_excel_safe
from utils.config import project_root

logger = setup_logging(__name__)

MANIFEST = {
    "id": "V95",
    "name": "Visualize Treasury",
    "stage": "V",
    "description": "Generate 6 key Treasury market visualization charts",
    "depends_on": ["A170", "A175", "A180", "A185"],
    "inputs": [
        {"path": "Output/Data/treasury_market_structure.xlsx", "required": True},
        {"path": "Output/Data/yield_curve_daily.xlsx", "required": True},
        {"path": "Output/Data/yield_curve_monthly.xlsx", "required": True},
        {"path": "Output/Data/treasury_duration_analysis.xlsx", "required": True},
    ],
    "outputs": [
        {"path": "Output/PDFs/treasury_market_size.png"},
        {"path": "Output/PDFs/treasury_yield_curve_snapshot.png"},
        {"path": "Output/PDFs/treasury_yield_heatmap.png"},
        {"path": "Output/PDFs/treasury_term_spread.png"},
        {"path": "Output/PDFs/treasury_portfolio_duration.png"},
        {"path": "Output/PDFs/treasury_refinancing_wall.png"},
    ],
    "timeout": 180,
    "parallel_safe": True,
}

# Professional style
plt.style.use("seaborn-v0_8-whitegrid")
COLORS = {
    "Bills": "#1f77b4",
    "Notes": "#ff7f0e",
    "Bonds": "#2ca02c",
    "TIPS": "#d62728",
    "FRN": "#9467bd",
}
DPI = 300


def ensure_pdf_dir():
    """Ensure Output/PDFs directory exists."""
    pdf_dir = project_root() / "Output" / "PDFs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir


def chart_market_size(pdf_dir):
    """Chart 1: Stacked area chart of Treasury outstanding by type."""
    logger.info("Chart 1: Treasury market size...")
    df = read_excel_safe(project_root() / "Output" / "Data" / "treasury_market_structure.xlsx")
    if df.empty:
        logger.warning("No market structure data")
        return

    df["record_date"] = pd.to_datetime(df["record_date"])
    df = df.sort_values("record_date")

    fig, ax = plt.subplots(figsize=(14, 7))

    types_cols = []
    labels = []
    colors = []
    for stype in ["Bills", "Notes", "Bonds", "TIPS", "FRN"]:
        col = f"{stype.lower()}_outstanding_bil"
        if col in df.columns:
            types_cols.append(col)
            labels.append(stype)
            colors.append(COLORS.get(stype, "#888888"))

    if types_cols:
        # Fill NaN with 0 for stacking
        plot_data = df[types_cols].fillna(0)
        ax.stackplot(df["record_date"], *[plot_data[c] for c in types_cols],
                     labels=labels, colors=colors, alpha=0.85)

    ax.set_title("U.S. Treasury Marketable Debt Outstanding", fontsize=16, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Outstanding ($ Billions)", fontsize=12)
    ax.legend(loc="upper left", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}B"))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_market_size.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_market_size.png")


def chart_yield_curve_snapshot(pdf_dir):
    """Chart 2: Current yield curve vs historical snapshots."""
    logger.info("Chart 2: Yield curve snapshot...")
    df = read_excel_safe(project_root() / "Output" / "Data" / "yield_curve_daily.xlsx")
    if df.empty:
        logger.warning("No daily yield data")
        return

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    maturities = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3",
                   "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]
    mat_years = [1/12, 3/12, 6/12, 1, 2, 3, 5, 7, 10, 20, 30]
    mat_labels = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]

    # Find snapshots: latest, 1yr ago, 5yr ago, 10yr ago
    latest_date = df["date"].max()
    target_offsets = {"Current": 0, "1Y Ago": 365, "5Y Ago": 365*5, "10Y Ago": 365*10}
    snapshot_colors = {"Current": "#d62728", "1Y Ago": "#ff7f0e", "5Y Ago": "#2ca02c", "10Y Ago": "#1f77b4"}

    fig, ax = plt.subplots(figsize=(12, 7))

    for label, offset in target_offsets.items():
        target = latest_date - pd.Timedelta(days=offset)
        # Find nearest date
        idx = (df["date"] - target).abs().idxmin()
        row = df.loc[idx]
        actual_date = row["date"]

        yields = []
        for col in maturities:
            val = pd.to_numeric(row.get(col, np.nan), errors="coerce")
            yields.append(val)

        # Filter out NaN for plotting
        valid = [(m, y, l) for m, y, l in zip(mat_years, yields, mat_labels) if pd.notna(y)]
        if valid:
            ms, ys, _ = zip(*valid)
            ax.plot(ms, ys, marker="o", markersize=5, linewidth=2.5,
                    label=f"{label} ({actual_date.strftime('%Y-%m-%d')})",
                    color=snapshot_colors[label])

    ax.set_title("U.S. Treasury Yield Curve Snapshots", fontsize=16, fontweight="bold")
    ax.set_xlabel("Maturity (Years)", fontsize=12)
    ax.set_ylabel("Yield (%)", fontsize=12)
    ax.set_xticks(mat_years)
    ax.set_xticklabels(mat_labels, rotation=45)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_yield_curve_snapshot.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_yield_curve_snapshot.png")


def chart_yield_heatmap(pdf_dir):
    """Chart 3: Heatmap of monthly yields by maturity."""
    logger.info("Chart 3: Yield heatmap...")
    df = read_excel_safe(project_root() / "Output" / "Data" / "yield_curve_monthly.xlsx")
    if df.empty:
        logger.warning("No monthly yield data")
        return

    df["month_end"] = pd.to_datetime(df["month_end"])
    df = df.sort_values("month_end")

    # Focus on post-2000 for readability
    df = df[df["month_end"] >= "2000-01-01"].copy()

    maturities = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3",
                   "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]
    available = [c for c in maturities if c in df.columns]

    if not available:
        logger.warning("No maturity columns for heatmap")
        return

    heat_data = df.set_index("month_end")[available]

    fig, ax = plt.subplots(figsize=(14, 10))
    im = ax.pcolormesh(range(len(available)), heat_data.index,
                        heat_data.values, cmap="RdYlGn_r", shading="auto")

    ax.set_xticks(range(len(available)))
    ax.set_xticklabels([c.replace("DGS", "") for c in available], fontsize=10)
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_locator(mdates.YearLocator(2))

    cbar = plt.colorbar(im, ax=ax, label="Yield (%)", pad=0.02)
    ax.set_title("Treasury Yield Heatmap by Maturity (2000-Present)", fontsize=16, fontweight="bold")
    ax.set_xlabel("Maturity", fontsize=12)
    ax.set_ylabel("")
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_yield_heatmap.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_yield_heatmap.png")


def chart_term_spread(pdf_dir):
    """Chart 4: 10Y-2Y term spread with inversion shading."""
    logger.info("Chart 4: Term spread...")
    df = read_excel_safe(project_root() / "Output" / "Data" / "yield_curve_monthly.xlsx")
    if df.empty:
        logger.warning("No monthly yield data")
        return

    df["month_end"] = pd.to_datetime(df["month_end"])
    df = df.sort_values("month_end")
    df = df.dropna(subset=["term_spread_10y2y"])

    fig, ax = plt.subplots(figsize=(14, 6))

    # Plot spread
    ax.plot(df["month_end"], df["term_spread_10y2y"], color="#1f77b4", linewidth=1.5)
    ax.axhline(y=0, color="black", linewidth=1, linestyle="-")

    # Shade inversions
    inverted = df["term_spread_10y2y"] < 0
    ax.fill_between(df["month_end"], df["term_spread_10y2y"], 0,
                    where=inverted, color="#d62728", alpha=0.3, label="Inverted")
    ax.fill_between(df["month_end"], df["term_spread_10y2y"], 0,
                    where=~inverted, color="#2ca02c", alpha=0.15, label="Normal")

    ax.set_title("10-Year minus 2-Year Treasury Spread", fontsize=16, fontweight="bold")
    ax.set_xlabel("")
    ax.set_ylabel("Spread (percentage points)", fontsize=12)
    ax.legend(fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_term_spread.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_term_spread.png")


def chart_portfolio_duration(pdf_dir):
    """Chart 5: Weighted average duration of Treasury portfolio."""
    logger.info("Chart 5: Portfolio duration...")
    df = read_excel_safe(project_root() / "Output" / "Data" / "treasury_duration_analysis.xlsx")
    if df.empty:
        logger.warning("No duration data")
        return

    df["record_date"] = pd.to_datetime(df["record_date"])
    df = df.sort_values("record_date")

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # Duration line
    ax1.plot(df["record_date"], df["portfolio_duration_years"],
             color="#1f77b4", linewidth=2.5, label="Portfolio Duration")
    ax1.set_ylabel("Duration (Years)", fontsize=12, color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")

    # Add component durations if available
    for stype, color in [("notes", "#ff7f0e"), ("bonds", "#2ca02c"), ("bills", "#d62728")]:
        col = f"{stype}_duration"
        if col in df.columns:
            ax1.plot(df["record_date"], df[col], linewidth=1, alpha=0.6,
                     color=color, linestyle="--", label=f"{stype.title()}")

    # Total outstanding on right axis
    ax2 = ax1.twinx()
    ax2.fill_between(df["record_date"], df["total_outstanding_bil"],
                      alpha=0.1, color="#888888")
    ax2.set_ylabel("Total Outstanding ($ Billions)", fontsize=12, color="#888888")
    ax2.tick_params(axis="y", labelcolor="#888888")

    ax1.set_title("Treasury Portfolio Duration and Outstanding", fontsize=16, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=10)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator(2))
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_portfolio_duration.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_portfolio_duration.png")


def chart_refinancing_wall(pdf_dir):
    """Chart 6: Maturity wall - securities maturing by year."""
    logger.info("Chart 6: Refinancing wall...")
    raw = raw_data_dir() / "treasury"
    df = pd.read_csv(raw / "mspd_table_3_market.csv", low_memory=False)

    df["record_date"] = pd.to_datetime(df["record_date"], errors="coerce")
    df["maturity_date"] = pd.to_datetime(df["maturity_date"], errors="coerce")
    df["outstanding_amt"] = pd.to_numeric(df["outstanding_amt"], errors="coerce")

    # Use latest record date
    latest = df["record_date"].max()
    current = df[df["record_date"] == latest].copy()
    current = current[current["outstanding_amt"].notna() & (current["outstanding_amt"] > 0)]
    current = current[current["maturity_date"].notna()]

    current["maturity_year"] = current["maturity_date"].dt.year

    # Security type classification
    type_map = {
        "Bills Maturity Value": "Bills",
        "Notes": "Notes",
        "Bonds": "Bonds",
        "Inflation-Protected Securities": "TIPS",
        "Inflation-Indexed Notes": "TIPS",
        "Inflation-Indexed Bonds": "TIPS",
        "Floating Rate Notes": "FRN",
    }
    current["sec_type"] = current["security_class1_desc"].map(type_map)
    current = current[current["sec_type"].notna()]

    # Aggregate by maturity year and type
    wall = current.groupby(["maturity_year", "sec_type"])["outstanding_amt"].sum().reset_index()
    wall["outstanding_bil"] = wall["outstanding_amt"] / 1000.0

    # Focus on next 10 years
    current_year = latest.year
    wall = wall[(wall["maturity_year"] >= current_year) & (wall["maturity_year"] <= current_year + 10)]

    fig, ax = plt.subplots(figsize=(14, 7))

    # Stacked bar chart
    years = sorted(wall["maturity_year"].unique())
    bottom = np.zeros(len(years))

    for stype in ["Bills", "Notes", "Bonds", "TIPS", "FRN"]:
        vals = []
        for yr in years:
            v = wall[(wall["maturity_year"] == yr) & (wall["sec_type"] == stype)]["outstanding_bil"].sum()
            vals.append(v)
        vals = np.array(vals)
        ax.bar(years, vals, bottom=bottom, label=stype,
               color=COLORS.get(stype, "#888888"), alpha=0.85, width=0.7)
        bottom += vals

    ax.set_title(f"Treasury Maturity Wall (as of {latest.strftime('%Y-%m-%d')})",
                 fontsize=16, fontweight="bold")
    ax.set_xlabel("Maturity Year", fontsize=12)
    ax.set_ylabel("Outstanding ($ Billions)", fontsize=12)
    ax.set_xticks(years)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}B"))
    ax.legend(fontsize=11)
    plt.tight_layout()
    plt.savefig(pdf_dir / "treasury_refinancing_wall.png", dpi=DPI, bbox_inches="tight")
    plt.close()
    logger.info("  Saved treasury_refinancing_wall.png")


def run():
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    pdf_dir = ensure_pdf_dir()
    logger.info(f"Output directory: {pdf_dir}")

    chart_market_size(pdf_dir)
    chart_yield_curve_snapshot(pdf_dir)
    chart_yield_heatmap(pdf_dir)
    chart_term_spread(pdf_dir)
    chart_portfolio_duration(pdf_dir)
    chart_refinancing_wall(pdf_dir)

    # Count outputs
    charts = list(pdf_dir.glob("treasury_*.png"))
    logger.info(f"[{MANIFEST['id']}] Done. Generated {len(charts)} charts")


if __name__ == "__main__":
    run()
