from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cacl.settings import settings
from cacl.services.jwt_token_service import create_jwt_token, verify_jwt_token, blacklist_token
from cacl.utils.security import set_auth_tokens, clear_auth_tokens
from cacl.models.jwt_token import JWTToken

from app.db import async_session_maker
from app.models.users import User
from app.schemas.auth import LoginRequest


router = APIRouter(prefix="/auth", tags=["auth"])


async def _authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    """
    Authenticate user by email and password.
    Returns user if valid, raises HTTPException otherwise.
    """
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


async def _create_tokens_and_respond(session: AsyncSession, user: User) -> JSONResponse:
    """
    Create access and refresh tokens, commit, and return response.
    """
    access_token = await create_jwt_token(session, user=user, token_type="access")
    refresh_token = await create_jwt_token(session, user=user, token_type="refresh")
    await session.commit()

    response = JSONResponse(content={"detail": "Login successful"})
    set_auth_tokens(response, access_token, refresh_token)
    return response


def _extract_refresh_token(request: Request, refresh_cookie: str | None) -> str | None:
    """
    Extract refresh token from cookie or Authorization header.
    """
    if settings.USE_COOKIE_AUTH:
        return refresh_cookie

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


@router.post("/login")
async def login(data: LoginRequest):
    """
    Regular user login.
    """
    async with async_session_maker() as session:
        user = await _authenticate_user(session, data.email, data.password)
        return await _create_tokens_and_respond(session, user)


@router.post("/admin/login")
async def admin_login(data: LoginRequest):
    """
    Admin-only login. Rejects non-admin users.
    """
    async with async_session_maker() as session:
        user = await _authenticate_user(session, data.email, data.password)

        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access only",
            )

        return await _create_tokens_and_respond(session, user)


@router.post("/logout")
async def logout(
    request: Request,
    refresh_token_cookie: str | None = Cookie(default=None, alias=settings.COOKIE_REFRESH_NAME),
):
    """
    Logout via refresh token:
    - Verify refresh token
    - Blacklist refresh token
    - Blacklist all active access tokens for the user
    """
    refresh_token = _extract_refresh_token(request, refresh_token_cookie)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    async with async_session_maker() as session:
        user = await verify_jwt_token(session, refresh_token, token_type="refresh")

        await blacklist_token(session, refresh_token)

        await session.execute(
            update(JWTToken)
            .where(
                JWTToken.user_id == user.id,
                JWTToken.token_type == "access",
                JWTToken.is_blacklisted == False,
                JWTToken.expires_at > datetime.utcnow(),
            )
            .values(is_blacklisted=True)
        )

        await session.commit()

    response = JSONResponse(content={"detail": "Logged out"})
    clear_auth_tokens(response)
    return response


@router.post("/refresh")
async def refresh(
    request: Request,
    refresh_token_cookie: str | None = Cookie(default=None, alias=settings.COOKIE_REFRESH_NAME),
):
    """
    Refresh tokens: verify refresh token, issue new access and refresh tokens.
    Blacklists the old refresh token (token rotation).
    """
    refresh_token = _extract_refresh_token(request, refresh_token_cookie)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    async with async_session_maker() as session:
        user = await verify_jwt_token(session, refresh_token, token_type="refresh")

        await blacklist_token(session, refresh_token)

        access_token = await create_jwt_token(session, user=user, token_type="access")
        new_refresh_token = await create_jwt_token(session, user=user, token_type="refresh")
        await session.commit()

        response = JSONResponse(content={"detail": "Tokens refreshed"})
        set_auth_tokens(response, access_token, new_refresh_token)
        return response
