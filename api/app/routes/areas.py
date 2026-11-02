from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db import Database, Db
from app.params import Threshold, area_or_404, check_threshold

router = APIRouter(prefix="/areas")


def kpis(db: Database, threshold: int, where: str, params: list[Any]) -> list[dict[str, Any]]:
    return db.rows(
        f"select * exclude (threshold) from marts.mart_area_kpis "
        f"where threshold = ? and {where} order by rank_in_parent nulls first, code",
        [threshold, *params],
    )


def parent_ref(db: Database, threshold: int, level: str, code: str) -> dict[str, Any]:
    p = area_or_404(db, threshold, level, code)
    return {"level": level, "code": p["code"], "name": p["name"]}


@router.get("/france")
def france(db: Db, threshold: Threshold = 30) -> dict[str, Any]:
    check_threshold(threshold)
    return {
        "area": area_or_404(db, threshold, "france", "FR"),
        "children": kpis(db, threshold, "level = 'region'", []),
    }


@router.get("/regions/{code}")
def region(db: Db, code: str, threshold: Threshold = 30) -> dict[str, Any]:
    check_threshold(threshold)
    area = area_or_404(db, threshold, "region", code)
    return {
        "area": area,
        "parent": parent_ref(db, threshold, "france", area["parent_code"]),
        "children": kpis(db, threshold, "level = 'department' and parent_code = ?", [code]),
    }


@router.get("/departments/{code}")
def department(db: Db, code: str, threshold: Threshold = 30) -> dict[str, Any]:
    check_threshold(threshold)
    area = area_or_404(db, threshold, "department", code)
    return {"area": area, "parent": parent_ref(db, threshold, "region", area["parent_code"])}
