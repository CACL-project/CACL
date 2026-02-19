from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request body for token refresh in Bearer mode."""
    refresh_token: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Valid refresh token obtained from login or previous refresh",
    )


class LogoutRequest(BaseModel):
    """Request body for logout in Bearer mode."""
    refresh_token: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        description="Refresh token to revoke (also revokes all associated access tokens)",
    )
