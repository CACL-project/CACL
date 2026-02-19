import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Database
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cacl_demo")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # Auth mode: "cookie" or "bearer"
    USE_COOKIE_AUTH: bool = os.getenv("USE_COOKIE_AUTH", "true").lower() == "true"

    # Cookie names (must match library config via env vars)
    COOKIE_ACCESS_NAME: str = os.getenv("COOKIE_ACCESS_NAME", "access_token")
    COOKIE_REFRESH_NAME: str = os.getenv("COOKIE_REFRESH_NAME", "refresh_token")


settings = Settings()
