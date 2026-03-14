"""
Shared pytest fixtures.

Key design decision:
  asyncpg connections are not coroutine-safe for concurrent operations on the
  same connection. To prevent "another operation is in progress" errors when
  tests share an event loop, we use NullPool (creates a fresh connection per
  transaction, never reuses). We also override get_db in the FastAPI app so
  HTTP tests use the same pool strategy.
"""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.deps import get_db
from app.main import app

# Test engine: NullPool avoids connection reuse across async contexts
test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


# Single event loop for all tests
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


# Inject NullPool sessions into the FastAPI app for all route tests
app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(scope="function")
async def db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
