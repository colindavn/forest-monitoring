import logging
import threading
from pathlib import Path
from typing import Any

import pytest

from forestfr.hansen import compare_with_reference, parse_area_stats, run_hansen
from forestfr.load import Warehouse

VERSION = "UMD/hansen/global_forest_change_2025_v1_13"

ISERE = {
    "code": "38",
    "groups": [
        {"lossyear": 0, "sum": 348_979.5},  # forest without loss
        {"lossyear": 1, "sum": 120.5},
        {"lossyear": 22, "sum": 900.0},
    ],
}  # forest 2000 = 350 000 ha


def test_parse_extracts_forest_extent() -> None:
    extent, _ = parse_area_stats(ISERE, threshold=30)

    assert extent == {"country": "FR", "code": "38", "threshold": 30, "forest_2000_ha": 350_000.0}


def test_forest_extent_is_the_sum_of_all_groups_including_no_loss() -> None:
    extent, _ = parse_area_stats(ISERE, threshold=30)

    assert extent["forest_2000_ha"] == pytest.approx(348_979.5 + 120.5 + 900.0)


def test_missing_no_loss_group_is_rejected() -> None:
    # Happens when lossyear is masked where 0: forest extent would equal total loss.
    only_loss = {"code": "38", "groups": [{"lossyear": 1, "sum": 120.5}]}

    with pytest.raises(ValueError, match="lossyear 0"):
        parse_area_stats(only_loss, threshold=30)


def test_parse_maps_lossyear_codes_to_calendar_years() -> None:
    _, loss = parse_area_stats(ISERE, threshold=30)

    assert [(r["code"], r["year"], r["loss_ha"]) for r in loss] == [
        ("38", 2001, 120.5),
        ("38", 2022, 900.0),
    ]


def test_france_total_within_5_percent_of_reference_passes() -> None:
    check = compare_with_reference(total_ha=1_040_000, reference_ha=1_000_000)

    assert check.ok
    assert check.diff_pct == pytest.approx(4.0)


def test_france_total_outside_tolerance_fails() -> None:
    check = compare_with_reference(total_ha=900_000, reference_ha=1_000_000)

    assert not check.ok
    assert check.diff_pct == pytest.approx(-10.0)


class FakeSource:
    """One département per call, like the GEE adapter; records calls (thread-safe)."""

    version = VERSION
    codes = ("38", "2A", "01")

    def __init__(self, fail_on: str | None = None) -> None:
        self.calls: list[tuple[str, int]] = []
        self.fail_on = fail_on
        self._lock = threading.Lock()

    def area_stats(self, code: str, threshold: int) -> dict[str, Any]:
        with self._lock:
            self.calls.append((code, threshold))
        if code == self.fail_on:
            raise RuntimeError("Computation timed out.")
        scale = {10: 1.2, 30: 1.0, 50: 0.7}[threshold]
        no_loss = {"lossyear": 0, "sum": 350_000.0 * scale - 1_020.5}
        return {"code": code, "groups": [no_loss, *ISERE["groups"][1:]]}


def test_run_hansen_loads_every_area_and_threshold(tmp_path: Path) -> None:
    wh = Warehouse(tmp_path / "wh.duckdb")

    run_hansen(wh, FakeSource(), thresholds=(10, 30, 50), workers=2)

    assert wh.query(
        "select threshold, count(*), max(forest_2000_ha) from raw.hansen_forest_extent "
        "group by 1 order by 1"
    ) == [(10, 3, pytest.approx(420_000.0)), (30, 3, 350_000.0), (50, 3, pytest.approx(245_000.0))]
    assert wh.query("select count(*), max(_source_version) from raw.hansen_loss") == [(18, VERSION)]


def test_rerun_skips_areas_already_loaded_for_this_version(tmp_path: Path) -> None:
    wh = Warehouse(tmp_path / "wh.duckdb")
    run_hansen(wh, FakeSource(), thresholds=(30,), workers=1)
    source = FakeSource()

    run_hansen(wh, source, thresholds=(10, 30), workers=1)

    assert sorted(source.calls) == [("01", 10), ("2A", 10), ("38", 10)]


def test_a_failed_area_does_not_lose_the_others(tmp_path: Path) -> None:
    wh = Warehouse(tmp_path / "wh.duckdb")

    with pytest.raises(RuntimeError, match="1 of 3"):
        run_hansen(wh, FakeSource(fail_on="2A"), thresholds=(30,), workers=2)

    assert wh.query("select code from raw.hansen_forest_extent order by code") == [
        ("01",),
        ("38",),
    ]


def test_progress_is_logged_per_area(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    wh = Warehouse(tmp_path / "wh.duckdb")

    with caplog.at_level(logging.INFO, logger="forestfr.hansen"):
        run_hansen(wh, FakeSource(), thresholds=(30,), workers=1)

    progress = [r.getMessage() for r in caplog.records if "/3" in r.getMessage()]
    assert len(progress) == 3
    assert progress[-1].startswith("Hansen 30 %: 3/3")
