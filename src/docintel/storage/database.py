"""
Open Doc Intelligence (docintel) - Database Engine & Connection Management
Async SQLAlchemy 2.0 connection pooling, dual PostgreSQL/SQLite lifecycle management,
and FastAPI dependency injection session factory.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from docintel.config.settings import get_settings

logger = logging.getLogger(__name__)

# Module-level singletons
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_engine_and_factory(
    database_url: str | None = None,
    echo: bool = False,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """
    Create and configure an AsyncEngine and async_sessionmaker.
    Configures connection pooling and dialect-specific pragmas.
    """
    settings = get_settings()
    url = database_url or settings.async_database_url

    connect_args: dict[str, Any] = {}
    engine_kwargs: dict[str, Any] = {
        "echo": echo or (settings.DOCINTEL_LOG_LEVEL == "DEBUG"),
    }

    if "sqlite" in url.lower():
        connect_args["check_same_thread"] = False
        engine_kwargs["connect_args"] = connect_args
        # SQLite uses StaticPool or NullPool for in-memory / concurrency safety
    else:
        # PostgreSQL with asyncpg connection pooling
        engine_kwargs["pool_size"] = settings.DOCINTEL_DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DOCINTEL_DB_MAX_OVERFLOW
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_timeout"] = settings.DOCINTEL_DB_TIMEOUT_SECONDS

    engine = create_async_engine(url, **engine_kwargs)

    # Enable foreign keys for SQLite
    if "sqlite" in url.lower():
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, factory


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the singleton AsyncEngine."""
    global _engine, _session_factory
    if _engine is None:
        _engine, _session_factory = create_engine_and_factory()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the singleton async_sessionmaker."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine, _session_factory = create_engine_and_factory()
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency and async context manager yielding an AsyncSession.
    Ensures rollback on error and clean session closure.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for standalone scripts, background workers, and jobs."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_database() -> None:
    """Dispose of engine connection pool on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connection engine disposed cleanly.")
