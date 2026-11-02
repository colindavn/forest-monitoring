"""FastAPI app factory (read-only API over the dbt marts)."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.db import Database
from app.routes import areas, health, maps, meta, series

API_PREFIX = "/api"
CACHE_CONTROL = "public, max-age=3600"


def create_app(warehouse_path: Path, web_origin: str = "http://localhost:5173") -> FastAPI:
    app = FastAPI(title="Forest Loss Monitor France API", version="0.1.0")
    app.state.db = Database(warehouse_path)

    @app.middleware("http")
    async def cache_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if request.method == "GET" and response.status_code == 200:
            response.headers["Cache-Control"] = CACHE_CONTROL
        return response

    app.add_middleware(
        CORSMiddleware, allow_origins=[web_origin], allow_methods=["GET"], allow_headers=["*"]
    )
    for module in (health, areas, series, maps, meta):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


def app_from_env() -> FastAPI:
    root = Path(__file__).resolve().parents[2]
    path = Path(os.getenv("WAREHOUSE_PATH", "data/warehouse.duckdb"))
    return create_app(
        path if path.is_absolute() else root / path,
        web_origin=os.getenv("WEB_ORIGIN", "http://localhost:5173"),
    )
