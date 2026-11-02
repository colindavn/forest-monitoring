"""DuckDB warehouse: raw table definitions and idempotent upserts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class RawTable:
    columns: dict[str, str]  # name -> DuckDB type (metadata columns are added automatically)
    keys: tuple[str, ...]


# Generic admin-level naming (SPEC §15.3): `code` is the INSEE code of the lowest level
# (département for FR); `admin_level` 1 = région, 2 = département.
RAW_TABLES: dict[str, RawTable] = {
    "admin_areas": RawTable(
        columns={
            "country": "VARCHAR",
            "admin_level": "INTEGER",
            "code": "VARCHAR",
            "parent_code": "VARCHAR",
            "name": "VARCHAR",
            "area_km2": "DOUBLE",
            "geom_wkb": "BLOB",
        },
        keys=("country", "admin_level", "code"),
    ),
    "hansen_forest_extent": RawTable(
        columns={
            "country": "VARCHAR",
            "code": "VARCHAR",
            "threshold": "INTEGER",
            "forest_2000_ha": "DOUBLE",
        },
        keys=("country", "code", "threshold"),
    ),
    "hansen_loss": RawTable(
        columns={
            "country": "VARCHAR",
            "code": "VARCHAR",
            "threshold": "INTEGER",
            "year": "INTEGER",
            "loss_ha": "DOUBLE",
        },
        keys=("country", "code", "threshold", "year"),
    ),
    "dist_alerts_day": RawTable(
        columns={
            "country": "VARCHAR",
            "code": "VARCHAR",
            "threshold": "INTEGER",
            "alert_date": "DATE",
            "confidence_code": "INTEGER",
            "area_ha": "DOUBLE",
        },
        keys=("country", "code", "threshold", "alert_date", "confidence_code"),
    ),
}

META_COLUMNS = {"_source_version": "VARCHAR", "_loaded_at": "TIMESTAMP"}


class Warehouse:
    """Thin wrapper over a DuckDB file holding the `raw` schema."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._con = duckdb.connect(str(path))
        self._con.execute("create schema if not exists raw")
        for name, table in RAW_TABLES.items():
            cols = {**table.columns, **META_COLUMNS}
            ddl = ", ".join(f"{c} {t}" for c, t in cols.items())
            pk = ", ".join(table.keys)
            self._con.execute(f"create table if not exists raw.{name} ({ddl}, primary key ({pk}))")

    def upsert(self, table: str, rows: Iterable[Mapping[str, Any]], *, source_version: str) -> int:
        """Insert rows, replacing existing rows with the same keys. Returns row count."""
        spec = RAW_TABLES[table]
        cols = list(spec.columns)
        values = [(*(row[c] for c in cols), source_version) for row in rows]
        if not values:
            return 0
        placeholders = ", ".join(["?"] * (len(cols) + 1))
        self._con.executemany(
            f"insert or replace into raw.{table} ({', '.join(cols)}, _source_version, _loaded_at) "
            f"values ({placeholders}, current_timestamp)",
            values,
        )
        return len(values)

    def query(self, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        return self._con.execute(sql, params or []).fetchall()

    def close(self) -> None:
        self._con.close()
