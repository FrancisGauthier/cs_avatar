from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cs_avatar.api.auth import router as auth_router
from cs_avatar.auth.steam_openid import configure_steam_openid_fetcher
from cs_avatar.config import Settings
from cs_avatar.safe_logging import configure_safe_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_safe_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        active_settings = app.state.settings or Settings()
        app.state.settings = active_settings
        configure_steam_openid_fetcher()
        engine = create_async_engine(active_settings.database_url, pool_pre_ping=True)
        app.state.engine = engine
        app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="CS Avatar", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(auth_router, prefix="/api/v1/auth")
    return app


app = create_app()
