"""
Tests for JWT token creation in cacl library.
"""
import pytest
from jose import jwt
from sqlalchemy import select

from cacl.services.jwt_token_service import create_jwt_token
from cacl.models.jwt_token import JWTToken
from cacl.settings import settings


@pytest.mark.asyncio
async def test_create_access_token_returns_string(session, active_user):
    """create_jwt_token returns a non-empty string."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_create_access_and_refresh_tokens_differ(session, active_user):
    """Access and refresh tokens are different strings."""
    access_token = await create_jwt_token(session, user=active_user, token_type="access")
    refresh_token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    assert access_token != refresh_token


@pytest.mark.asyncio
async def test_token_payload_contains_required_claims(session, active_user):
    """Token payload contains sub, type, exp, iat, jti."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert "sub" in payload
    assert "type" in payload
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload

    assert payload["sub"] == str(active_user.id)
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_refresh_token_has_correct_type(session, active_user):
    """Refresh token has type='refresh' in payload."""
    token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_token_creates_db_record(session, active_user):
    """create_jwt_token adds a JWTToken record to the session."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token)
    )
    db_token = result.scalar_one_or_none()

    assert db_token is not None
    assert db_token.token == token
    assert db_token.token_type == "access"
    assert db_token.user_id == active_user.id
    assert db_token.is_blacklisted is False


@pytest.mark.asyncio
async def test_tokens_created_same_moment_are_unique(session, active_user):
    """Tokens created at the same moment have different jti values."""
    token1 = await create_jwt_token(session, user=active_user, token_type="access")
    token2 = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    assert token1 != token2

    payload1 = jwt.decode(token1, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    payload2 = jwt.decode(token2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    assert payload1["jti"] != payload2["jti"]


@pytest.mark.asyncio
async def test_no_commit_inside_create_jwt_token(session, active_user):
    """create_jwt_token does not commit - caller controls transaction."""
    token = await create_jwt_token(session, user=active_user, token_type="access")

    # Rollback without commit
    await session.rollback()

    # Token should NOT be in DB
    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token)
    )
    db_token = result.scalar_one_or_none()

    assert db_token is None
