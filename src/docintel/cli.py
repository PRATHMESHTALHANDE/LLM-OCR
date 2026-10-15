"""
Open Doc Intelligence (docintel) - Command Line Interface (CLI)
Provides CLI commands for diagnostics, starting services, and processing documents.
"""

from pathlib import Path
import sys

from rich.console import Console
import typer

from docintel.config.settings import get_settings

app = typer.Typer(
    name="docintel",
    help="Open Doc Intelligence - Local-first document parsing, OCR, and evaluation platform.",
    add_completion=False,
)
console = Console()


@app.command()
def doctor():
    """Run diagnostic pre-flight checks on local hardware, Python, CUDA, and Docker."""
    from scripts.doctor import run_doctor
    run_doctor()


@app.command()
def start(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8080, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(True, "--reload/--no-reload", help="Enable auto-reload"),
):
    """Start the DocIntel FastAPI backend and documentation server."""
    from scripts.start import main
    main()


@app.command()
def test():
    """Run the complete automated unit test suite with pytest."""
    import pytest
    console.print("[bold green]Running DocIntel test suite...[/bold green]")
    retcode = pytest.main(["-v", "tests/unit/"])
    sys.exit(retcode)


if __name__ == "__main__":
    app()
