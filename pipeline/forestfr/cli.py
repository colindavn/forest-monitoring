"""Command line entry point: `forestfr extract ...`, `forestfr demo-data`."""

from __future__ import annotations

import typer

from forestfr.config import Settings
from forestfr.load import Warehouse

app = typer.Typer(no_args_is_help=True, help="Forest loss monitor — extract & load.")
extract_app = typer.Typer(no_args_is_help=True, help="Extract raw data into the warehouse.")
app.add_typer(extract_app, name="extract")


@app.command()
def version() -> None:
    """Print the package version."""
    from forestfr import __version__

    typer.echo(__version__)


@extract_app.command("boundaries")
def extract_boundaries_cmd() -> None:
    """Download ADMIN-EXPRESS, load raw.admin_areas, write web GeoJSON, upload to GEE."""
    from forestfr.boundaries import extract_boundaries

    settings = Settings.from_env()
    wh = Warehouse(settings.warehouse_path)
    try:
        areas = extract_boundaries(settings, wh)
    finally:
        wh.close()
    counts = areas.admin_level.value_counts().to_dict()
    typer.echo(f"Loaded {counts.get(1, 0)} régions and {counts.get(2, 0)} départements.")

    if not settings.gee_project:
        typer.echo("GEE upload skipped: GEE_PROJECT is not set (see docs/SETUP_CREDENTIALS.md).")
        return
    from forestfr.gee import upload_departments

    task_id = upload_departments(settings, areas[areas.admin_level == 2])
    typer.echo(f"GEE upload started (task {task_id}).")


if __name__ == "__main__":
    app()
