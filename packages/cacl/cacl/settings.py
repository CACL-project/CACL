import logging
import os
import warnings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("cacl.settings")

_DEV_SECRET = "CHANGE_ME_DEV_SECRET"


class Settings:
    """
    CACL settings loaded from environment variables.
    Independent of application settings.
    """

    # Path to User model class, e.g.: "app.models.users.User"
    CACL_USER_MODEL: str | None = os.getenv("CACL_USER_MODEL")

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", _DEV_SECRET)
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "1"))

    # Cookie mode
    USE_COOKIE_AUTH: bool = os.getenv("USE_COOKIE_AUTH", "true").lower() == "true"
    COOKIE_ACCESS_NAME: str = os.getenv("COOKIE_ACCESS_NAME", "access_token")
    COOKIE_REFRESH_NAME: str = os.getenv("COOKIE_REFRESH_NAME", "refresh_token")
    COOKIE_DOMAIN: str | None = os.getenv("COOKIE_DOMAIN")
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = os.getenv("COOKIE_SAMESITE", "Lax")


settings = Settings()

if settings.JWT_SECRET_KEY == _DEV_SECRET:
    warnings.warn(
        "CACL: JWT_SECRET_KEY is set to the default development value ('CHANGE_ME_DEV_SECRET'). "
        "Set a strong, unique JWT_SECRET_KEY in your environment before deploying to production.",
        UserWarning,
        stacklevel=1,
    )
