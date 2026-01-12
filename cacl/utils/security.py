from fastapi.responses import JSONResponse
from cacl.settings import settings


def set_auth_tokens(response: JSONResponse, access_token: str, refresh_token: str):
    """
    Универсальный механизм сохранения токенов:
    - Если включён cookie-режим: ставим HttpOnly куки
    - Иначе — добавляем токены в тело ответа
    """

    if settings.USE_COOKIE_AUTH:
        response.set_cookie(
            key=settings.COOKIE_ACCESS_NAME,
            value=access_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
        response.set_cookie(
            key=settings.COOKIE_REFRESH_NAME,
            value=refresh_token,
            httponly=settings.COOKIE_HTTPONLY,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            domain=settings.COOKIE_DOMAIN,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        )

    else:
        # Старый JSON-формат (при разработке)
        response.body = response.render({
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
            }
        })


def clear_auth_tokens(response: JSONResponse):
    """Удаление токенов при logout"""
    if settings.USE_COOKIE_AUTH:
        response.delete_cookie(settings.COOKIE_ACCESS_NAME, domain=settings.COOKIE_DOMAIN)
        response.delete_cookie(settings.COOKIE_REFRESH_NAME, domain=settings.COOKIE_DOMAIN)
