from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cacl.services.jwt_token_service import (
    create_jwt_token,
    verify_jwt_token,
    blacklist_token,
)
from cacl.models.jwt_token import JWTToken

from app.models.users import User


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Validate credentials and return user."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.verify_password(password):
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


async def create_tokens(
    session: AsyncSession,
    user: User,
) -> tuple[str, str]:
    """Create access and refresh tokens for user."""
    access_token = await create_jwt_token(session, user=user, token_type="access")
    refresh_token = await create_jwt_token(session, user=user, token_type="refresh")
    await session.commit()
    return access_token, refresh_token


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
) -> tuple[User, str, str]:
    """Verify refresh token, rotate, return user and new tokens."""
    user = await verify_jwt_token(session, refresh_token, token_type="refresh")
    await blacklist_token(session, refresh_token)

    new_access = await create_jwt_token(session, user=user, token_type="access")
    new_refresh = await create_jwt_token(session, user=user, token_type="refresh")
    await session.commit()

    return user, new_access, new_refresh


async def logout_user(
    session: AsyncSession,
    refresh_token: str,
) -> None:
    """Blacklist refresh token and all active access tokens for user."""
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
