"""Command line entry point: `forestfr extract ...`, `forestfr demo-data`."""

from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True, help="Forest loss monitor — extract & load.")
extract_app = typer.Typer(no_args_is_help=True, help="Extract raw data into the warehouse.")
app.add_typer(extract_app, name="extract")


@app.command()
def version() -> None:
    """Print the package version."""
    from forestfr import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
