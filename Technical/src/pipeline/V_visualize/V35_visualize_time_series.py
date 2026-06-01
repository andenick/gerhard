#!/usr/bin/env python3
"""
V35: Time Series Visualizations
Charts for structural breaks, trends, convergence.
Stage: V | ID: V35
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
    "id": "V35",
    "name": "Time Series Visualizations",
    "stage": "V",
    "description": "Charts for structural breaks, trends, convergence",
    "depends_on": ["A80", "A82", "A84"],
    "inputs": [
        {"path": "Output/Data/structural_breaks.xlsx", "required": False},
        {"path": "Output/Data/trend_decomposition.xlsx", "required": False},
        {"path": "Output/Data/convergence_analysis.xlsx", "required": False},
    ],
    "outputs": [],
    "timeout": 120,
    "parallel_safe": True,
}

# Professional B&W style
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


def plot_sigma_convergence(df_conv):
    """Line plot of cross-country std dev of tax-to-GDP over time."""
    logger.info("Creating sigma convergence plot...")

    # Check for sigma convergence data
    if "year" not in df_conv.columns:
        logger.warning("No 'year' column in convergence data, skipping sigma convergence")
        return

    # Look for sigma/std columns
    sigma_col = None
    for candidate in ["sigma", "std_dev", "cross_country_std", "std_tax", "coefficient_of_variation"]:
        if candidate in df_conv.columns:
            sigma_col = candidate
            break

    if sigma_col is None:
        # Try to compute from master panel
        master = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
        if master.empty:
            logger.warning("Cannot compute sigma convergence, skipping")
            return
        sigma_data = master.dropna(subset=["tax_revenue_pct_gdp"]).groupby("year").agg(
            std_dev=("tax_revenue_pct_gdp", "std"),
            n_countries=("country_code", "nunique"),
        ).reset_index()
        sigma_data = sigma_data[sigma_data["n_countries"] >= 20]
    else:
        sigma_data = df_conv[["year", sigma_col]].dropna().rename(columns={sigma_col: "std_dev"})

    if sigma_data.empty or len(sigma_data) < 5:
        logger.warning("Insufficient sigma convergence data")
        return

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(sigma_data["year"], sigma_data["std_dev"], color="black", linewidth=2, marker="o", markersize=3)
    ax.set_xlabel("Year")
    ax.set_ylabel("Cross-Country Std Dev (Tax/GDP %)")
    ax.set_title("Sigma Convergence: Tax-to-GDP Dispersion Over Time")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "sigma_convergence.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_beta_convergence(df_conv):
    """Scatter: initial tax level vs growth rate with regression line."""
    logger.info("Creating beta convergence scatter...")

    # Look for initial level and growth columns
    init_col = None
    growth_col = None
    for c in df_conv.columns:
        cl = c.lower()
        if "initial" in cl or "start" in cl or "base" in cl:
            init_col = c
        if "growth" in cl or "change" in cl or "delta" in cl:
            growth_col = c

    if init_col is None or growth_col is None:
        # Compute from master panel
        master = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
        if master.empty:
            logger.warning("Cannot compute beta convergence, skipping")
            return
        tax = master.dropna(subset=["tax_revenue_pct_gdp"]).sort_values(["country_code", "year"])
        first = tax.groupby("country_code").first()[["tax_revenue_pct_gdp"]].rename(columns={"tax_revenue_pct_gdp": "initial_tax"})
        last = tax.groupby("country_code").last()[["tax_revenue_pct_gdp"]].rename(columns={"tax_revenue_pct_gdp": "final_tax"})
        years_span = tax.groupby("country_code")["year"].agg(["min", "max"])
        beta_data = first.join(last).join(years_span)
        beta_data["years"] = beta_data["max"] - beta_data["min"]
        beta_data = beta_data[beta_data["years"] >= 10]
        beta_data["annual_change"] = (beta_data["final_tax"] - beta_data["initial_tax"]) / beta_data["years"]
    else:
        beta_data = df_conv[[init_col, growth_col]].dropna().rename(
            columns={init_col: "initial_tax", growth_col: "annual_change"}
        )

    if beta_data.empty or len(beta_data) < 10:
        logger.warning("Insufficient beta convergence data")
        return

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.scatter(beta_data["initial_tax"], beta_data["annual_change"],
               color="gray", edgecolors="black", alpha=0.6, s=30)

    # Regression line
    mask = beta_data[["initial_tax", "annual_change"]].notna().all(axis=1)
    x = beta_data.loc[mask, "initial_tax"].values
    y = beta_data.loc[mask, "annual_change"].values
    if len(x) > 5:
        slope, intercept = np.polyfit(x, y, 1)
        x_line = np.linspace(x.min(), x.max(), 100)
        ax.plot(x_line, intercept + slope * x_line, color="black", linewidth=2,
                linestyle="--", label=f"slope={slope:.4f}")
        ax.legend()

    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.set_xlabel("Initial Tax-to-GDP (%)")
    ax.set_ylabel("Annual Change in Tax-to-GDP (pp/year)")
    ax.set_title("Beta Convergence: Initial Level vs. Subsequent Change")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "beta_convergence.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_g7_trends(df_trends):
    """HP trend vs actual for G7 countries."""
    logger.info("Creating G7 trend decomposition plot...")

    G7 = {"USA": "United States", "GBR": "United Kingdom", "DEU": "Germany",
           "FRA": "France", "JPN": "Japan", "CAN": "Canada", "ITA": "Italy"}

    # Check if trends data has what we need
    has_trend = False
    trend_col = None
    actual_col = None
    for c in df_trends.columns:
        cl = c.lower()
        if "trend" in cl and "hp" in cl:
            trend_col = c
            has_trend = True
        elif "actual" in cl or "tax_revenue" in cl:
            actual_col = c

    if not has_trend:
        # Try to use master panel directly
        master = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
        if master.empty:
            logger.warning("No trend data available, skipping G7 trends")
            return
        df_src = master
        actual_col = "tax_revenue_pct_gdp"
        # Compute HP trend manually
        has_trend = False
    else:
        df_src = df_trends

    fig, axes = plt.subplots(3, 3, figsize=(16, 14))
    axes = axes.flatten()

    plot_idx = 0
    for code, name in G7.items():
        if plot_idx >= 7:
            break
        ax = axes[plot_idx]
        grp = df_src[df_src["country_code"] == code].sort_values("year")

        if grp.empty or actual_col not in grp.columns:
            ax.text(0.5, 0.5, f"{name}\nNo data", ha="center", va="center", transform=ax.transAxes)
            ax.set_title(name)
            plot_idx += 1
            continue

        grp = grp.dropna(subset=[actual_col])
        ax.plot(grp["year"], grp[actual_col], color="gray", linewidth=1, label="Actual", alpha=0.7)

        if has_trend and trend_col in grp.columns:
            ax.plot(grp["year"], grp[trend_col], color="black", linewidth=2, label="HP Trend")
        else:
            # Simple moving average as trend proxy
            if len(grp) >= 5:
                grp_sorted = grp.sort_values("year")
                ma = grp_sorted[actual_col].rolling(window=5, center=True).mean()
                ax.plot(grp_sorted["year"], ma, color="black", linewidth=2, label="5-yr MA Trend")

        ax.set_title(name, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Tax/GDP %")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        plot_idx += 1

    # Hide unused subplots
    for i in range(plot_idx, len(axes)):
        axes[i].set_visible(False)

    fig.suptitle("G7 Tax-to-GDP: Actual vs Trend", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    out = VIZ_DIR / "g7_trend_decomposition.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_structural_breaks(df_breaks):
    """Top 10 countries with most significant breaks, before/after means."""
    logger.info("Creating structural breaks plot...")

    if df_breaks.empty:
        logger.warning("No structural breaks data")
        return

    # Find relevant columns
    country_col = "country_code"
    f_col = None
    before_col = None
    after_col = None
    for c in df_breaks.columns:
        cl = c.lower()
        if "f_stat" in cl or "f_value" in cl or "chow" in cl:
            f_col = c
        if "before" in cl and "mean" in cl:
            before_col = c
        if "after" in cl and "mean" in cl:
            after_col = c

    if f_col is None:
        # Use p-value instead
        for c in df_breaks.columns:
            if "p_val" in c.lower():
                f_col = c
                break

    if f_col is None:
        logger.warning("Cannot identify break significance column, skipping")
        return

    # Top 10 by F-statistic
    top10 = df_breaks.nlargest(10, f_col)

    fig, ax = plt.subplots(figsize=(12, 7))

    if before_col and after_col:
        # Paired bar chart: before and after means
        x = np.arange(len(top10))
        width = 0.35
        ax.barh(x - width / 2, top10[before_col], width, label="Before Break", color="gray", edgecolor="black")
        ax.barh(x + width / 2, top10[after_col], width, label="After Break", color="black", alpha=0.7)
        ax.set_yticks(x)
        ax.set_yticklabels(top10[country_col])
        ax.set_xlabel("Tax-to-GDP (%)")
        ax.legend()
    else:
        # Simple horizontal bar of F-statistics
        ax.barh(range(len(top10)), top10[f_col], color="gray", edgecolor="black")
        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels(top10[country_col])
        ax.set_xlabel(f_col)

    ax.set_title("Top 10 Most Significant Structural Breaks in Tax-to-GDP", fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()

    plt.tight_layout()
    out = VIZ_DIR / "structural_breaks_top10.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    charts_created = 0

    # Load available data
    df_breaks = read_excel_safe(DATA_DIR / "structural_breaks.xlsx")
    df_trends = read_excel_safe(DATA_DIR / "trend_decomposition.xlsx")
    df_conv = read_excel_safe(DATA_DIR / "convergence_analysis.xlsx")

    # If convergence_analysis doesn't exist, try the international one
    if df_conv.empty:
        df_conv = read_excel_safe(DATA_DIR / "international_convergence_analysis.xlsx")

    # 1. Sigma convergence
    try:
        plot_sigma_convergence(df_conv)
        charts_created += 1
    except Exception as e:
        logger.warning(f"Sigma convergence plot failed: {e}")

    # 2. Beta convergence
    try:
        plot_beta_convergence(df_conv)
        charts_created += 1
    except Exception as e:
        logger.warning(f"Beta convergence plot failed: {e}")

    # 3. G7 trend decomposition
    if not df_trends.empty:
        try:
            plot_g7_trends(df_trends)
            charts_created += 1
        except Exception as e:
            logger.warning(f"G7 trends plot failed: {e}")
    else:
        # Fall back to master panel
        master = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
        if not master.empty:
            try:
                plot_g7_trends(master)
                charts_created += 1
            except Exception as e:
                logger.warning(f"G7 trends plot (from master) failed: {e}")

    # 4. Structural breaks
    if not df_breaks.empty:
        try:
            plot_structural_breaks(df_breaks)
            charts_created += 1
        except Exception as e:
            logger.warning(f"Structural breaks plot failed: {e}")
    else:
        logger.info("No structural_breaks.xlsx found, skipping breaks chart")

    logger.info(f"\nCreated {charts_created} time series visualizations")
    plt.close("all")


if __name__ == "__main__":
    run()
