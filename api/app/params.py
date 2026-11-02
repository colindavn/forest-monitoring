"""Shared query parameters and validation helpers."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import HTTPException, Query

from app.db import Database

THRESHOLDS = (10, 30, 50)
Level = Literal["france", "region", "department"]
Threshold = Annotated[int, Query(description="Forest threshold (% tree cover 2000): 10, 30, 50")]


def check_threshold(threshold: int) -> int:
    if threshold not in THRESHOLDS:
        raise HTTPException(status_code=422, detail=f"threshold must be one of {THRESHOLDS}")
    return threshold


def area_or_404(db: Database, threshold: int, level: str, code: str) -> dict[str, Any]:
    found = db.one(
        "select * exclude (threshold) from marts.mart_area_kpis "
        "where threshold = ? and level = ? and code = ?",
        [threshold, level, code],
    )
    if not found:
        raise HTTPException(status_code=404, detail=f"Unknown {level} code {code!r}")
    return found
