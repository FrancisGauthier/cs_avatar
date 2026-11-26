from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from cs_avatar.config import Settings
from cs_avatar.main import create_app
from cs_avatar.persistence.models import Base


@pytest.fixture
def app_client_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'steam-login-test.db'}",
        public_app_origin="https://testserver",
        steam_openid_realm="https://testserver/",
        steam_openid_return_to=(
            "https://testserver/api/v1/auth/steam/callback"
        ),
        session_secret=SecretStr("test-session-secret-with-more-than-32-bytes"),
        steam_web_api_key=SecretStr("test-steam-api-key"),
    )


@pytest_asyncio.fixture
async def app_client(app_client_settings: Settings) -> AsyncIterator[tuple[object, AsyncClient]]:
    settings = app_client_settings
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        engine: AsyncEngine = app.state.engine
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url=settings.public_app_origin,
        ) as client:
            yield app, client
