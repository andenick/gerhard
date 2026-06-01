"""HTML page routes (server-rendered Jinja2)."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from app import config as C
from app.services import data_service as D
from app.services import narrative_service as N

router = APIRouter(tags=["pages"])


def _t(request: Request):
    return request.app.state.templates


def _ctx(request: Request, **kw):
    base = {"request": request, "site_title": C.SITE_TITLE, "tagline": C.SITE_TAGLINE}
    base.update(kw)
    return base


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _t(request).TemplateResponse("home.html", _ctx(request, stats=D.headline_stats(), eras=N.list_eras()))


@router.get("/history", response_class=HTMLResponse)
def history_index(request: Request):
    return _t(request).TemplateResponse("history_index.html", _ctx(request, eras=N.list_eras(), section="History"))


@router.get("/history/{era}", response_class=HTMLResponse)
def history_era(request: Request, era: str):
    # files are NN-era.md; match by frontmatter era slug
    import glob, os
    target = None
    for p in sorted((C.CONTENT_DIR / "history").glob("*.md")):
        page = N.render(f"history/{p.name}")
        if page and (page["meta"].get("era") == era or p.stem.split("-", 1)[-1] == era or p.stem == era):
            target = page; break
    if target is None:
        raise HTTPException(404, "Era not found")
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=target, section="History", eras=N.list_eras()))


@router.get("/modern", response_class=HTMLResponse)
def modern_index(request: Request):
    page = N.render("modern/index.md") or {"title": "Modern", "html": "", "charts": [], "citations": []}
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="Modern"))


@router.get("/modern/{sub}", response_class=HTMLResponse)
def modern_sub(request: Request, sub: str):
    page = N.render(f"modern/{sub}.md")
    if page is None:
        raise HTTPException(404, "Page not found")
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="Modern"))


@router.get("/treasury", response_class=HTMLResponse)
def treasury_index(request: Request):
    page = N.render("treasury/index.md") or {"title": "Treasury", "html": "", "charts": [], "citations": []}
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="Treasury"))


@router.get("/treasury/{sub}", response_class=HTMLResponse)
def treasury_sub(request: Request, sub: str):
    page = N.render(f"treasury/{sub}.md")
    if page is None:
        raise HTTPException(404, "Page not found")
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="Treasury"))


@router.get("/explore", response_class=HTMLResponse)
def explore(request: Request):
    return _t(request).TemplateResponse("explore.html", _ctx(request, section="Explore"))


@router.get("/data", response_class=HTMLResponse)
def data_catalog(request: Request):
    return _t(request).TemplateResponse("catalog.html", _ctx(
        request, series=D.list_series(), treasury=D.list_treasury(),
        us_history=D.list_us_history(), section="Data"))


@router.get("/methodology", response_class=HTMLResponse)
def methodology(request: Request):
    page = N.render("methodology.md") or {"title": "Methodology", "html": "", "charts": [], "citations": []}
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="About"))


@router.get("/about", response_class=HTMLResponse)
def about(request: Request):
    page = N.render("about.md") or {"title": "About", "html": "", "charts": [], "citations": []}
    return _t(request).TemplateResponse("narrative.html", _ctx(request, page=page, section="About"))


@router.get("/healthz")
def healthz():
    return {"status": "ok", "series_cached": sum(1 for s in D.list_series().values() if s.get("cached"))}
