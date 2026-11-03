"""Data sources, versions and update dates for the "À propos des données" panel."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.db import Database, Db
from app.params import THRESHOLDS
from app.routes.health import is_synthetic

router = APIRouter()

SOURCES = [
    {
        "id": "hansen",
        "name": "Hansen / UMD Global Forest Change 2025 v1.13",
        "provider": "University of Maryland, Google, USGS, NASA",
        "url": "https://glad.earthengine.app/view/global-forest-change",
        "licence": "CC BY 4.0",
    },
    {
        "id": "dist_alert",
        "name": "DIST-ALERT (alertes de perturbation de la végétation)",
        "provider": "UMD GLAD / NASA OPERA, via Global Forest Watch / WRI",
        "url": "https://data.globalforestwatch.org/",
        "licence": "Données ouvertes — attribution « Global Forest Watch / WRI »",
    },
    {
        "id": "admin_express",
        "name": "IGN ADMIN-EXPRESS COG CARTO 4.0 (2026)",
        "provider": "IGN",
        "url": "https://geoservices.ign.fr/adminexpress",
        "licence": "Licence Ouverte Etalab 2.0",
    },
    {
        "id": "ign_basemaps",
        "name": "Plan IGN v2 et orthophotographies (Géoplateforme)",
        "provider": "IGN",
        "url": "https://geoservices.ign.fr/",
        "licence": "Licence Ouverte Etalab 2.0",
    },
]


def versions(db: Database, table: str) -> list[str]:
    rows = db.rows(f"select distinct _source_version as v from raw.{table} order by v")
    return [r["v"] for r in rows]


def loaded_at(db: Database, table: str) -> str | None:
    ts = db.scalar(f"select max(_loaded_at) from raw.{table}")
    return ts.isoformat() if ts else None


@router.get("/meta")
def meta(db: Db) -> dict[str, Any]:
    latest_alert = db.scalar("select max(alert_date) from raw.dist_alerts_day")
    return {
        "sources": SOURCES,
        "versions": {
            "boundaries": versions(db, "admin_areas"),
            "hansen": versions(db, "hansen_loss"),
            "alerts": versions(db, "dist_alerts_day"),
        },
        "updated": {
            "hansen": loaded_at(db, "hansen_loss"),
            "alerts": loaded_at(db, "dist_alerts_day"),
        },
        "thresholds": list(THRESHOLDS),
        "default_threshold": 30,
        "latest_loss_year": db.scalar("select max(year) from marts.fct_loss_year"),
        "latest_alert_date": latest_alert.isoformat() if latest_alert else None,
        "synthetic": is_synthetic(db),
        "dbt_docs_url": "/dbt-docs/index.html",
    }
