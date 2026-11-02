"""Shared fixtures: tiny synthetic ADMIN-EXPRESS-like layers (WGS84)."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import box


@pytest.fixture
def ign_regions() -> gpd.GeoDataFrame:
    """Two metropolitan régions sharing a border at lon 5, plus one overseas région."""
    return gpd.GeoDataFrame(
        {
            "code_insee": ["84", "93", "01"],
            "nom_officiel": ["Auvergne-Rhône-Alpes", "Provence-Alpes-Côte d'Azur", "Guadeloupe"],
        },
        geometry=[box(4, 45, 5, 46), box(5, 45, 6, 46), box(-61.8, 15.8, -61.0, 16.5)],
        crs="EPSG:4326",
    )


@pytest.fixture
def ign_departements() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "code_insee": ["38", "01", "05", "971"],
            "nom_officiel": ["Isère", "Ain", "Hautes-Alpes", "Guadeloupe"],
            "code_insee_de_la_region": ["84", "84", "93", "01"],
        },
        geometry=[
            box(4, 45, 5, 45.5),
            box(4, 45.5, 5, 46),
            box(5, 45, 6, 46),
            box(-61.8, 15.8, -61.0, 16.5),
        ],
        crs="EPSG:4326",
    )
