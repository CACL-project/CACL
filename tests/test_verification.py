"""
Tests for JWT token verification in cacl library.
"""
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from cacl.services.jwt_token_service import create_jwt_token, verify_jwt_token, blacklist_token
from cacl.settings import settings


@pytest.mark.asyncio
async def test_verify_valid_access_token_returns_user(session, active_user):
    """verify_jwt_token returns the user for a valid access token."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    user = await verify_jwt_token(session, token, token_type="access")

    assert user.id == active_user.id
    assert user.email == active_user.email


@pytest.mark.asyncio
async def test_verify_valid_refresh_token_returns_user(session, active_user):
    """verify_jwt_token returns the user for a valid refresh token."""
    token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    user = await verify_jwt_token(session, token, token_type="refresh")

    assert user.id == active_user.id


@pytest.mark.asyncio
async def test_verify_expired_token_rejected(session, active_user):
    """verify_jwt_token rejects an expired token."""
    # Create token that expires immediately
    token = await create_jwt_token(
        session,
        user=active_user,
        token_type="access",
        expires_delta=timedelta(seconds=-1),  # Already expired
    )
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_blacklisted_token_rejected(session, active_user):
    """verify_jwt_token rejects a blacklisted token."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Blacklist the token
    await blacklist_token(session, token)
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401
    assert "invalid" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_wrong_token_type_rejected(session, active_user):
    """verify_jwt_token rejects token with wrong type."""
    # Create refresh token
    token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    # Try to verify as access token
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401
    assert "type" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_malformed_token_rejected(session):
    """verify_jwt_token rejects malformed tokens."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, "not.a.valid.jwt.token", token_type="access")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_not_in_db_rejected(session, active_user):
    """verify_jwt_token rejects token that's not in the database."""
    # Create a valid JWT manually (not via create_jwt_token)
    import uuid
    from datetime import datetime

    payload = {
        "sub": str(active_user.id),
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }
    fake_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, fake_token, token_type="access")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_with_wrong_secret_rejected(session, active_user):
    """verify_jwt_token rejects token signed with wrong secret."""
    import uuid
    from datetime import datetime

    payload = {
        "sub": str(active_user.id),
        "type": "access",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }
    fake_token = jwt.encode(payload, "wrong_secret_key", algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, fake_token, token_type="access")

    assert exc_info.value.status_code == 401
