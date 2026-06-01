"""Live refresh orchestrator.

For each live series: fetch via adapter -> validate -> atomically promote the
Parquet cache + bump manifest freshness, OR keep last-good and log the failure.
Honors no-synthetic / no-freeze: a failed fetch never fabricates or overwrites.

Run:  python webapp/data_pipeline/refresh.py [--only treasury|fred|worldbank] [--series S022] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import config as C  # noqa: E402
from data_pipeline import validators  # noqa: E402
from data_pipeline.adapters import treasury_fiscaldata, worldbank, fred  # noqa: E402

ADAPTERS = {"treasury": treasury_fiscaldata, "worldbank": worldbank, "fred": fred}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_log() -> dict:
    return json.loads(C.REFRESH_LOG.read_text(encoding="utf-8")) if C.REFRESH_LOG.exists() else {}


def _save_log(log: dict) -> None:
    C.REFRESH_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


RAW_FEEDS = C.SITE_DATA / "raw_feeds"


def _atomic_write_parquet(df: pd.DataFrame, path) -> None:
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def refresh_series(sid: str, adapter_name: str, log: dict) -> tuple[bool, str]:
    """Fetch raw source data and snapshot it to raw_feeds/ (NOT the display cache).

    The display cache holds curated LEPAVR panels; overwriting them with a raw API
    dump would change the schema the charts depend on. Refresh therefore keeps a
    validated raw snapshot + freshness stamp. Turning raw feeds into display panels
    is a deliberate pipeline/rebuild step. A failed fetch keeps the last-good
    snapshot (no freeze, no fabrication).
    """
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        return False, f"unknown adapter {adapter_name}"
    RAW_FEEDS.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_FEEDS / f"{sid}__{adapter_name}.parquet"
    old = None
    if raw_path.exists():
        try:
            old = pd.read_parquet(raw_path)
        except Exception:
            old = None
    try:
        new = adapter.fetch(sid)
    except Exception as e:  # noqa: BLE001
        return False, f"fetch error: {e}"
    ok, reason = validators.validate_fetch(new, old)
    if not ok:
        return False, f"validation failed: {reason} (kept last-good)"
    _atomic_write_parquet(new, raw_path)
    log.setdefault(adapter_name, {})[sid] = {"last_refresh": _now(), "rows": int(len(new)),
                                             "raw_feed": f"raw_feeds/{sid}__{adapter_name}.parquet"}
    return True, f"snapshot {len(new)} rows -> raw_feeds/"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(ADAPTERS))
    ap.add_argument("--series")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    C.ensure_dirs()
    manifest = json.loads(C.MANIFEST_PATH.read_text(encoding="utf-8")) if C.MANIFEST_PATH.exists() else {"series": {}}
    log = _load_log()

    targets = []
    for sid, e in manifest.get("series", {}).items():
        fr = e.get("freshness") or {}
        if not fr.get("live"):
            continue
        adapter = fr.get("adapter")
        if args.only and adapter != args.only:
            continue
        if args.series and sid != args.series:
            continue
        targets.append((sid, adapter))

    print(f"refresh: {len(targets)} live target(s) at {_now()}")
    n_ok = 0
    for sid, adapter in targets:
        if args.dry_run:
            print(f"  [dry-run] would refresh {sid} via {adapter}")
            continue
        ok, msg = refresh_series(sid, adapter, log)
        print(f"  {'OK ' if ok else 'SKIP'} {sid} ({adapter}): {msg}")
        n_ok += int(ok)

    if not args.dry_run:
        log["_last_run"] = _now()
        _save_log(log)
    print(f"refresh done: {n_ok}/{len(targets)} promoted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
