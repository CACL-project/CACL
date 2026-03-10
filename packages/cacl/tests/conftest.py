"""
Test fixtures for cacl library tests.

Uses PostgreSQL (same as production) for full compatibility.
Defines TestUser model that satisfies UserProtocol.
"""
import os
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from cacl.models.base import Base
from cacl.models.jwt_token import JWTToken

# Override settings BEFORE importing cacl modules that use them
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "1"
os.environ["USE_COOKIE_AUTH"] = "false"
os.environ["CACL_USER_MODEL"] = "tests.conftest.TestUser"


class TestUser(Base):
    """
    Test user model that satisfies UserProtocol.
    Uses PostgreSQL UUID for compatibility with JWTToken.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TestUser {self.email}>"


# Test database URL - uses the same PostgreSQL but different database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@db:5432/cacl_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create async engine and tables for each test function."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine):
    """Create async session for each test."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def active_user(session: AsyncSession):
    """Create an active regular user."""
    user = TestUser(
        id=uuid.uuid4(),
        email="user@test.com",
        is_admin=False,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(session: AsyncSession):
    """Create an active admin user."""
    user = TestUser(
        id=uuid.uuid4(),
        email="admin@test.com",
        is_admin=True,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(session: AsyncSession):
    """Create an inactive user."""
    user = TestUser(
        id=uuid.uuid4(),
        email="inactive@test.com",
        is_admin=False,
        is_active=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def clear_user_model_cache():
    """Clear the cached user model before each test."""
    from cacl.utils import model_loader
    model_loader._cached_user_model = None
    yield
    model_loader._cached_user_model = None
