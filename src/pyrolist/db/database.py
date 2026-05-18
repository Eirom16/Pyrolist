from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from pyrolist.config.paths import AppDirs
from loguru import logger

Base = declarative_base()

DATABASE_URL = f"sqlite+aiosqlite:///{AppDirs.database}"

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False)
    return _engine


async def get_session_factory():
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(engine, class_=AsyncSession)
    return _session_factory


async def init_db():
    from pyrolist.db import models
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    
    # Safely alter table to add the new column for existing databases
    from sqlalchemy import text
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE downloads ADD COLUMN parent_playlist_thumbnail_url TEXT"))
        logger.info("Added parent_playlist_thumbnail_url column to downloads table")
    except Exception:
        pass
    
    logger.info("Database initialized")

from contextlib import asynccontextmanager


@asynccontextmanager
async def get_session():
    factory = await get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()

