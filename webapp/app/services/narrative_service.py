"""Narrative service — load authored markdown pages with frontmatter.

Inline directives:
  {{chart:CHART_KEY@Y0-Y1}}  -> hydrating chart placeholder (app.js fills it)
  [cite:KEY]                 -> numbered footnote resolved from citations.json
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from markdown_it import MarkdownIt

from app import config as C

_md = MarkdownIt("commonmark", {"html": True, "linkify": True, "typographer": True})
_CHART_RE = re.compile(r"\{\{chart:([a-zA-Z0-9_]+)(?:@(\d{4})-(\d{4}))?\}\}")
_CITE_RE = re.compile(r"\[cite:([a-zA-Z0-9_]+)\]")


@lru_cache(maxsize=1)
def citations() -> dict:
    p = C.CONTENT_DIR / "citations.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _frontmatter(text: str):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw, body = text[3:end].strip(), text[end + 4:].lstrip("\n")
    meta = {}
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, body


def render(path_rel: str):
    p = C.CONTENT_DIR / path_rel
    if not p.exists():
        return None
    meta, body = _frontmatter(p.read_text(encoding="utf-8"))
    cites = citations()
    used, idx = [], {}

    def cite_sub(m):
        key = m.group(1)
        if key not in idx:
            idx[key] = len(used) + 1
            used.append({"n": idx[key], "key": key, **cites.get(key, {"title": key})})
        return f'<sup class="cite"><a href="#ref-{idx[key]}">[{idx[key]}]</a></sup>'

    body = _CITE_RE.sub(cite_sub, body)
    charts = []

    def chart_sub(m):
        key, y0, y1 = m.group(1), m.group(2), m.group(3)
        cid = f"chart-{len(charts)}"
        charts.append({"id": cid, "key": key, "y0": y0, "y1": y1})
        q = f"?y0={y0}&amp;y1={y1}" if y0 else ""
        return f'\n\n<div class="chart-embed" id="{cid}" data-chart="{key}" data-params="{q}"></div>\n\n'

    body = _CHART_RE.sub(chart_sub, body)
    html = _md.render(body)
    return {"meta": meta, "html": html, "charts": charts, "citations": used,
            "title": meta.get("title", path_rel)}


def list_eras():
    eras = []
    hist = C.CONTENT_DIR / "history"
    if not hist.exists():
        return eras
    for p in sorted(hist.glob("*.md")):
        meta, _ = _frontmatter(p.read_text(encoding="utf-8"))
        eras.append({"slug": meta.get("era", p.stem), "title": meta.get("title", p.stem),
                     "period": meta.get("period", ""), "order": meta.get("order", "99")})
    return sorted(eras, key=lambda e: str(e.get("order")))
