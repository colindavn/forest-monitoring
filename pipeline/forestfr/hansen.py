"""Hansen/UMD tree cover loss: zonal stats per area & year → raw.hansen_* tables.

Areas are computed concurrently, saved as soon as each one finishes, and skipped on a
re-run when already loaded for the same Hansen version (so an interrupted run resumes).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Protocol

from forestfr.load import Warehouse

log = logging.getLogger(__name__)

COUNTRY = "FR"
Row = dict[str, Any]


class HansenSource(Protocol):
    """Computes zonal stats for one area at a time.

    `area_stats` returns `{"code", "forest_2000_ha", "groups"}` where `groups` is a list
    of `{"lossyear": int, "sum": ha}` from a grouped sum reducer. Must be thread-safe.
    """

    version: str

    @property
    def codes(self) -> Sequence[str]: ...

    def area_stats(self, code: str, threshold: int) -> dict[str, Any]: ...


def parse_area_stats(props: dict[str, Any], threshold: int) -> tuple[Row, list[Row]]:
    """Split one area's stats into a forest-extent row and loss rows (lossyear 0 ignored)."""
    base = {"country": COUNTRY, "code": str(props["code"]), "threshold": threshold}
    extent = {**base, "forest_2000_ha": float(props["forest_2000_ha"])}
    loss = [
        {**base, "year": 2000 + int(g["lossyear"]), "loss_ha": float(g["sum"])}
        for g in props.get("groups", [])
        if int(g["lossyear"]) != 0
    ]
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


def _loaded_codes(wh: Warehouse, version: str, threshold: int) -> set[str]:
    rows = wh.query(
        "select code from raw.hansen_forest_extent "
        "where country = ? and threshold = ? and _source_version = ?",
        [COUNTRY, threshold, version],
    )
    return {r[0] for r in rows}


def _run_threshold(wh: Warehouse, source: HansenSource, threshold: int, workers: int) -> int:
    """Compute missing areas for one threshold; returns the number of failed areas."""
    done = _loaded_codes(wh, source.version, threshold)
    todo = [c for c in source.codes if c not in done]
    total = len(source.codes)
    if done:
        log.info("Hansen %s %%: %d/%d already loaded, resuming", threshold, len(done), total)
    if not todo:
        return 0

    started, finished, failed = time.monotonic(), len(done), 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures: dict[Future[dict[str, Any]], str] = {
            pool.submit(source.area_stats, code, threshold): code for code in todo
        }
        for future in as_completed(futures):
            code = futures[future]
            try:
                extent, loss = parse_area_stats(future.result(), threshold)
            except Exception as exc:  # one area failing must not lose the others
                failed += 1
                log.warning("Hansen %s %%: %s failed: %s", threshold, code, exc)
                continue
            # DuckDB writes stay on this thread; only GEE calls run in parallel.
            wh.upsert("hansen_loss", loss, source_version=source.version)
            wh.upsert("hansen_forest_extent", [extent], source_version=source.version)
            finished += 1
            elapsed = time.monotonic() - started
            log.info(
                "Hansen %s %%: %d/%d (%s) — %dm%02ds",
                threshold,
                finished,
                total,
                code,
                elapsed // 60,
                elapsed % 60,
            )
    return failed


def run_hansen(
    wh: Warehouse,
    source: HansenSource,
    thresholds: Iterable[int],
    reference_ha: dict[int, float] | None = None,
    workers: int = 8,
) -> list[ReferenceCheck]:
    """Compute and load Hansen stats for every area and threshold (resumable).

    `reference_ha` maps threshold → GFW France total loss 2001-latest (ha), if known;
    the comparison is logged and returned. Raises after all thresholds if any area failed
    (the successful ones are kept; re-run to retry only the failed ones).
    """
    thresholds = list(thresholds)
    failures = {t: _run_threshold(wh, source, t, workers) for t in thresholds}

    checks = []
    for threshold in thresholds:
        if reference_ha and threshold in reference_ha and not failures[threshold]:
            total = wh.query(
                "select coalesce(sum(loss_ha), 0) from raw.hansen_loss "
                "where country = ? and threshold = ? and _source_version = ?",
                [COUNTRY, threshold, source.version],
            )[0][0]
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

    failed = sum(failures.values())
    if failed:
        n = len(source.codes) * len(thresholds)
        raise RuntimeError(f"Hansen: {failed} of {n} area computations failed; re-run to retry.")
    return checks
