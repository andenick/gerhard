"""Vendor front-end assets so the site has zero runtime CDN dependency."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config as C  # noqa: E402

VENDOR = C.STATIC_DIR / "vendor"


def vendor_plotly() -> bool:
    try:
        import plotly
    except ImportError:
        print("plotly not installed"); return False
    pkg = Path(plotly.__file__).parent
    for cand in [pkg / "package_data" / "plotly.min.js", pkg / "offline" / "plotly.min.js"]:
        if cand.exists():
            VENDOR.mkdir(parents=True, exist_ok=True)
            shutil.copy(cand, VENDOR / "plotly.min.js")
            print(f"vendored plotly.min.js ({cand.stat().st_size // 1024} KB) <- {cand}")
            return True
    print("could not locate plotly.min.js in package")
    return False


def vendor_htmx() -> bool:
    VENDOR.mkdir(parents=True, exist_ok=True)
    try:
        import requests
        r = requests.get("https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js", timeout=20)
        if r.ok:
            (VENDOR / "htmx.min.js").write_text(r.text, encoding="utf-8")
            print(f"vendored htmx.min.js ({len(r.text) // 1024} KB)"); return True
    except Exception as e:  # noqa: BLE001
        print(f"htmx vendor skipped ({e})")
    return False


if __name__ == "__main__":
    vendor_plotly()
    vendor_htmx()
