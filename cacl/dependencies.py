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
    Универсальный механизм извлечения access-токена:
    • если cookie-режим включён → читаем HttpOnly cookie
    • иначе → Authorization: Bearer <token>
    """

    # Cookie-mode
    if settings.USE_COOKIE_AUTH:
        return access_cookie

    # Header-mode
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
    Обязательная авторизация:
    • cookie mode → токен из HttpOnly cookie
    • header mode → токен из Authorization
    • проверка токена в БД и активности пользователя
    """
    token = await _extract_token(request, access_token_cookie)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )

    if len(token) > MAX_TOKEN_LEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
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
    Защита админских эндпоинтов:
    • проверяет current_user.is_admin
    """
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещён. Только для администратора.",
        )

    return current_user
