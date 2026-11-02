"""ADMIN-EXPRESS COG CARTO boundaries → raw.admin_areas + simplified web GeoJSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx
import pandas as pd
from topojson import Topology  # type: ignore[attr-defined]

from forestfr.config import Settings
from forestfr.load import Warehouse

log = logging.getLogger(__name__)

COUNTRY = "FR"
OVERSEAS_REGIONS = {"01", "02", "03", "04", "06"}
AREA_CRS = "EPSG:2154"  # Lambert-93, used for area computation

SOURCE_VERSION = "ADMIN-EXPRESS-COG-CARTO 4.0 2026-01-01"
_BASE = (
    "https://data.geopf.fr/telechargement/download/ADMIN-EXPRESS-COG-CARTO/"
    "ADMIN-EXPRESS-COG-CARTO_4-0__FLATGEOBUF_WGS84G_FRA_2026-01-01"
)
REGION_URL = f"{_BASE}/region.fgb"
DEPARTEMENT_URL = f"{_BASE}/departement.fgb"


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


def download(url: str, dest: Path) -> Path:
    """Download `url` to `dest` (skipped if already present)."""
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=120) as resp:
        resp.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in resp.iter_bytes():
                fh.write(chunk)
    tmp.replace(dest)
    return dest


def extract_boundaries(settings: Settings, wh: Warehouse) -> gpd.GeoDataFrame:
    """Download IGN layers, load raw.admin_areas and write simplified web GeoJSON."""
    regions = gpd.read_file(download(REGION_URL, settings.download_dir / "region.fgb"))
    deps = gpd.read_file(download(DEPARTEMENT_URL, settings.download_dir / "departement.fgb"))
    areas = to_admin_areas(regions, deps)

    rows = [
        {**rec, "geom_wkb": geom.wkb}
        for rec, geom in zip(
            areas.drop(columns="geometry").to_dict("records"), areas.geometry, strict=True
        )
    ]
    wh.upsert("admin_areas", rows, source_version=SOURCE_VERSION)

    settings.web_geo_dir.mkdir(parents=True, exist_ok=True)
    for level, filename in ((1, "regions.geojson"), (2, "departments.geojson")):
        fc = to_web_geojson(areas[areas.admin_level == level])
        (settings.web_geo_dir / filename).write_text(
            json.dumps(fc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    return areas
