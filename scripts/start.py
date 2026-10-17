"""
Open Doc Intelligence (docintel) - Unified Application Launcher
Checks environment configuration, runs database migrations, and boots the FastAPI server.
"""

from pathlib import Path
import shutil
import subprocess
import sys

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Auto-switch to project .venv if launched using global system python
venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    venv_python = root_dir / ".venv" / "bin" / "python"

if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    print(f"[BOOT] Switching to project virtual environment: {venv_python.relative_to(root_dir)}")
    res = subprocess.run([str(venv_python)] + sys.argv)
    sys.exit(res.returncode)

from alembic import command
from alembic.config import Config
import uvicorn

from docintel.config.settings import get_settings


def ensure_environment() -> None:
    """Ensure .env exists; if not, create it from .env.example."""
    env_file = Path(".env")
    example_env = Path(".env.example")
    if not env_file.exists() and example_env.exists():
        shutil.copyfile(example_env, env_file)
        print("[INIT] Created .env configuration from .env.example with local defaults.")


def run_database_migrations() -> None:
    """Run Alembic migrations to upgrade the database schema to head."""
    print("[MIGRATION] Applying Alembic database schema migrations...")
    try:
        settings = get_settings()
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", settings.sync_database_url)
        command.upgrade(alembic_cfg, "head")
        print("[MIGRATION] Database schema is up to date.")
    except Exception as e:
        print(f"[WARN] Automatic migration encountered notice: {e}")
        print("[WARN] Proceeding with runtime table synchronization fallback.")


import socket

def find_available_port(host: str, initial_port: int, max_attempts: int = 10) -> int:
    """Verify if target port is available; fallback to next open port if occupied."""
    for port in range(initial_port, initial_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return initial_port


def main() -> None:
    """Launch the DocIntel platform backend server."""
    ensure_environment()
    settings = get_settings()
    settings.ensure_directories()

    run_database_migrations()

    active_port = find_available_port(settings.DOCINTEL_HOST, settings.DOCINTEL_PORT)
    if active_port != settings.DOCINTEL_PORT:
        print(f"[PORT] Port {settings.DOCINTEL_PORT} is in use; automatically using open port {active_port}.")

    banner = f"""
====================================================================
           OPEN DOC INTELLIGENCE (docintel) - v0.1.0
      Local-First Document Parsing, OCR & Layout Platform
====================================================================
  * Neumorphic Dashboard: http://{settings.DOCINTEL_HOST}:{active_port}/
  * Interactive API Docs: http://{settings.DOCINTEL_HOST}:{active_port}/docs
  * Alternative Docs:     http://{settings.DOCINTEL_HOST}:{active_port}/redoc
  * Health Endpoint:      http://{settings.DOCINTEL_HOST}:{active_port}/health
  * Database Driver:      {"SQLite (Zero-Docker Local Mode)" if settings.is_sqlite else "PostgreSQL (Production Container)"}
  * Advanced OCR:         {"Enabled (" + settings.DOCINTEL_ADVANCED_OCR_PROVIDER + ")" if settings.DOCINTEL_ADVANCED_OCR_ENABLED else "Disabled"}
====================================================================
"""
    print(banner)

    from apps.api.main import app

    uvicorn.run(
        app,
        host=settings.DOCINTEL_HOST,
        port=active_port,
        log_level=settings.DOCINTEL_LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
