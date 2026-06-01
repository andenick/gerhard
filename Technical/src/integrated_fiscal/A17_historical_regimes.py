"""
A17: Historical Fiscal Regimes (JST 1870-2020)
================================================
Identifies distinct fiscal regimes across 150 years using clustering,
analyzes r-g dynamics, and connects crises to fiscal space.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logging_setup import setup_logging
from utils.paths import raw_data_dir, output_data_dir
from utils.data_io import write_single_sheet_excel

logger = setup_logging(__name__)

JST_DIR = raw_data_dir() / "jst"
PWT_DIR = raw_data_dir() / "profit_rates"
OUTPUT_DIR = output_data_dir() / "integrated_fiscal"


def load_jst_full() -> pd.DataFrame:
    """Load full JST dataset."""
    fpath = JST_DIR / "JSTdatasetR6.parquet"
    if not fpath.exists():
        fpath = JST_DIR / "jst_fiscal_panel.parquet"
    if not fpath.exists():
        return pd.DataFrame()
    df = pd.read_parquet(fpath)
    if 'iso' in df.columns:
        df = df.rename(columns={'iso': 'country_code'})
    elif 'country_code' not in df.columns:
        first_str_col = next((c for c in df.columns if df[c].dtype == object), None)
        if first_str_col:
            df = df.rename(columns={first_str_col: 'country_code'})
    logger.info(f"JST: {len(df):,} rows, {df['country_code'].nunique()} countries, "
               f"{df['year'].min()}-{df['year'].max()}")
    return df


def compute_r_minus_g(jst: pd.DataFrame) -> pd.DataFrame:
    """Compute real interest rate minus real growth (r-g) — the key debt sustainability variable."""
    jst = jst.copy()

    # Real long-term rate: ltrate - inflation
    if 'ltrate' in jst.columns and 'cpi' in jst.columns:
        # CPI in JST is price level; compute inflation as % change
        jst['inflation'] = jst.groupby('country_code')['cpi'].pct_change() * 100
        jst['real_rate'] = jst['ltrate'] - jst['inflation']
    elif 'stir' in jst.columns and 'cpi' in jst.columns:
        jst['inflation'] = jst.groupby('country_code')['cpi'].pct_change() * 100
        jst['real_rate'] = jst['stir'] - jst['inflation']
    else:
        return pd.DataFrame()

    # Real GDP growth
    if 'rgdpmad' in jst.columns:
        jst['real_growth'] = jst.groupby('country_code')['rgdpmad'].pct_change() * 100
    elif 'gdp' in jst.columns:
        jst['real_growth'] = jst.groupby('country_code')['gdp'].pct_change() * 100
        jst['real_growth'] = jst['real_growth'] - jst['inflation']  # Deflate nominal
    else:
        return pd.DataFrame()

    jst['r_minus_g'] = jst['real_rate'] - jst['real_growth']
    jst['r_g_favorable'] = jst['r_minus_g'] < 0  # Growth exceeds interest rate

    return jst[['country_code', 'year', 'real_rate', 'real_growth', 'r_minus_g',
                'r_g_favorable', 'inflation']].dropna(subset=['r_minus_g'])


def analyze_r_g_by_era(r_g_panel: pd.DataFrame) -> pd.DataFrame:
    """Average r-g by historical era."""
    if r_g_panel.empty:
        return pd.DataFrame()

    eras = {
        'pre_wwi': (1870, 1913),
        'interwar': (1919, 1938),
        'wwii': (1939, 1945),
        'golden_age': (1946, 1973),
        'stagflation': (1974, 1982),
        'great_moderation': (1983, 2007),
        'post_gfc': (2008, 2020),
    }

    results = []
    for era_name, (start, end) in eras.items():
        era_data = r_g_panel[(r_g_panel['year'] >= start) & (r_g_panel['year'] <= end)]
        if era_data.empty:
            continue

        results.append({
            'era': era_name,
            'start': start, 'end': end,
            'n_obs': len(era_data),
            'avg_real_rate': era_data['real_rate'].mean(),
            'avg_real_growth': era_data['real_growth'].mean(),
            'avg_r_minus_g': era_data['r_minus_g'].mean(),
            'pct_favorable': era_data['r_g_favorable'].mean() * 100,
            'avg_inflation': era_data['inflation'].mean(),
        })

    return pd.DataFrame(results)


def classify_fiscal_regimes(jst: pd.DataFrame) -> pd.DataFrame:
    """Classify country-decades into fiscal regimes using K-means on fiscal vectors."""
    # Build decade-averaged fiscal state vectors
    jst = jst.copy()
    jst['decade'] = (jst['year'] // 10) * 10

    fiscal_vars = ['revenue', 'expenditure', 'debtgdp']
    available = [v for v in fiscal_vars if v in jst.columns]
    if len(available) < 2:
        return pd.DataFrame()

    decade_avg = jst.groupby(['country_code', 'decade'])[available].mean().reset_index()
    decade_avg = decade_avg.dropna()

    if len(decade_avg) < 20:
        return pd.DataFrame()

    # Standardize
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans

    scaler = StandardScaler()
    X = scaler.fit_transform(decade_avg[available])

    # K-means with 4 clusters
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    decade_avg['regime'] = kmeans.fit_predict(X)

    # Label clusters by their characteristics
    cluster_means = decade_avg.groupby('regime')[available].mean()
    logger.info(f"Regime cluster means:\n{cluster_means}")

    # Assign human-readable labels based on characteristics
    labels = {}
    for regime_id in range(4):
        means = cluster_means.loc[regime_id]
        if 'debtgdp' in means and means.get('debtgdp', 0) > cluster_means['debtgdp'].median():
            if means.get('expenditure', 0) > cluster_means['expenditure'].median():
                labels[regime_id] = 'high_debt_high_spend'
            else:
                labels[regime_id] = 'high_debt_constrained'
        else:
            if means.get('revenue', 0) > cluster_means['revenue'].median():
                labels[regime_id] = 'fiscal_expansion'
            else:
                labels[regime_id] = 'minimal_state'

    decade_avg['regime_label'] = decade_avg['regime'].map(labels)
    return decade_avg


def analyze_150yr_trajectory(jst: pd.DataFrame) -> pd.DataFrame:
    """Track the 150-year fiscal trajectory: revenue, expenditure, debt averages."""
    if jst.empty:
        return pd.DataFrame()

    fiscal_vars = ['revenue', 'expenditure', 'debtgdp']
    available = [v for v in fiscal_vars if v in jst.columns]

    results = []
    for year in sorted(jst['year'].unique()):
        yr_data = jst[jst['year'] == year]
        row = {'year': year, 'n_countries': yr_data['country_code'].nunique()}
        for col in available:
            valid = yr_data[col].dropna()
            if len(valid) >= 5:
                row[f'{col}_mean'] = valid.mean()
                row[f'{col}_median'] = valid.median()
                row[f'{col}_std'] = valid.std()
        results.append(row)

    return pd.DataFrame(results)


def fiscal_space_and_crises(jst: pd.DataFrame) -> pd.DataFrame:
    """Analyze fiscal space before banking crises and post-crisis fiscal cost."""
    if 'crisisJST' not in jst.columns or 'debtgdp' not in jst.columns:
        return pd.DataFrame()

    jst = jst.sort_values(['country_code', 'year']).copy()
    jst['crisis_start'] = (jst['crisisJST'] == 1) & (jst.groupby('country_code')['crisisJST'].shift(1) != 1)

    events = jst[jst['crisis_start']].copy()
    results = []

    for _, event in events.iterrows():
        country = event['country_code']
        t0 = event['year']

        window = jst[(jst['country_code'] == country) &
                     (jst['year'] >= t0 - 5) & (jst['year'] <= t0 + 5)]
        if len(window) < 6:
            continue

        pre = window[window['year'] < t0]
        post = window[window['year'] > t0]

        row = {
            'country_code': country,
            'crisis_year': int(t0),
            'debt_at_crisis': event.get('debtgdp', np.nan),
            'debt_pre_5yr_avg': pre['debtgdp'].mean() if not pre.empty else np.nan,
        }

        if not post.empty and 'debtgdp' in post.columns:
            post_debt = post['debtgdp'].iloc[-1] if len(post) > 0 else np.nan
            row['debt_post_5yr'] = post_debt
            row['fiscal_cost_pp'] = (post_debt - event.get('debtgdp', 0)) * 100

        # Was revenue falling before crisis?
        if 'revenue' in pre.columns and len(pre) >= 3:
            rev_trend = np.polyfit(range(len(pre)), pre['revenue'].values, 1)[0]
            row['pre_crisis_revenue_trend'] = rev_trend

        results.append(row)

    return pd.DataFrame(results)


def run() -> dict:
    logger.info("=" * 80)
    logger.info("A17: HISTORICAL FISCAL REGIMES (1870-2020)")
    logger.info("=" * 80)

    jst = load_jst_full()
    if jst.empty:
        return {}

    # r-g dynamics
    r_g = compute_r_minus_g(jst)
    if not r_g.empty:
        write_single_sheet_excel(r_g.head(50000), OUTPUT_DIR / "A17_r_minus_g_panel.xlsx", "R_G")
        logger.info(f"r-g panel: {len(r_g):,} obs")

        era_analysis = analyze_r_g_by_era(r_g)
        if not era_analysis.empty:
            write_single_sheet_excel(era_analysis, OUTPUT_DIR / "A17_r_g_by_era.xlsx", "Eras")
            logger.info("r-g by era:")
            for _, row in era_analysis.iterrows():
                logger.info(f"  {row['era']:20s}: r-g = {row['avg_r_minus_g']:+.1f}pp "
                           f"(r={row['avg_real_rate']:.1f}, g={row['avg_real_growth']:.1f})")

    # 150-year trajectory
    trajectory = analyze_150yr_trajectory(jst)
    if not trajectory.empty:
        write_single_sheet_excel(trajectory, OUTPUT_DIR / "A17_150yr_trajectory.xlsx", "Trajectory")
        logger.info(f"150-year trajectory: {len(trajectory)} years")

    # Regime classification
    try:
        regimes = classify_fiscal_regimes(jst)
        if not regimes.empty:
            write_single_sheet_excel(regimes, OUTPUT_DIR / "A17_fiscal_regimes.xlsx", "Regimes")
            logger.info(f"Fiscal regimes: {len(regimes)} country-decades classified")
            logger.info(f"Regime distribution: {regimes['regime_label'].value_counts().to_dict()}")
    except ImportError:
        logger.warning("sklearn not available — skipping regime clustering")
    except Exception as e:
        logger.warning(f"Regime classification failed: {e}")

    # Fiscal space + crises
    crisis_analysis = fiscal_space_and_crises(jst)
    if not crisis_analysis.empty:
        write_single_sheet_excel(crisis_analysis, OUTPUT_DIR / "A17_fiscal_space_crises.xlsx", "CrisisSpace")
        avg_cost = crisis_analysis['fiscal_cost_pp'].dropna().mean()
        logger.info(f"Banking crises: {len(crisis_analysis)} events, "
                   f"avg fiscal cost: {avg_cost:.1f} pp of GDP")

    logger.info("A17 COMPLETE")
    return {'r_g_obs': len(r_g) if not r_g.empty else 0}


if __name__ == "__main__":
    run()
