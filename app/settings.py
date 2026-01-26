import os

from dotenv import load_dotenv

load_dotenv()


class Settings:

    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT: int = os.getenv("POSTGRES_PORT")

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "1"))

    # Cookie settings
    USE_COOKIE_AUTH: bool = os.getenv("USE_COOKIE_AUTH", "true").lower() == "true"
    COOKIE_ACCESS_NAME = "access_token"
    COOKIE_REFRESH_NAME = "refresh_token"
    COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")
    COOKIE_SECURE = False  # Set True in production (HTTPS only)
    COOKIE_HTTPONLY = True  # Not accessible from JavaScript
    COOKIE_SAMESITE = "Lax"






settings = Settings()

