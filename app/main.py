import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import async_session_maker
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.settings import settings as app_settings
from cacl.db import register_session_maker
from cacl.settings import settings as cacl_settings

logger = logging.getLogger(__name__)


def validate_auth_mode_consistency():
    """
    Validate that demo app and library have consistent USE_COOKIE_AUTH setting.
    Both must read from the same environment variable, so a mismatch indicates
    a configuration problem (e.g., stale cache, different .env files).
    """
    app_mode = app_settings.USE_COOKIE_AUTH
    lib_mode = cacl_settings.USE_COOKIE_AUTH

    if app_mode != lib_mode:
        raise RuntimeError(
            f"Configuration mismatch detected!\n"
            f"  app.settings.USE_COOKIE_AUTH = {app_mode}\n"
            f"  cacl.settings.USE_COOKIE_AUTH = {lib_mode}\n\n"
            f"Both the demo app and the CACL library must use the same auth mode.\n"
            f"This typically happens when:\n"
            f"  1. You changed USE_COOKIE_AUTH in .env but didn't recreate the container\n"
            f"  2. Multiple .env files exist with different values\n\n"
            f"Fix: Ensure USE_COOKIE_AUTH is set consistently in your .env file,\n"
            f"then recreate the container (restart is NOT sufficient):\n"
            f"  docker compose down && docker compose up -d\n"
            f"Or: docker compose up -d --force-recreate"
        )

    mode_name = "Cookie" if app_mode else "Bearer"
    logger.info(f"Auth mode: {mode_name} (USE_COOKIE_AUTH={app_mode})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_auth_mode_consistency()
    yield


register_session_maker(async_session_maker)

app = FastAPI(title="CACL Demo App", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(users_router)
