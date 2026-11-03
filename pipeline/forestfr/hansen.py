"""Hansen/UMD tree cover loss: zonal stats per area & year → raw.hansen_* tables."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from forestfr.load import Warehouse

log = logging.getLogger(__name__)

COUNTRY = "FR"
Row = dict[str, Any]


class HansenSource(Protocol):
    """Anything that returns zonal stats in the `ee.FeatureCollection.getInfo()` shape.

    Each feature has properties `code`, `forest_2000_ha` and `groups`
    (a list of `{"lossyear": int, "sum": ha}` from a grouped sum reducer).
    """

    version: str

    def zonal_stats(self, threshold: int) -> dict[str, Any]: ...


def parse_zonal_stats(fc: dict[str, Any], threshold: int) -> tuple[list[Row], list[Row]]:
    """Split a zonal-stats FeatureCollection into forest-extent rows and loss rows."""
    extent: list[Row] = []
    loss: list[Row] = []
    for feature in fc["features"]:
        props = feature["properties"]
        code = str(props["code"])
        base = {"country": COUNTRY, "code": code, "threshold": threshold}
        extent.append({**base, "forest_2000_ha": float(props["forest_2000_ha"])})
        for group in props.get("groups", []):
            lossyear = int(group["lossyear"])
            if lossyear == 0:
                continue
            loss.append({**base, "year": 2000 + lossyear, "loss_ha": float(group["sum"])})
    return extent, loss


@dataclass(frozen=True)
class ReferenceCheck:
    total_ha: float
    reference_ha: float
    diff_pct: float
    ok: bool


def compare_with_reference(
    total_ha: float, reference_ha: float, tolerance: float = 0.05
) -> ReferenceCheck:
    """Compare our France-wide loss with GFW's published figure (SPEC §6.2: ±5 %)."""
    diff = (total_ha - reference_ha) / reference_ha
    return ReferenceCheck(total_ha, reference_ha, diff * 100, abs(diff) <= tolerance)


def run_hansen(
    wh: Warehouse,
    source: HansenSource,
    thresholds: Iterable[int],
    reference_ha: dict[int, float] | None = None,
) -> list[ReferenceCheck]:
    """Compute and load Hansen stats for every threshold (idempotent).

    `reference_ha` maps threshold → GFW France total loss 2001-latest (ha), if known;
    the comparison is logged and returned.
    """
    checks = []
    for threshold in thresholds:
        extent, loss = parse_zonal_stats(source.zonal_stats(threshold), threshold)
        wh.upsert("hansen_forest_extent", extent, source_version=source.version)
        wh.upsert("hansen_loss", loss, source_version=source.version)
        total = sum(r["loss_ha"] for r in loss)
        log.info("Hansen threshold %s: %d areas, %.0f ha total loss", threshold, len(extent), total)
        if reference_ha and threshold in reference_ha:
            check = compare_with_reference(total, reference_ha[threshold])
            log.log(
                logging.INFO if check.ok else logging.WARNING,
                "France total vs GFW at %s %%: %.0f vs %.0f ha (%+.1f %%) → %s",
                threshold,
                check.total_ha,
                check.reference_ha,
                check.diff_pct,
                "OK" if check.ok else "OUTSIDE ±5 %",
            )
            checks.append(check)
    return checks
