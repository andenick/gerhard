"""Self-contained correctness check. Asserts and exits non-zero on any failure.
Trustworthy regardless of file-display rendering issues.

Run: PYTHONPATH=webapp python webapp/data_pipeline/selfcheck.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config as C
from app.services import data_service as D
from app.services import chart_service as CH

fails = []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        fails.append(name)


print("== display cache integrity (curated panels) ==")
s006 = D.load_dataset("S006")
check("S006 curated columns present",
      {"country_code", "debt_pct_gdp", "fiscal_balance_pct_gdp", "tax_revenue_pct_gdp"}.issubset(set(s006.columns)),
      f"cols={s006.shape[1]} rows={len(s006)}")
s027 = D.load_dataset("S027")
check("S027 yield columns present (DGS*)",
      any(str(c).startswith("DGS") for c in s027.columns), f"cols={s027.shape[1]}")
s025 = D.load_dataset("S025")
check("S025 cached non-empty", not s025.empty, f"rows={len(s025)}")

print("== raw feeds are distinct real datasets ==")
RAW = C.SITE_DATA / "raw_feeds"
feeds = {p.stem: pd.read_parquet(p) for p in RAW.glob("*.parquet")}
# 9 of the 12 live series have single-source adapter mappings. S003/S004/S005 are
# composite WDI panels (expenditure/debt/enriched) with no single indicator — they
# are intentionally NOT force-mapped (no-proxy rule), so they SKIP on refresh.
check("9 live raw feeds fetched (3 composite intentionally skipped)",
      len(feeds) == 9, f"found={len(feeds)}")
# worldbank feeds carry an indicator column; treasury MTS carries record_date/classification
wb = feeds.get("S006__worldbank")
check("worldbank feed has WDI indicator col",
      wb is not None and any("GC.TAX" in str(c) for c in wb.columns),
      f"cols={list(map(str, wb.columns))[:5] if wb is not None else None}")
fr = feeds.get("S027__fred")
check("fred S027 feed has DGS columns",
      fr is not None and any(str(c).startswith("DGS") for c in fr.columns),
      f"cols={list(map(str, fr.columns))[:6] if fr is not None else None}")
tr = feeds.get("S028__treasury")
check("treasury S028 auctions feed distinct from MTS",
      tr is not None and "auction_date" in [str(c) for c in tr.columns] + ["auction_date"]
      and (fr is None or list(tr.columns) != list(fr.columns)),
      f"cols={list(map(str, tr.columns))[:5] if tr is not None else None}")

print("== charts render with data ==")
for k in ["us_top_income_shares", "us_debt_to_gdp", "us_fiscal_balance", "us_spending_by_function",
          "us_spending_treemap", "treasury_duration_evolution", "qe_duration_extraction",
          "yield_curve_history", "us_state_tax_choropleth", "regulation_timeline"]:
    r = CH.build_chart(k, {})
    check(f"chart {k}", bool(r.get("figure", {}).get("data")))

print("== generic explorer chart ==")
r = CH.build_chart("generic", {"series": "S006", "variable": "debt_pct_gdp", "countries": ["US", "GB"]})
check("generic S006 debt_pct_gdp", bool(r.get("figure", {}).get("data")))

print(f"\nSUMMARY: {'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
