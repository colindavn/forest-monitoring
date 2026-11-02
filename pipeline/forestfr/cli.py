"""Command line entry point: `forestfr extract ...`, `forestfr demo-data`."""

from __future__ import annotations

from datetime import date
from typing import Annotated

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


@extract_app.command("hansen")
def extract_hansen_cmd() -> None:
    """Compute Hansen forest extent and annual loss per département in GEE (all thresholds)."""
    settings = Settings.from_env()
    if not settings.gee_project:
        typer.echo("GEE_PROJECT is not set (see docs/SETUP_CREDENTIALS.md).", err=True)
        raise typer.Exit(code=1)
    from forestfr.gee import GeeHansenSource
    from forestfr.hansen import run_hansen

    wh = Warehouse(settings.warehouse_path)
    try:
        run_hansen(wh, GeeHansenSource(settings), settings.thresholds)
    finally:
        wh.close()


@app.command("demo-data")
def demo_data_cmd(
    until: Annotated[
        str | None, typer.Option(help="Last alert date (YYYY-MM-DD), default today.")
    ] = None,
) -> None:
    """Write SYNTHETIC Hansen and alert rows for local development (never publish)."""
    from forestfr.demo import NoBoundariesError, generate

    settings = Settings.from_env()
    wh = Warehouse(settings.warehouse_path)
    try:
        counts = generate(wh, until=date.fromisoformat(until) if until else date.today())
    except NoBoundariesError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    finally:
        wh.close()
    for table, n in counts.items():
        typer.echo(f"raw.{table}: {n} synthetic rows")


if __name__ == "__main__":
    app()
