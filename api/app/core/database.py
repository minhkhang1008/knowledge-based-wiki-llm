import os

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./knowledge_base.db")
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() == "true"
engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO)
Base = declarative_base()
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def _migrate_sqlite_schema(connection: Connection) -> None:
    """Apply small, backwards-compatible migrations for existing local databases."""
    if connection.dialect.name != "sqlite":
        return

    inspector = inspect(connection)
    if "qa_logs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("qa_logs")}
    if "sources" not in columns:
        connection.execute(
            text(
                "ALTER TABLE qa_logs "
                "ADD COLUMN sources JSON NOT NULL DEFAULT '[]'"
            )
        )

    # Older versions used the singular column name. Preserve those citations
    # when upgrading, including databases that were only partially migrated.
    if "source" in columns:
        connection.execute(
            text(
                "UPDATE qa_logs SET sources = source "
                "WHERE source IS NOT NULL "
                "AND (sources IS NULL OR sources = '[]')"
            )
        )


async def init_db() -> None:
    from app.models.article import Article
    from app.models.qa_log import QALog

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite_schema)


async def close_db() -> None:
    await engine.dispose()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
