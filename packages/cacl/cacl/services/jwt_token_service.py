import logging
import uuid
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import HTTPException, status
from jose import jwt, JWTError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from cacl.settings import settings
from cacl.models.jwt_token import JWTToken
from cacl.utils.model_loader import get_user_model

logger = logging.getLogger("cacl.jwt_token_service")


async def create_jwt_token(
    session: AsyncSession,
    *,
    user,
    token_type: Literal["access", "refresh"],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT token and add record to session.
    Caller is responsible for commit.
    """
    now = datetime.utcnow()

    if token_type == "access":
        expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    elif token_type == "refresh":
        expire = now + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
    else:
        raise HTTPException(status_code=400, detail="Invalid token type")

    payload = {"sub": str(user.id), "type": token_type, "exp": expire, "iat": now, "jti": str(uuid.uuid4())}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    db_token = JWTToken(
        user_id=user.id,
        token=token,
        token_type=token_type,
        expires_at=expire,
    )
    session.add(db_token)

    return token


async def verify_jwt_token(
    session: AsyncSession,
    token: str,
    token_type: Literal["access", "refresh"],
):
    """
    Verify token and return user.
    Validates signature, type, database record, blacklist status, and user.is_active.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != token_type:
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing user_id in token")

    try:
        result = await session.execute(
            select(JWTToken).where(
                JWTToken.token == token,
                JWTToken.token_type == token_type,
            )
        )
        db_token = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.exception("Database error during token verification: %s", e)
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    if not db_token or not db_token.is_valid():
        raise HTTPException(status_code=401, detail="Token is invalid")

    User = get_user_model()
    try:
        user = await session.get(User, db_token.user_id)
    except SQLAlchemyError as e:
        logger.exception("Database error loading user: %s", e)
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    if not user or not getattr(user, "is_active", False):
        raise HTTPException(status_code=401, detail="User is inactive")

    return user


async def blacklist_token(session: AsyncSession, token: str) -> None:
    """
    Revoke token by marking it as blacklisted.
    Caller is responsible for commit.
    """
    await session.execute(
        update(JWTToken).where(JWTToken.token == token).values(is_blacklisted=True)
    )
    logger.info("Token added to blacklist")
