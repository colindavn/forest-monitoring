from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db import Database, Db

router = APIRouter()

SYNTHETIC_SQL = """
select exists (
    select 1 from raw.hansen_loss where _source_version = 'SYNTHETIC'
    union all
    select 1 from raw.dist_alerts_day where _source_version = 'SYNTHETIC'
)
"""


def is_synthetic(db: Database) -> bool:
    return bool(db.scalar(SYNTHETIC_SQL))


@router.get("/health")
def health(db: Db) -> dict[str, Any]:
    latest_alert = db.scalar("select max(alert_date) from raw.dist_alerts_day")
    return {
        "status": "ok",
        "latest_loss_year": db.scalar("select max(year) from marts.fct_loss_year"),
        "latest_alert_date": latest_alert.isoformat() if latest_alert else None,
        "synthetic": is_synthetic(db),
    }
