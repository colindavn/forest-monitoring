"""Read-only access to the DuckDB warehouse."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Annotated, Any

import duckdb
from fastapi import Depends, Request


class Database:
    """One read-only connection; each query runs on its own cursor (thread-safe)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._con = duckdb.connect(str(path), read_only=True)
        self._lock = threading.Lock()

    def rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._con.cursor()
        try:
            result = cur.execute(sql, params or [])
            cols = [d[0] for d in result.description]
            return [dict(zip(cols, r, strict=True)) for r in result.fetchall()]
        finally:
            cur.close()

    def one(self, sql: str, params: list[Any] | None = None) -> dict[str, Any] | None:
        found = self.rows(sql, params)
        return found[0] if found else None

    def scalar(self, sql: str, params: list[Any] | None = None) -> Any:
        row = self.one(sql, params)
        return next(iter(row.values())) if row else None

    def close(self) -> None:
        self._con.close()


def get_db(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


Db = Annotated[Database, Depends(get_db)]
