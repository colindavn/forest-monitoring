"""ADMIN-EXPRESS COG CARTO boundaries → raw.admin_areas + simplified web GeoJSON."""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import pandas as pd
from topojson import Topology  # type: ignore[attr-defined]

COUNTRY = "FR"
OVERSEAS_REGIONS = {"01", "02", "03", "04", "06"}
AREA_CRS = "EPSG:2154"  # Lambert-93, used for area computation


def to_admin_areas(regions: gpd.GeoDataFrame, departements: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter IGN layers to metropolitan France and map them to generic admin-area columns."""
    reg = regions[~regions["code_insee"].isin(OVERSEAS_REGIONS)]
    dep = departements[departements["code_insee_de_la_region"].isin(reg["code_insee"])]

    level1 = pd.DataFrame(
        {
            "admin_level": 1,
            "code": reg["code_insee"].astype(str),
            "parent_code": COUNTRY,
            "name": reg["nom_officiel"],
            "geometry": reg.geometry,
        }
    )
    level2 = pd.DataFrame(
        {
            "admin_level": 2,
            "code": dep["code_insee"].astype(str),
            "parent_code": dep["code_insee_de_la_region"].astype(str),
            "name": dep["nom_officiel"],
            "geometry": dep.geometry,
        }
    )
    areas = gpd.GeoDataFrame(
        pd.concat([level1, level2], ignore_index=True), geometry="geometry", crs=regions.crs
    ).to_crs("EPSG:4326")
    areas.insert(0, "country", COUNTRY)
    areas["area_km2"] = areas.geometry.to_crs(AREA_CRS).area / 1e6
    return areas


def to_web_geojson(areas: gpd.GeoDataFrame, tolerance_deg: float = 0.005) -> dict[str, Any]:
    """Topology-preserving simplification → GeoJSON FeatureCollection (code, name, parent_code).

    Shared borders are simplified once (TopoJSON arcs), so neighbours stay aligned.
    """
    slim = areas[["code", "name", "parent_code", "geometry"]].to_crs("EPSG:4326")
    topo = Topology(slim, prequantize=False, toposimplify=tolerance_deg, prevent_oversimplify=True)
    fc: dict[str, Any] = json.loads(str(topo.to_geojson()))
    for feature in fc["features"]:
        props = feature["properties"]
        feature["properties"] = {k: props[k] for k in ("code", "name", "parent_code")}
        feature.pop("id", None)
    return fc
