"""Download service — stream any cached dataset as csv / xlsx / json / parquet."""
from __future__ import annotations

import io
import json

import pandas as pd
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from app import config as C
from app.services import data_service as D

MEDIA = {"csv": "text/csv",
         "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
         "json": "application/json", "parquet": "application/octet-stream"}


def _prov(key: str) -> str:
    entry = D.dataset_entry(key) or {}
    prov = entry.get("provenance", {}) or {}
    src = prov.get("source") or entry.get("source") or "Gerhard"
    return f"# Gerhard — {entry.get('name', key)} | source: {src} | exported from Gerhard website\n"


def stream(key: str, fmt: str):
    fmt = fmt.lower()
    if fmt not in MEDIA:
        raise HTTPException(400, f"Unsupported format '{fmt}'")
    df = D.load_dataset(key)
    if df.empty:
        raise HTTPException(404, f"No data for '{key}'")
    filename = f"gerhard_{key}.{fmt}"

    if fmt == "parquet":
        path = C.CACHE_DIR / f"{key}.parquet"
        if path.exists():
            return FileResponse(path, media_type=MEDIA[fmt], filename=filename)
        buf = io.BytesIO(); df.to_parquet(buf, index=False); buf.seek(0)
    elif fmt == "csv":
        buf = io.BytesIO((_prov(key) + df.to_csv(index=False)).encode("utf-8"))
    elif fmt == "json":
        payload = {"dataset": key, "provenance": (D.dataset_entry(key) or {}).get("provenance"),
                   "records": json.loads(df.to_json(orient="records"))}
        buf = io.BytesIO(json.dumps(payload, default=str).encode("utf-8"))
    else:  # xlsx
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xl:
            df.to_excel(xl, index=False, sheet_name="data")
        buf.seek(0)

    buf.seek(0)
    return StreamingResponse(buf, media_type=MEDIA[fmt],
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
