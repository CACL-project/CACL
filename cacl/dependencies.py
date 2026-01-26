from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from cacl.settings import settings
from cacl.services.jwt_token_service import verify_jwt_token
from cacl.db import get_db_session


# Guard against oversized tokens (DoS protection)
MAX_TOKEN_LEN = 2048


# TOKEN EXTRACTOR

async def _extract_token(request: Request, access_cookie: str | None) -> str | None:
    """
    Extract access token from request.
    Cookie mode: reads HttpOnly cookie.
    Header mode: reads Authorization: Bearer header.
    """
    if settings.USE_COOKIE_AUTH:
        return access_cookie

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


# MAIN DEPENDENCIES

async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    access_token_cookie: str | None = Cookie(default=None, alias=settings.COOKIE_ACCESS_NAME),
):
    """
    FastAPI dependency for protected routes.
    Extracts and validates access token, returns authenticated user.
    Raises HTTPException 401 if token is missing, invalid, or user is inactive.
    """
    token = await _extract_token(request, access_token_cookie)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
        )

    if len(token) > MAX_TOKEN_LEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return await verify_jwt_token(
        session=session,
        token=token,
        token_type="access",
    )


async def get_current_admin(
    current_user=Depends(get_current_user),
):
    """
    FastAPI dependency for admin-only routes.
    Validates that current_user.is_admin is True.
    Raises HTTPException 403 if user is not an admin.
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required.",
        )

    return current_user
