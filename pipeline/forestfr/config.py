"""Runtime configuration, read from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ALLOWED_THRESHOLDS = (10, 15, 20, 25, 30, 50, 75)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _thresholds(raw: str) -> tuple[int, ...]:
    values = tuple(int(v) for v in raw.split(",") if v.strip())
    bad = [v for v in values if v not in ALLOWED_THRESHOLDS]
    if bad:
        raise ValueError(f"Unsupported forest thresholds: {bad}; allowed {ALLOWED_THRESHOLDS}")
    return values


@dataclass(frozen=True)
class Settings:
    country: str = "FR"
    warehouse_path: Path = REPO_ROOT / "data" / "warehouse.duckdb"
    thresholds: tuple[int, ...] = (10, 30, 50)
    default_threshold: int = 30
    gee_project: str | None = None
    gfw_api_key: str | None = field(default=None, repr=False)
    web_geo_dir: Path = REPO_ROOT / "web" / "public" / "geo"
    download_dir: Path = REPO_ROOT / "data" / "downloads"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv(REPO_ROOT / ".env")

        def path(var: str, default: Path) -> Path:
            value = os.getenv(var)
            return REPO_ROOT / value if value else default  # absolute values win over REPO_ROOT

        return cls(
            warehouse_path=path("WAREHOUSE_PATH", cls.warehouse_path),
            web_geo_dir=path("WEB_GEO_DIR", cls.web_geo_dir),
            download_dir=path("DOWNLOAD_DIR", cls.download_dir),
            thresholds=_thresholds(os.getenv("FOREST_THRESHOLDS", "10,30,50")),
            default_threshold=int(os.getenv("FOREST_THRESHOLD", "30")),
            gee_project=os.getenv("GEE_PROJECT") or None,
            gfw_api_key=os.getenv("GFW_API_KEY") or None,
        )
