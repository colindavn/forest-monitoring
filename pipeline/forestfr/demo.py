"""Synthetic raw data for development and API tests (never published; SPEC §15.9).

Values are plausible in shape (seasonality, trends, a few outbreak years and weeks)
but entirely fake. Every row carries `_source_version = 'SYNTHETIC'`.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from forestfr.load import Warehouse

SYNTHETIC = "SYNTHETIC"
COUNTRY = "FR"
FIRST_YEAR, LAST_YEAR = 2001, 2025
ALERTS_START = date(2023, 1, 1)
# Relative forest extent / loss by threshold (lower threshold → more pixels count as forest).
THRESHOLD_SCALE = {10: 1.18, 30: 1.0, 50: 0.82}
# Share of daily alert area by GFW confidence code (2 nominal, 3 high, 4 highest).
CONFIDENCE_SHARE = {2: 0.5, 3: 0.3, 4: 0.2}


class NoBoundariesError(RuntimeError):
    pass


def generate(wh: Warehouse, until: date, seed: int = 42) -> dict[str, int]:
    """Write synthetic Hansen extent/loss and DIST-ALERT rows for every loaded département."""
    departments = wh.query(
        "select code, area_km2 from raw.admin_areas where country = ? and admin_level = 2 "
        "order by code",
        [COUNTRY],
    )
    if not departments:
        raise NoBoundariesError("No départements loaded: run `forestfr extract boundaries` first.")

    rng = np.random.default_rng(seed)
    years = np.arange(FIRST_YEAR, LAST_YEAR + 1)
    days = pd.date_range(ALERTS_START, until, freq="D")
    season = 1 + 0.6 * np.sin((days.day_of_year.to_numpy() - 100) / 365 * 2 * np.pi)

    extent: list[dict[str, object]] = []
    loss: list[dict[str, object]] = []
    alerts: list[pd.DataFrame] = []
    for code, area_km2 in departments:
        forest_30 = area_km2 * 100 * rng.uniform(0.12, 0.6)  # ha
        rate = rng.uniform(0.002, 0.007)  # yearly loss as share of forest
        trend = rng.uniform(-0.02, 0.06)
        yearly = forest_30 * rate * (1 + trend) ** (years - FIRST_YEAR)
        yearly *= rng.lognormal(0, 0.25, len(years))
        for spike_year in rng.choice(years, size=2, replace=False):  # storms, fires, beetles
            yearly[years == spike_year] *= rng.uniform(1.8, 3.5)

        daily = rng.gamma(0.6, forest_30 * 1.5e-5, len(days)) * season
        daily[rng.random(len(days)) > 0.4] = 0.0  # most days have no alert
        burst = rng.integers(0, len(days) - 21)
        daily[burst : burst + 21] *= rng.uniform(4, 8)  # one anomalous 3-week burst

        for threshold, scale in THRESHOLD_SCALE.items():
            base = {"country": COUNTRY, "code": code, "threshold": threshold}
            extent.append({**base, "forest_2000_ha": forest_30 * scale})
            loss.extend(
                {**base, "year": int(y), "loss_ha": float(v * scale)}
                for y, v in zip(years, yearly, strict=True)
            )
            for conf, share in CONFIDENCE_SHARE.items():
                mask = daily > 0
                alerts.append(
                    pd.DataFrame(
                        {
                            **base,
                            "alert_date": days[mask].date,
                            "confidence_code": conf,
                            "area_ha": daily[mask] * scale * share,
                        }
                    )
                )

    return {
        "hansen_forest_extent": wh.upsert("hansen_forest_extent", extent, source_version=SYNTHETIC),
        "hansen_loss": wh.upsert("hansen_loss", loss, source_version=SYNTHETIC),
        "dist_alerts_day": wh.upsert(
            "dist_alerts_day", pd.concat(alerts, ignore_index=True), source_version=SYNTHETIC
        ),
    }
