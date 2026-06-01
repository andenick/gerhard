#!/usr/bin/env python3
"""
V45: Econometric Visualizations
Charts for regression coefficients, elasticity, projections.
Stage: V | ID: V45
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
    "id": "V45",
    "name": "Econometric Visualizations",
    "stage": "V",
    "description": "Charts for regression coefficients, elasticity, projections",
    "depends_on": ["A86", "A92", "A96"],
    "inputs": [
        {"path": "Output/Data/tax_elasticity.xlsx", "required": False},
        {"path": "Output/Data/panel_regression_results.xlsx", "required": False},
        {"path": "Output/Data/fiscal_projections_2025_2030.xlsx", "required": False},
    ],
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


def plot_buoyancy_by_income_group(df_elast):
    """Box plot of buoyancy estimates by income group."""
    logger.info("Creating buoyancy by income group plot...")

    if "income_group" not in df_elast.columns or "buoyancy_estimate" not in df_elast.columns:
        logger.warning("Missing income_group or buoyancy_estimate columns")
        return

    df_plot = df_elast.dropna(subset=["buoyancy_estimate", "income_group"])
    df_plot = df_plot[df_plot["income_group"] != ""]

    if len(df_plot) < 5:
        logger.warning("Insufficient data for buoyancy box plot")
        return

    fig, ax = plt.subplots(figsize=(12, 7))

    # Order income groups logically
    order = ["Low income", "Lower middle income", "Upper middle income", "High income"]
    present = [g for g in order if g in df_plot["income_group"].values]
    if not present:
        present = sorted(df_plot["income_group"].unique())

    bp = ax.boxplot(
        [df_plot[df_plot["income_group"] == g]["buoyancy_estimate"].values for g in present],
        labels=present,
        patch_artist=True,
        medianprops=dict(color="black", linewidth=2),
    )

    # Grayscale fills
    grays = ["0.85", "0.65", "0.45", "0.25"]
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(grays[i % len(grays)])
        patch.set_edgecolor("black")

    ax.axhline(y=1, color="black", linewidth=1, linestyle="--", alpha=0.5, label="Unit elasticity")
    ax.set_xlabel("Income Group")
    ax.set_ylabel("Tax Buoyancy Estimate")
    ax.set_title("Tax Buoyancy by Income Group", fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "tax_buoyancy_by_income_group.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_regression_forest(df_reg):
    """Forest plot: coefficient +/- 95% CI for Fixed Effects model."""
    logger.info("Creating regression forest plot...")

    fe = df_reg[df_reg["model"] == "Fixed Effects"].copy()
    if fe.empty:
        # Try any model
        fe = df_reg.copy()
        if fe.empty:
            logger.warning("No regression results for forest plot")
            return

    # Exclude constant
    fe = fe[fe["variable"] != "const"]

    if fe.empty:
        logger.warning("No non-constant coefficients")
        return

    fig, ax = plt.subplots(figsize=(10, max(4, len(fe) * 0.8 + 2)))

    y_pos = np.arange(len(fe))
    coefs = fe["coefficient"].values
    ses = fe["std_error"].values
    ci_95 = 1.96 * ses

    ax.errorbar(coefs, y_pos, xerr=ci_95, fmt="ko", markersize=8, capsize=5,
                linewidth=2, elinewidth=1.5, capthick=1.5)
    ax.axvline(x=0, color="black", linewidth=0.8, linestyle="--")

    ax.set_yticks(y_pos)
    labels = fe["variable"].values
    # Clean up labels for display
    clean = [l.replace("_dm", "").replace("_", " ").title() for l in labels]
    ax.set_yticklabels(clean)
    ax.set_xlabel("Coefficient (with 95% CI)")

    model_name = fe["model"].iloc[0]
    n_obs = fe["n_obs"].iloc[0]
    r2 = fe["r_squared"].iloc[0]
    ax.set_title(f"Panel Regression Coefficients ({model_name})\nn={n_obs}, R²={r2:.4f}",
                 fontweight="bold")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    out = VIZ_DIR / "regression_forest_plot.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def plot_projection_fans(df_proj):
    """Projection fan charts for US, UK, DE: actual + projected with CI bands."""
    logger.info("Creating projection fan charts...")

    countries = {"USA": "United States", "GBR": "United Kingdom", "DEU": "Germany"}

    # Load master panel for actual data
    master = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if master.empty:
        logger.warning("master_fiscal_panel.xlsx needed for projection context")
        return

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for i, (code, name) in enumerate(countries.items()):
        ax = axes[i]

        # Actual data
        actual = master[master["country_code"] == code].dropna(subset=["tax_revenue_pct_gdp"]).sort_values("year")
        if not actual.empty:
            # Show last 20 years for context
            recent = actual[actual["year"] >= actual["year"].max() - 20]
            ax.plot(recent["year"], recent["tax_revenue_pct_gdp"], color="black",
                    linewidth=2, label="Actual")

        # Projections
        proj = df_proj[df_proj["country_code"] == code].sort_values("year")
        if not proj.empty:
            ax.plot(proj["year"], proj["projected_tax_pct"], color="gray",
                    linewidth=2, linestyle="--", label="Projected")

            if "ci_lower" in proj.columns and "ci_upper" in proj.columns:
                ax.fill_between(
                    proj["year"],
                    proj["ci_lower"],
                    proj["ci_upper"],
                    color="gray", alpha=0.2, label="90% CI",
                )

            # Connect actual to projected
            if not actual.empty:
                last_actual = actual.iloc[-1]
                first_proj = proj.iloc[0]
                ax.plot(
                    [last_actual["year"], first_proj["year"]],
                    [last_actual["tax_revenue_pct_gdp"], first_proj["projected_tax_pct"]],
                    color="gray", linewidth=1.5, linestyle=":",
                )

        ax.set_title(name, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Tax-to-GDP (%)")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Tax-to-GDP Projections (2025-2030)", fontsize=16, fontweight="bold")
    plt.tight_layout()
    out = VIZ_DIR / "projection_fans.png"
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"Saved: {out.name}")


def run():
    """Main execution function."""
    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    df_elast = read_excel_safe(DATA_DIR / "tax_elasticity.xlsx")
    df_reg = read_excel_safe(DATA_DIR / "panel_regression_results.xlsx")
    df_proj = read_excel_safe(DATA_DIR / "fiscal_projections_2025_2030.xlsx")

    charts_created = 0

    # 1. Tax buoyancy by income group
    if not df_elast.empty:
        try:
            plot_buoyancy_by_income_group(df_elast)
            charts_created += 1
        except Exception as e:
            logger.warning(f"Buoyancy plot failed: {e}")
    else:
        logger.info("No tax_elasticity.xlsx, skipping buoyancy chart")

    # 2. Regression forest plot
    if not df_reg.empty:
        try:
            plot_regression_forest(df_reg)
            charts_created += 1
        except Exception as e:
            logger.warning(f"Forest plot failed: {e}")
    else:
        logger.info("No panel_regression_results.xlsx, skipping forest plot")

    # 3. Projection fans
    if not df_proj.empty:
        try:
            plot_projection_fans(df_proj)
            charts_created += 1
        except Exception as e:
            logger.warning(f"Projection fan plot failed: {e}")
    else:
        logger.info("No fiscal_projections_2025_2030.xlsx, skipping projections chart")

    logger.info(f"\nCreated {charts_created} econometric visualizations")
    plt.close("all")


if __name__ == "__main__":
    run()
