from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def register_session_maker(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """
    Регистрирует async_sessionmaker из проекта.
    Библиотека НЕ создаёт собственный engine, а использует тот,
    который передал основной проект.
    """
    global async_session_maker
    async_session_maker = session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: yields a session from the registered session maker.
    Caller controls transaction (commit/rollback).
    """
    if async_session_maker is None:
        raise RuntimeError(
            "CACL: async_session_maker is not registered. "
            "Call register_session_maker(async_session_maker) at startup."
        )
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
