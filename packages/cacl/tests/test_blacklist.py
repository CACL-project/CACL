"""
Tests for token blacklisting in cacl library.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from cacl.services.jwt_token_service import create_jwt_token, blacklist_token, verify_jwt_token
from cacl.models.jwt_token import JWTToken


@pytest.mark.asyncio
async def test_blacklist_token_marks_as_blacklisted(session, active_user):
    """blacklist_token sets is_blacklisted=True in the database."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Verify token is not blacklisted initially
    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token)
    )
    db_token = result.scalar_one()
    assert db_token.is_blacklisted is False

    # Blacklist the token
    await blacklist_token(session, token)
    await session.commit()

    # Refresh and verify
    await session.refresh(db_token)
    assert db_token.is_blacklisted is True


@pytest.mark.asyncio
async def test_blacklisted_token_cannot_be_verified(session, active_user):
    """A blacklisted token fails verification."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Verify works before blacklist
    user = await verify_jwt_token(session, token, token_type="access")
    assert user.id == active_user.id

    # Blacklist
    await blacklist_token(session, token)
    await session.commit()

    # Verify fails after blacklist
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_blacklist_refresh_token(session, active_user):
    """blacklist_token works for refresh tokens."""
    token = await create_jwt_token(session, user=active_user, token_type="refresh")
    await session.commit()

    await blacklist_token(session, token)
    await session.commit()

    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token)
    )
    db_token = result.scalar_one()
    assert db_token.is_blacklisted is True


@pytest.mark.asyncio
async def test_no_commit_inside_blacklist_token(session, active_user):
    """blacklist_token does not commit - caller controls transaction."""
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # Blacklist but don't commit
    await blacklist_token(session, token)

    # Rollback
    await session.rollback()

    # Token should NOT be blacklisted
    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token)
    )
    db_token = result.scalar_one()
    assert db_token.is_blacklisted is False


@pytest.mark.asyncio
async def test_blacklist_nonexistent_token_no_error(session):
    """blacklist_token does not raise error for nonexistent token."""
    # This should not raise - it's a no-op for missing tokens
    await blacklist_token(session, "nonexistent.token.string")
    await session.commit()
    # No exception = success
