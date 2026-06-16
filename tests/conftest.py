from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete


TEST_DB_PATH = Path(__file__).resolve().parent / "test.db"

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("FRONTEND_URL", "http://localhost:4173")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-with-at-least-thirty-two-bytes")
os.environ.setdefault("META_APP_ID", "test-meta-app")
os.environ.setdefault("META_APP_SECRET", "test-meta-secret")
os.environ.setdefault("META_OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/meta/oauth/callback")
os.environ.setdefault("FIELD_ENCRYPTION_KEY", "1p_UUU0j5OJ9SxWwtUWFI7Ak4luuL8EA3twJY86W0Z0=")
os.environ.setdefault("INTERNAL_ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

from main import app
from core.container import reset_container
from core.models.auth_session import AuthSession
from core.models.base import Base
from core.models.db_helper import db_helper
from core.models.meta_ad_account import MetaAdAccount
from core.models.meta_connection import MetaConnection
from core.models.user import User


@pytest.fixture(scope="session", autouse=True)
def cleanup_database_file():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()

    yield

    asyncio.run(db_helper.engine.dispose())
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    async with db_helper.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield


@pytest_asyncio.fixture(autouse=True)
async def reset_state():
    reset_container()
    app.dependency_overrides.clear()

    async with db_helper.session_factory() as session:
        for model in (MetaAdAccount, MetaConnection, AuthSession, User):
            await session.execute(delete(model))
        await session.commit()

    yield

    app.dependency_overrides.clear()
    reset_container()


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    async with db_helper.session_factory() as session:
        yield session
