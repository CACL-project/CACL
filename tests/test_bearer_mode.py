"""
Tests for Bearer mode authentication flows.

Tests in this file focus on:
- Pydantic schema validation (RefreshRequest, LogoutRequest)
- Response format for Bearer mode (set_auth_tokens)
- Content-Length header correctness

Note: Token verification logic is tested in test_verification.py.
"""
import json
import pytest
from unittest.mock import patch
from fastapi.responses import JSONResponse


class TestRefreshRequestSchema:
    """Tests for RefreshRequest Pydantic schema validation."""

    def test_valid_refresh_request(self):
        """Valid refresh_token is accepted."""
        from app.schemas.auth import RefreshRequest

        request = RefreshRequest(refresh_token="valid_token_string")
        assert request.refresh_token == "valid_token_string"

    def test_missing_refresh_token_rejected(self):
        """Missing refresh_token raises validation error."""
        from app.schemas.auth import RefreshRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            RefreshRequest()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("refresh_token",) for e in errors)

    def test_empty_refresh_token_rejected(self):
        """Empty string refresh_token raises validation error."""
        from app.schemas.auth import RefreshRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RefreshRequest(refresh_token="")

    def test_oversized_refresh_token_rejected(self):
        """Token exceeding max_length is rejected."""
        from app.schemas.auth import RefreshRequest
        from pydantic import ValidationError

        oversized_token = "x" * 2049

        with pytest.raises(ValidationError) as exc_info:
            RefreshRequest(refresh_token=oversized_token)

        errors = exc_info.value.errors()
        assert any("max_length" in str(e) or "2048" in str(e) for e in errors)

    def test_max_length_refresh_token_accepted(self):
        """Token at exactly max_length is accepted."""
        from app.schemas.auth import RefreshRequest

        max_length_token = "x" * 2048
        request = RefreshRequest(refresh_token=max_length_token)
        assert len(request.refresh_token) == 2048


class TestLogoutRequestSchema:
    """Tests for LogoutRequest Pydantic schema validation."""

    def test_valid_logout_request(self):
        """Valid refresh_token is accepted."""
        from app.schemas.auth import LogoutRequest

        request = LogoutRequest(refresh_token="valid_token_string")
        assert request.refresh_token == "valid_token_string"

    def test_missing_refresh_token_rejected(self):
        """Missing refresh_token raises validation error."""
        from app.schemas.auth import LogoutRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            LogoutRequest()

    def test_oversized_refresh_token_rejected(self):
        """Token exceeding max_length is rejected."""
        from app.schemas.auth import LogoutRequest
        from pydantic import ValidationError

        oversized_token = "x" * 2049

        with pytest.raises(ValidationError):
            LogoutRequest(refresh_token=oversized_token)


class TestTokenResponseFormat:
    """Tests for set_auth_tokens() behavior in both modes."""

    def test_bearer_mode_preserves_original_content(self):
        """Bearer mode preserves original response body and adds tokens."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "Login successful", "extra": "data"})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', False):
            with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                set_auth_tokens(response, "access_token_value", "refresh_token_value")

        body = json.loads(response.body)

        assert body["detail"] == "Login successful"
        assert body["extra"] == "data"
        assert "tokens" in body
        assert body["tokens"]["access_token"] == "access_token_value"
        assert body["tokens"]["refresh_token"] == "refresh_token_value"
        assert body["tokens"]["token_type"] == "bearer"

    def test_bearer_mode_includes_expires_in(self):
        """Bearer mode response includes expires_in field."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "Login successful"})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', False):
            with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                set_auth_tokens(response, "access", "refresh")

        body = json.loads(response.body)

        assert body["tokens"]["expires_in"] == 1800  # 30 * 60

    def test_bearer_mode_updates_content_length(self):
        """Bearer mode correctly updates Content-Length header."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "OK"})
        original_length = int(response.headers["content-length"])

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', False):
            with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                set_auth_tokens(response, "access_token", "refresh_token")

        new_length = int(response.headers["content-length"])
        actual_body_length = len(response.body)

        assert new_length == actual_body_length
        assert new_length > original_length

    def test_bearer_mode_content_length_matches_body(self):
        """Content-Length header matches actual body length (regression test)."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "Test message"})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', False):
            with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                set_auth_tokens(response, "a" * 100, "r" * 100)

        content_length = int(response.headers["content-length"])
        body_length = len(response.body)

        assert content_length == body_length, \
            f"Content-Length ({content_length}) must match body length ({body_length})"

    def test_bearer_mode_empty_initial_body(self):
        """Bearer mode handles empty initial body correctly."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', False):
            with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                set_auth_tokens(response, "access", "refresh")

        body = json.loads(response.body)
        assert "tokens" in body
        assert body["tokens"]["access_token"] == "access"

        content_length = int(response.headers["content-length"])
        assert content_length == len(response.body)

    def test_cookie_mode_body_unchanged(self):
        """Cookie mode does not modify response body."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "Login successful"})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', True):
            with patch.object(cacl.utils.security.settings, 'COOKIE_ACCESS_NAME', 'access_token'):
                with patch.object(cacl.utils.security.settings, 'COOKIE_REFRESH_NAME', 'refresh_token'):
                    with patch.object(cacl.utils.security.settings, 'COOKIE_HTTPONLY', True):
                        with patch.object(cacl.utils.security.settings, 'COOKIE_SECURE', False):
                            with patch.object(cacl.utils.security.settings, 'COOKIE_SAMESITE', 'Lax'):
                                with patch.object(cacl.utils.security.settings, 'COOKIE_DOMAIN', None):
                                    with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                                        with patch.object(cacl.utils.security.settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 1):
                                            set_auth_tokens(response, "access", "refresh")

        body = json.loads(response.body)
        assert body == {"detail": "Login successful"}
        assert "tokens" not in body

    def test_cookie_mode_sets_cookies(self):
        """Cookie mode sets access and refresh token cookies."""
        from cacl.utils.security import set_auth_tokens
        import cacl.utils.security

        response = JSONResponse(content={"detail": "OK"})

        with patch.object(cacl.utils.security.settings, 'USE_COOKIE_AUTH', True):
            with patch.object(cacl.utils.security.settings, 'COOKIE_ACCESS_NAME', 'access_token'):
                with patch.object(cacl.utils.security.settings, 'COOKIE_REFRESH_NAME', 'refresh_token'):
                    with patch.object(cacl.utils.security.settings, 'COOKIE_HTTPONLY', True):
                        with patch.object(cacl.utils.security.settings, 'COOKIE_SECURE', False):
                            with patch.object(cacl.utils.security.settings, 'COOKIE_SAMESITE', 'Lax'):
                                with patch.object(cacl.utils.security.settings, 'COOKIE_DOMAIN', None):
                                    with patch.object(cacl.utils.security.settings, 'ACCESS_TOKEN_EXPIRE_MINUTES', 30):
                                        with patch.object(cacl.utils.security.settings, 'REFRESH_TOKEN_EXPIRE_DAYS', 1):
                                            set_auth_tokens(response, "test_access", "test_refresh")

        set_cookie_headers = [h for h in response.raw_headers if h[0] == b"set-cookie"]
        assert len(set_cookie_headers) == 2

        cookie_values = [h[1].decode() for h in set_cookie_headers]
        assert any("access_token=test_access" in c for c in cookie_values)
        assert any("refresh_token=test_refresh" in c for c in cookie_values)
