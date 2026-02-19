from app.settings import settings
from app.schemas.auth import RefreshRequest, LogoutRequest


def get_refresh_token(
    body: RefreshRequest | LogoutRequest | None,
    cookie_value: str | None,
) -> str | None:
    """
    Extract refresh token based on auth mode.
    Cookie mode: returns cookie value.
    Bearer mode: returns token from request body.
    """
    if settings.USE_COOKIE_AUTH:
        return cookie_value
    return body.refresh_token if body else None
