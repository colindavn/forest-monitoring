import json
import math

import pytest
from shapely.geometry import Polygon, shape

from forestfr.gee import gee_geometry


def jagged_polygon(n: int = 40_000) -> Polygon:
    """Roughly 1°x1° polygon with a very detailed coastline-like edge (~1.5 MB of GeoJSON)."""
    edge = [(4 + i / n, 45 + 0.002 * math.sin(i / 2)) for i in range(n + 1)]
    return Polygon([*edge, (5, 46), (4, 46)])


def test_geometry_payload_fits_the_budget() -> None:
    geom = jagged_polygon()
    assert len(json.dumps(geom.__geo_interface__)) > 1_000_000

    payload = gee_geometry(geom, max_bytes=200_000)

    assert len(json.dumps(payload)) <= 200_000


def test_simplification_keeps_the_area() -> None:
    geom = jagged_polygon()

    simplified = shape(gee_geometry(geom, max_bytes=200_000))

    assert simplified.area == pytest.approx(geom.area, rel=0.005)


def test_small_geometries_are_kept_at_full_detail() -> None:
    square = Polygon([(4, 45), (5, 45), (5, 46), (4, 46)])

    assert shape(gee_geometry(square)).equals(square)
