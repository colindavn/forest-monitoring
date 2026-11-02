"""Choropleth values and rankings for a level and metric."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.db import Database, Db
from app.params import Threshold, check_threshold

router = APIRouter()

MapLevel = Literal["region", "department"]
Metric = Literal["loss_ha", "loss_pct_of_2000", "alerts_ha_last_4w", "trend_slope"]

# Year-based metrics come from fct_loss_year; the others from mart_area_kpis.
YEARLY = {"loss_ha": "loss_ha", "loss_pct_of_2000": "loss_pct_of_2000"}
KPI = {"alerts_ha_last_4w": "alerts_last_4w_ha", "trend_slope": "trend_slope_ha_per_year"}


def metric_values(
    db: Database,
    level: str,
    metric: str,
    threshold: int,
    year: int | None,
    parent: str | None,
) -> tuple[int, list[dict[str, Any]]]:
    """Return (year used, rows of code/name/value) for the metric."""
    latest = db.scalar("select max(year) from marts.fct_loss_year")
    year = year or latest
    if metric in YEARLY:
        sql = (
            f"select f.code, k.name, f.{YEARLY[metric]} as value "
            "from marts.fct_loss_year as f "
            "join marts.mart_area_kpis as k using (level, code, threshold) "
            "where f.level = ? and f.threshold = ? and f.year = ?"
        )
        params: list[Any] = [level, threshold, year]
    else:
        sql = (
            f"select code, name, {KPI[metric]} as value from marts.mart_area_kpis as k "
            "where level = ? and threshold = ?"
        )
        params = [level, threshold]
    if parent:
        sql += " and k.parent_code = ?"
        params.append(parent)
    return year, db.rows(sql + " order by value desc nulls last, code", params)


@router.get("/choropleth")
def choropleth(
    db: Db,
    level: MapLevel,
    metric: Metric,
    threshold: Threshold = 30,
    year: int | None = None,
    parent: str | None = None,
) -> dict[str, Any]:
    check_threshold(threshold)
    used_year, rows = metric_values(db, level, metric, threshold, year, parent)
    return {
        "level": level,
        "metric": metric,
        "year": used_year,
        "threshold": threshold,
        "values": {r["code"]: r["value"] for r in sorted(rows, key=lambda r: r["code"])},
    }


@router.get("/rankings")
def rankings(
    db: Db,
    level: MapLevel,
    metric: Metric,
    threshold: Threshold = 30,
    year: int | None = None,
    parent: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> dict[str, Any]:
    check_threshold(threshold)
    used_year, rows = metric_values(db, level, metric, threshold, year, parent)
    items, rank, previous = [], 0, None
    for i, row in enumerate(rows, start=1):
        if row["value"] != previous:
            rank, previous = i, row["value"]
        items.append({"rank": rank, **row})
    return {
        "level": level,
        "metric": metric,
        "year": used_year,
        "threshold": threshold,
        "parent": parent,
        "items": items[:limit],
    }
