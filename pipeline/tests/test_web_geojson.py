import math

import geopandas as gpd
import pytest
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

from forestfr.boundaries import to_web_geojson


def wiggly_pair() -> gpd.GeoDataFrame:
    """Two départements sharing a jagged 400-vertex border along lat ~45.5."""
    n = 400
    border = [(4 + i / n, 45.5 + 0.01 * math.sin(i / 3)) for i in range(n + 1)]
    south = Polygon([(4, 45), (5, 45), *reversed(border)])
    north = Polygon([*border, (5, 46), (4, 46)])
    return gpd.GeoDataFrame(
        {
            "country": ["FR", "FR"],
            "admin_level": [2, 2],
            "code": ["38", "01"],
            "parent_code": ["84", "84"],
            "name": ["Isère", "Ain"],
            "area_km2": [1.0, 1.0],
        },
        geometry=[south, north],
        crs="EPSG:4326",
    )


def vertex_count(fc: dict) -> int:  # type: ignore[type-arg]
    return sum(len(shape(f["geometry"]).exterior.coords) for f in fc["features"])


def test_features_carry_code_name_and_parent() -> None:
    fc = to_web_geojson(wiggly_pair())

    props = sorted((f["properties"] for f in fc["features"]), key=lambda p: p["code"])
    assert props == [
        {"code": "01", "name": "Ain", "parent_code": "84"},
        {"code": "38", "name": "Isère", "parent_code": "84"},
    ]


def test_simplification_reduces_vertices() -> None:
    fc = to_web_geojson(wiggly_pair())

    assert vertex_count(fc) < 0.2 * 806


def test_shared_border_stays_aligned() -> None:
    fc = to_web_geojson(wiggly_pair())

    polys = [shape(f["geometry"]) for f in fc["features"]]
    union = unary_union(polys)
    assert union.geom_type == "Polygon"  # no slivers / gaps splitting the union
    assert len(union.interiors) == 0
    assert sum(p.area for p in polys) == pytest.approx(union.area, rel=1e-9)  # no overlaps
