"""Pytest configuration and fixtures for testing."""
import pytest
import pytest_asyncio
from src.database.db import init_db, engine, Base


@pytest.fixture(scope="session", autouse=True)
def setup_database_session():
    """Initialize database before running tests (session-scoped synchronous fixture)."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Drop all tables and recreate them
        loop.run_until_complete(_drop_and_recreate_db())
    finally:
        loop.close()


async def _drop_and_recreate_db():
    """Drop and recreate all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()
