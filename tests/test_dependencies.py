"""
Tests for FastAPI dependencies in cacl library.

Note: These tests focus on the dependency logic, not HTTP handling.
We test the underlying functions that the dependencies call.
"""
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from cacl.services.jwt_token_service import create_jwt_token, verify_jwt_token
from cacl.dependencies import get_current_admin, _extract_token, MAX_TOKEN_LEN


@pytest.mark.asyncio
async def test_get_current_user_via_verify_jwt_token(session, active_user):
    """
    get_current_user ultimately calls verify_jwt_token.
    Test that valid token returns the correct user.
    """
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    # This is what get_current_user calls internally
    user = await verify_jwt_token(session, token, token_type="access")

    assert user.id == active_user.id
    assert user.email == active_user.email
    assert user.is_active is True


@pytest.mark.asyncio
async def test_get_current_admin_allows_admin_user(session, admin_user):
    """get_current_admin allows users with is_admin=True."""
    # get_current_admin receives user from get_current_user
    # We test the admin check logic directly
    result = await get_current_admin(current_user=admin_user)

    assert result.id == admin_user.id
    assert result.is_admin is True


@pytest.mark.asyncio
async def test_get_current_admin_rejects_non_admin_user(session, active_user):
    """get_current_admin rejects users with is_admin=False."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=active_user)

    assert exc_info.value.status_code == 403
    assert "admin" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_admin_rejects_user_without_is_admin_attr():
    """get_current_admin rejects objects without is_admin attribute."""

    class FakeUser:
        id = "123"

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=FakeUser())

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_extract_token_from_cookie_mode():
    """_extract_token returns cookie value in cookie mode."""
    from unittest.mock import patch
    import cacl.dependencies

    request = MagicMock()

    # Patch the settings object used by _extract_token
    with patch.object(cacl.dependencies.settings, 'USE_COOKIE_AUTH', True):
        result = await _extract_token(request, access_cookie="test_token_value")

    assert result == "test_token_value"


@pytest.mark.asyncio
async def test_extract_token_from_header_mode():
    """_extract_token returns Bearer token from header in header mode."""
    import os
    os.environ["USE_COOKIE_AUTH"] = "false"

    from cacl import settings as settings_module
    settings_module.settings = settings_module.Settings()

    request = MagicMock()
    request.headers.get.return_value = "Bearer my_access_token"

    result = await _extract_token(request, access_cookie=None)

    assert result == "my_access_token"


@pytest.mark.asyncio
async def test_extract_token_returns_none_when_missing():
    """_extract_token returns None when no token is present."""
    import os
    os.environ["USE_COOKIE_AUTH"] = "false"

    from cacl import settings as settings_module
    settings_module.settings = settings_module.Settings()

    request = MagicMock()
    request.headers.get.return_value = None

    result = await _extract_token(request, access_cookie=None)

    assert result is None


@pytest.mark.asyncio
async def test_max_token_length_constant():
    """MAX_TOKEN_LEN is set to a reasonable value for DoS protection."""
    assert MAX_TOKEN_LEN == 2048
    assert isinstance(MAX_TOKEN_LEN, int)
