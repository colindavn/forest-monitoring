import geopandas as gpd

from forestfr.boundaries import to_admin_areas


def test_keeps_only_metropolitan_areas(
    ign_regions: gpd.GeoDataFrame, ign_departements: gpd.GeoDataFrame
) -> None:
    areas = to_admin_areas(ign_regions, ign_departements)

    assert sorted(areas.loc[areas.admin_level == 1, "code"]) == ["84", "93"]
    assert sorted(areas.loc[areas.admin_level == 2, "code"]) == ["01", "05", "38"]


def test_maps_ign_fields_to_generic_columns(
    ign_regions: gpd.GeoDataFrame, ign_departements: gpd.GeoDataFrame
) -> None:
    areas = to_admin_areas(ign_regions, ign_departements).set_index("code")

    isere = areas.loc["38"]
    assert isere["name"] == "Isère"
    assert isere["parent_code"] == "84"
    assert isere["country"] == "FR"
    assert areas.loc["84", "parent_code"] == "FR"


def test_area_is_computed_in_square_km(
    ign_regions: gpd.GeoDataFrame, ign_departements: gpd.GeoDataFrame
) -> None:
    areas = to_admin_areas(ign_regions, ign_departements).set_index("code")

    # 1° lon x 1° lat cell at 45-46°N ≈ 111.2 km x 78.7 km ≈ 8 750 km²
    assert 8_600 < areas.loc["93", "area_km2"] < 8_900
