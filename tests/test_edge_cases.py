"""
Tests for edge cases in cacl library.
"""
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from cacl.services.jwt_token_service import create_jwt_token, verify_jwt_token, blacklist_token
from cacl.settings import settings


@pytest.mark.asyncio
async def test_inactive_user_rejected(session, inactive_user):
    """verify_jwt_token rejects tokens for inactive users."""
    token = await create_jwt_token(session, user=inactive_user, token_type="access")
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401
    assert "неактивен" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_refresh_token_reuse_rejected_after_blacklist(session, active_user):
    """
    Simulates refresh token rotation:
    1. Create refresh token
    2. Use it (blacklist old, create new)
    3. Try to reuse old refresh token -> rejected
    """
    # Step 1: Create original refresh token
    old_refresh = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    # Step 2: Simulate rotation - blacklist old and create new
    await blacklist_token(session, old_refresh)
    new_refresh = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    # New token works
    user = await verify_jwt_token(session, new_refresh, token_type="refresh")
    assert user.id == active_user.id

    # Step 3: Old token is rejected
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, old_refresh, token_type="refresh")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_multiple_tokens_for_same_user(session, active_user):
    """Multiple valid tokens can exist for the same user."""
    token1 = await create_jwt_token(session, user=active_user, token_type="access")
    token2 = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Both tokens are valid
    user1 = await verify_jwt_token(session, token1, token_type="access")
    user2 = await verify_jwt_token(session, token2, token_type="access")

    assert user1.id == active_user.id
    assert user2.id == active_user.id


@pytest.mark.asyncio
async def test_jti_ensures_uniqueness(session, active_user):
    """
    JTI claim ensures tokens created at the same moment are unique.
    This prevents UNIQUE constraint violations on the token column.
    """
    tokens = []
    for _ in range(10):
        token = await create_jwt_token(session, user=active_user, token_type="access")
        tokens.append(token)

    await session.commit()

    # All tokens are unique strings
    assert len(set(tokens)) == 10

    # All tokens have unique JTI values
    jtis = []
    for token in tokens:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        jtis.append(payload["jti"])

    assert len(set(jtis)) == 10


@pytest.mark.asyncio
async def test_token_with_custom_expiry(session, active_user):
    """create_jwt_token respects custom expires_delta."""
    # Create token with 1 hour expiry
    token = await create_jwt_token(
        session,
        user=active_user,
        token_type="access",
        expires_delta=timedelta(hours=1),
    )
    await session.commit()

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    # exp should be roughly 1 hour from iat
    exp_delta = payload["exp"] - payload["iat"]
    assert 3550 <= exp_delta <= 3650  # ~1 hour with some tolerance


@pytest.mark.asyncio
async def test_access_and_refresh_tokens_have_different_expiry(session, active_user):
    """Access tokens expire faster than refresh tokens."""
    access_token = await create_jwt_token(session, user=active_user, token_type="access")
    refresh_token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    access_payload = jwt.decode(access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    refresh_payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    access_exp = access_payload["exp"] - access_payload["iat"]
    refresh_exp = refresh_payload["exp"] - refresh_payload["iat"]

    # Refresh token should have longer expiry
    assert refresh_exp > access_exp


@pytest.mark.asyncio
async def test_blacklist_one_token_does_not_affect_others(session, active_user):
    """Blacklisting one token does not affect other tokens for the same user."""
    token1 = await create_jwt_token(session, user=active_user, token_type="access")
    token2 = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Blacklist only token1
    await blacklist_token(session, token1)
    await session.commit()

    # token1 is rejected
    with pytest.raises(HTTPException):
        await verify_jwt_token(session, token1, token_type="access")

    # token2 still works
    user = await verify_jwt_token(session, token2, token_type="access")
    assert user.id == active_user.id


@pytest.mark.asyncio
async def test_verify_token_with_empty_string(session):
    """verify_jwt_token rejects empty string token."""
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, "", token_type="access")

    assert exc_info.value.status_code == 401
