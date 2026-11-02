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


class GeeHansenSource:
    """Hansen zonal stats per département, computed in Earth Engine.

    One `reduceRegion` call per département keeps each request well under the
    interactive time limit (all years in one pass via a grouped reducer on `lossyear`).
    """

    version = HANSEN_ASSET

    def __init__(self, settings: Settings, scale: int = 30, tile_scale: int = 4) -> None:
        self.ee = init(settings)
        self.departments = self.ee.FeatureCollection(departments_asset_id(settings))
        self.scale = scale
        self.tile_scale = tile_scale

    def zonal_stats(self, threshold: int) -> dict[str, Any]:
        ee = self.ee
        hansen = ee.Image(HANSEN_ASSET)
        forest = hansen.select("treecover2000").gte(threshold)
        area_ha = ee.Image.pixelArea().divide(1e4).updateMask(forest).rename("area")
        image = area_ha.addBands(hansen.select("lossyear"))
        reducer = ee.Reducer.sum().group(groupField=1, groupName="lossyear")

        codes: list[str] = self.departments.aggregate_array("code").getInfo()
        features = []
        for code in codes:
            geom = self.departments.filter(ee.Filter.eq("code", code)).geometry()
            result = image.reduceRegion(
                reducer=reducer,
                geometry=geom,
                scale=self.scale,
                maxPixels=1e11,
                tileScale=self.tile_scale,
            ).getInfo()
            groups = result.get("groups", [])
            # lossyear 0 = forest without loss, so the groups partition all forest pixels.
            forest_2000_ha = sum(g["sum"] for g in groups)
            features.append(
                {"properties": {"code": code, "forest_2000_ha": forest_2000_ha, "groups": groups}}
            )
        return {"type": "FeatureCollection", "features": features}
