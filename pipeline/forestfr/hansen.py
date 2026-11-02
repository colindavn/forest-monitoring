"""Hansen/UMD tree cover loss: zonal stats per area & year → raw.hansen_* tables."""

from __future__ import annotations

import logging
from collections.abc import Iterable
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


def run_hansen(wh: Warehouse, source: HansenSource, thresholds: Iterable[int]) -> None:
    """Compute and load Hansen stats for every threshold (idempotent)."""
    for threshold in thresholds:
        extent, loss = parse_zonal_stats(source.zonal_stats(threshold), threshold)
        wh.upsert("hansen_forest_extent", extent, source_version=source.version)
        wh.upsert("hansen_loss", loss, source_version=source.version)
        total = sum(r["loss_ha"] for r in loss)
        log.info("Hansen threshold %s: %d areas, %.0f ha total loss", threshold, len(extent), total)
