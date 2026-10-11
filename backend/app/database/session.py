from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Async Engine (for FastAPI dependency)
engine_args = {}
if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    **engine_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Sync Engine (for CLI scripts and Alembic)
sync_engine_args = {}
if "sqlite" in settings.SYNC_DATABASE_URL:
    sync_engine_args["connect_args"] = {"check_same_thread": False}

sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=False,
    future=True,
    **sync_engine_args
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_db() -> Session:
    """Provides a synchronous database session (for scripts/migrations)."""
    return SyncSessionLocal()
