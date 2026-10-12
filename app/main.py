"""FastAPI application factory (M4: Verify + Overview + Incidents + Explorer + Red-Team)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.routes import explorer, operations, redteam, verify


def create_app() -> FastAPI:
    app = FastAPI(title=config.app_title(), docs_url="/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(verify.router)
    app.include_router(operations.router)
    app.include_router(explorer.router)
    app.include_router(redteam.router)
    return app


app = create_app()
