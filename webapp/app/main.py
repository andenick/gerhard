"""FastAPI application factory for the Gerhard website."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import config as C
from app.routers import api, pages


def create_app() -> FastAPI:
    C.ensure_dirs()
    app = FastAPI(title=f"{C.SITE_TITLE} — {C.SITE_TAGLINE}", docs_url="/api/docs")
    templates = Jinja2Templates(directory=str(C.TEMPLATES_DIR))
    templates.env.globals["site_title"] = C.SITE_TITLE
    templates.env.globals["tagline"] = C.SITE_TAGLINE
    app.state.templates = templates
    app.mount("/static", StaticFiles(directory=str(C.STATIC_DIR)), name="static")
    app.include_router(pages.router)
    app.include_router(api.router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=False)
