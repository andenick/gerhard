"""
Pipeline: Cluster Analysis
Data-driven country groupings by fiscal profile using K-means.
Project: Gerhard
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import output_data_dir
from utils.data_io import write_single_sheet_excel, read_excel_safe

logger = setup_logging(__name__)


def _clean_country_name(val):
    """Parse dict-like country name strings from WB API."""
    if pd.isna(val):
        return val
    s = str(val)
    if s.startswith("{") and "'value'" in s:
        import ast
        try:
            d = ast.literal_eval(s)
            return d.get("value", s)
        except (ValueError, SyntaxError):
            return s
    return val


MANIFEST = {
    "id": "A88",
    "name": "Cluster Analysis",
    "stage": "A",
    "description": "K-means clustering of countries by fiscal profile",
    "depends_on": ["P60"],
    "inputs": [{"path": "Output/Data/master_fiscal_panel.xlsx", "required": True}],
    "outputs": [{"path": "Output/Data/fiscal_clusters.xlsx"}],
    "timeout": 120,
    "parallel_safe": True,
}

DATA_DIR = output_data_dir()

FEATURE_COLS = ["tax_revenue_pct_gdp", "expenditure_pct_gdp", "debt_pct_gdp", "gdp_per_capita_ppp"]


def get_latest_values(df: pd.DataFrame) -> pd.DataFrame:
    """For each country, get the most recent available values for each feature."""
    records = []
    for code, grp in df.groupby("country_code"):
        grp_sorted = grp.sort_values("year", ascending=False)
        row = {"country_code": code}
        row["country_name"] = grp_sorted["country_name"].iloc[0]
        row["region"] = grp_sorted["region"].iloc[0] if "region" in grp_sorted.columns else ""
        row["income_group"] = grp_sorted["income_group"].iloc[0] if "income_group" in grp_sorted.columns else ""

        for col in FEATURE_COLS:
            if col in grp_sorted.columns:
                valid = grp_sorted[grp_sorted[col].notna()]
                row[col] = valid[col].iloc[0] if len(valid) > 0 else np.nan
            else:
                row[col] = np.nan
        records.append(row)
    return pd.DataFrame(records)


def name_cluster(centroid: dict) -> str:
    """Auto-name a cluster based on its centroid values (z-scores)."""
    tax = centroid.get("tax_revenue_pct_gdp", 0)
    exp = centroid.get("expenditure_pct_gdp", 0)
    debt = centroid.get("debt_pct_gdp", 0)
    gdp_pc = centroid.get("gdp_per_capita_ppp", 0)

    # Classify by dominant pattern
    if tax > 0.5 and gdp_pc > 0.5:
        return "High-Tax High-Income"
    elif tax > 0.5 and gdp_pc <= 0.5:
        return "High-Tax Middle-Income"
    elif tax < -0.5 and gdp_pc < -0.5:
        return "Low-Tax Low-Income"
    elif tax < -0.5 and gdp_pc > 0:
        return "Low-Tax Higher-Income"
    elif debt > 0.8:
        return "High-Debt"
    elif exp > 0.5:
        return "High-Spending"
    else:
        return "Moderate-Fiscal"


def run():
    """Main execution function."""
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score

    logger.info(f"[{MANIFEST['id']}] {MANIFEST['name']}")

    # Load data
    df = read_excel_safe(DATA_DIR / "master_fiscal_panel.xlsx")
    if df.empty:
        logger.error("master_fiscal_panel.xlsx not found or empty")
        return

    logger.info(f"Loaded master_fiscal_panel: {len(df)} rows")

    # Clean dict-like country names
    df["country_name"] = df["country_name"].apply(_clean_country_name)

    # Get latest values per country
    latest = get_latest_values(df)
    logger.info(f"Countries with any data: {len(latest)}")

    # Filter: need tax + at least one other variable
    has_tax = latest["tax_revenue_pct_gdp"].notna()
    other_cols = [c for c in FEATURE_COLS if c != "tax_revenue_pct_gdp"]
    has_other = latest[other_cols].notna().any(axis=1)
    filtered = latest[has_tax & has_other].copy()
    logger.info(f"Countries with tax + at least one other variable: {len(filtered)}")

    if len(filtered) < 10:
        logger.error("Too few countries for clustering")
        return

    # Prepare feature matrix — fill NaN with column median for clustering
    available_features = [c for c in FEATURE_COLS if c in filtered.columns and filtered[c].notna().sum() > 10]
    logger.info(f"Features used: {available_features}")

    X = filtered[available_features].copy()
    for col in available_features:
        X[col] = X[col].fillna(X[col].median())

    # Standardize
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Find best k
    best_k, best_score = 3, -1
    k_scores = {}
    for k in range(3, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        k_scores[k] = score
        logger.info(f"  k={k}: silhouette={score:.4f}")
        if score > best_score:
            best_k, best_score = k, score

    logger.info(f"Best k={best_k} (silhouette={best_score:.4f})")

    # Final clustering with best k
    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    filtered["cluster_id"] = km_final.fit_predict(X_scaled)

    # Per-sample silhouette
    sample_silhouettes = silhouette_score(X_scaled, filtered["cluster_id"].values)
    # We can also compute per-sample scores
    from sklearn.metrics import silhouette_samples
    filtered["silhouette_score"] = silhouette_samples(X_scaled, filtered["cluster_id"].values)

    # Name clusters by examining centroids (in z-score space)
    centroids_scaled = km_final.cluster_centers_
    cluster_names = {}
    for i in range(best_k):
        centroid_dict = {feat: centroids_scaled[i, j] for j, feat in enumerate(available_features)}
        cluster_names[i] = name_cluster(centroid_dict)

    # Deduplicate names if needed
    seen = {}
    for k, v in cluster_names.items():
        if v in seen.values():
            cluster_names[k] = f"{v} ({k})"
        seen[k] = cluster_names[k]

    filtered["cluster_name"] = filtered["cluster_id"].map(cluster_names)

    # Log cluster summaries
    logger.info("\nCluster summaries:")
    for cid in range(best_k):
        cmask = filtered["cluster_id"] == cid
        cdata = filtered[cmask]
        logger.info(f"  Cluster {cid} ({cluster_names[cid]}): {len(cdata)} countries")
        for feat in available_features:
            logger.info(f"    {feat}: mean={cdata[feat].mean():.1f}, median={cdata[feat].median():.1f}")

    # Prepare output
    output_cols = ["country_code", "country_name", "cluster_id", "cluster_name"]
    # Add feature columns with short names
    col_rename = {
        "tax_revenue_pct_gdp": "tax_pct_gdp",
        "expenditure_pct_gdp": "expenditure_pct_gdp",
        "debt_pct_gdp": "debt_pct_gdp",
        "gdp_per_capita_ppp": "gdp_per_capita_ppp",
    }
    for orig, short in col_rename.items():
        if orig in filtered.columns:
            if orig != short:
                filtered[short] = filtered[orig]
            output_cols.append(short)

    output_cols.extend(["silhouette_score", "region", "income_group"])
    # Deduplicate columns
    output_cols = list(dict.fromkeys(output_cols))
    existing = [c for c in output_cols if c in filtered.columns]

    results_df = filtered[existing].sort_values(["cluster_id", "country_name"])

    # Save
    output_path = DATA_DIR / "fiscal_clusters.xlsx"
    write_single_sheet_excel(results_df, output_path)
    logger.info(f"Output saved to {output_path}: {len(results_df)} countries in {best_k} clusters")


if __name__ == "__main__":
    run()
