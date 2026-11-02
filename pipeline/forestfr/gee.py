"""Google Earth Engine adapter (needs credentials; not exercised by unit tests).

Unit tests use fakes for the `HansenSource` protocol defined in `forestfr.hansen`.
"""

from __future__ import annotations

from typing import Any

import geopandas as gpd

from forestfr.config import Settings

HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
DEPARTMENTS_ASSET = "fr_departements"
UPLOAD_TOLERANCE_DEG = 0.0001  # ~10 m: negligible vs 30 m pixels, keeps the request small


def _ee() -> Any:
    import ee

    return ee


def init(settings: Settings) -> Any:
    ee = _ee()
    if not settings.gee_project:
        raise RuntimeError("GEE_PROJECT is not set (see docs/SETUP_CREDENTIALS.md).")
    ee.Initialize(project=settings.gee_project)
    return ee


def departments_asset_id(settings: Settings) -> str:
    return f"projects/{settings.gee_project}/assets/{DEPARTMENTS_ASSET}"


def upload_departments(settings: Settings, departments: gpd.GeoDataFrame) -> str:
    """Export département polygons to a GEE table asset. Returns the task id."""
    ee = init(settings)
    features = [
        ee.Feature(
            ee.Geometry(geom.simplify(UPLOAD_TOLERANCE_DEG).__geo_interface__),
            {"code": code, "parent_code": parent},
        )
        for code, parent, geom in zip(
            departments["code"], departments["parent_code"], departments.geometry, strict=True
        )
    ]
    task = ee.batch.Export.table.toAsset(
        collection=ee.FeatureCollection(features),
        description="fr_departements_upload",
        assetId=departments_asset_id(settings),
    )
    task.start()
    return str(task.id)
