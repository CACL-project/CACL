from fastapi import APIRouter, HTTPException, status, Cookie
from fastapi.responses import JSONResponse

from cacl.utils.security import set_auth_tokens, clear_auth_tokens

from app.db import async_session_maker
from app.settings import settings
from app.schemas.auth import LoginRequest, RefreshRequest, LogoutRequest
from app.services import auth as auth_service
from app.utils.auth import get_refresh_token


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(data: LoginRequest):
    async with async_session_maker() as session:
        user = await auth_service.authenticate_user(session, data.email, data.password)
        access_token, refresh_token = await auth_service.create_tokens(session, user)

    response = JSONResponse(content={"detail": "Login successful"})
    set_auth_tokens(response, access_token, refresh_token)
    return response


@router.post("/admin/login")
async def admin_login(data: LoginRequest):
    async with async_session_maker() as session:
        user = await auth_service.authenticate_user(session, data.email, data.password)

        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access only",
            )

        access_token, refresh_token = await auth_service.create_tokens(session, user)

    response = JSONResponse(content={"detail": "Login successful"})
    set_auth_tokens(response, access_token, refresh_token)
    return response


@router.post("/refresh")
async def refresh(
    body: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias=settings.COOKIE_REFRESH_NAME),
):
    refresh_token = get_refresh_token(body, refresh_token_cookie)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    async with async_session_maker() as session:
        _, access_token, new_refresh_token = await auth_service.refresh_tokens(
            session, refresh_token
        )

    response = JSONResponse(content={"detail": "Tokens refreshed"})
    set_auth_tokens(response, access_token, new_refresh_token)
    return response


@router.post("/logout")
async def logout(
    body: LogoutRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias=settings.COOKIE_REFRESH_NAME),
):
    refresh_token = get_refresh_token(body, refresh_token_cookie)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    async with async_session_maker() as session:
        await auth_service.logout_user(session, refresh_token)

    response = JSONResponse(content={"detail": "Logged out"})
    clear_auth_tokens(response)
    return response
