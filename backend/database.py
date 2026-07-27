from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings

# SQLite does not support pool_size / max_overflow — only pass them for non-SQLite
_engine_kwargs: dict = {"echo": settings.DB_ECHO}
if not settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # SQLite: add any columns that exist in ORM models but not yet in the DB
    if settings.DATABASE_URL.startswith("sqlite"):
        await _sqlite_auto_migrate()


async def _sqlite_auto_migrate() -> None:
    """Add missing columns for SQLite (ALTER TABLE ADD COLUMN)."""
    from sqlalchemy import inspect, text
    async with engine.connect() as conn:
        def _get_existing(sync_conn):
            inspector = inspect(sync_conn)
            return {
                tbl: {col["name"] for col in inspector.get_columns(tbl)}
                for tbl in inspector.get_table_names()
            }

        existing: dict[str, set[str]] = await conn.run_sync(_get_existing)

        for table in Base.metadata.tables.values():
            tbl_existing = existing.get(table.name, set())
            for col in table.columns:
                if col.name not in tbl_existing:
                    col_type = col.type.compile(dialect=engine.dialect)
                    await conn.execute(
                        text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}")
                    )
        await conn.commit()
