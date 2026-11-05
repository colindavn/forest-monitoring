"""Google Earth Engine adapter (needs credentials; only `gee_geometry` is unit-tested).

Unit tests use fakes for the `HansenSource` protocol defined in `forestfr.hansen`.
Département polygons are sent inside each request (no GEE asset upload): one
département per request stays far below the 10 MB request payload limit.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import shapely
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from forestfr.config import Settings

HANSEN_ASSET = "UMD/hansen/global_forest_change_2025_v1_13"
BASE_TOLERANCE_DEG = 0.0001  # ~10 m: negligible vs 30 m pixels
MAX_GEOMETRY_BYTES = 2_000_000  # per request; GEE rejects payloads above 10 MB
COORD_GRID_DEG = 1e-6  # ~0.1 m coordinate precision


def gee_geometry(geom: BaseGeometry, max_bytes: int = MAX_GEOMETRY_BYTES) -> dict[str, Any]:
    """GeoJSON geometry small enough for one GEE request.

    Kept at full detail when it already fits; otherwise simplified from ~10 m,
    doubling the tolerance until the serialized payload fits `max_bytes`.
    """
    candidate, tolerance = geom, BASE_TOLERANCE_DEG
    while True:
        payload: dict[str, Any] = mapping(candidate)
        if len(json.dumps(payload)) <= max_bytes or tolerance > 0.05:
            return payload
        candidate = shapely.set_precision(geom.simplify(tolerance), COORD_GRID_DEG)
        tolerance *= 2


def init(settings: Settings) -> Any:
    import ee

    if not settings.gee_project:
        raise RuntimeError("GEE_PROJECT is not set (see docs/SETUP_CREDENTIALS.md).")
    ee.Initialize(project=settings.gee_project)
    return ee


class GeeHansenSource:
    """Hansen zonal stats per département, computed in Earth Engine.

    One `reduceRegion` call per département keeps each request small and under the
    interactive time limit (all years in one pass via a grouped reducer on `lossyear`).
    """

    version = HANSEN_ASSET

    def __init__(
        self,
        settings: Settings,
        departments: Sequence[tuple[str, BaseGeometry]],
        scale: int = 30,
        tile_scale: int = 4,
    ) -> None:
        self.ee = init(settings)
        self.departments = [(code, gee_geometry(geom)) for code, geom in departments]
        self.scale = scale
        self.tile_scale = tile_scale

    def zonal_stats(self, threshold: int) -> dict[str, Any]:
        ee = self.ee
        hansen = ee.Image(HANSEN_ASSET)
        forest = hansen.select("treecover2000").gte(threshold)
        area_ha = ee.Image.pixelArea().divide(1e4).updateMask(forest).rename("area")
        image = area_ha.addBands(hansen.select("lossyear"))
        reducer = ee.Reducer.sum().group(groupField=1, groupName="lossyear")

        features = []
        for code, geometry in self.departments:
            result = image.reduceRegion(
                reducer=reducer,
                geometry=ee.Geometry(geometry),
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
