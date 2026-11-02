from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query

from app.db import Db
from app.params import Level, Threshold, area_or_404, check_threshold

router = APIRouter()


@router.get("/loss")
def loss(
    db: Db,
    level: Level,
    code: str,
    threshold: Threshold = 30,
    from_: Annotated[int | None, Query(alias="from")] = None,
    to: int | None = None,
) -> dict[str, Any]:
    """Annual tree cover loss series (fct_loss_year)."""
    check_threshold(threshold)
    area_or_404(db, threshold, level, code)
    series = db.rows(
        "select year, forest_2000_ha, loss_ha, loss_pct_of_2000, cum_loss_ha, loss_ha_5y_avg, "
        "yoy_change_pct from marts.fct_loss_year "
        "where level = ? and code = ? and threshold = ? "
        "and year >= coalesce(?, 0) and year <= coalesce(?, 9999) order by year",
        [level, code, threshold, from_, to],
    )
    return {"level": level, "code": code, "threshold": threshold, "series": series}


@router.get("/alerts")
def alerts(
    db: Db,
    level: Level,
    code: str,
    threshold: Threshold = 30,
    from_: Annotated[date | None, Query(alias="from")] = None,
    to: date | None = None,
    confidence: Literal["all", "high"] = "all",
) -> dict[str, Any]:
    """Weekly DIST-ALERT series with anomaly flags.

    `area_ha` is the selected measure: all confidence levels, or high + highest (`high`).
    """
    check_threshold(threshold)
    area_or_404(db, threshold, level, code)
    measure = "area_ha_all" if confidence == "all" else "area_ha_high_conf"
    series = db.rows(
        f"select a.week_start, a.{measure} as area_ha, a.area_ha_nominal, a.area_ha_high, "
        "a.area_ha_highest, a.area_ha_high_conf, a.area_ha_all, a.area_ha_4w_rolling, "
        "n.z_score, n.is_anomaly "
        "from marts.fct_alerts_week as a "
        "join marts.mart_alert_anomalies as n using (level, code, threshold, week_start) "
        "where level = ? and code = ? and threshold = ? "
        "and week_start >= coalesce(?, date '1900-01-01') "
        "and week_start <= coalesce(?, date '2999-12-31') order by week_start",
        [level, code, threshold, from_, to],
    )
    return {
        "level": level,
        "code": code,
        "threshold": threshold,
        "confidence": confidence,
        "series": series,
    }
