import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import re
import logging
from getpass import getpass
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.db import async_session_maker
from app.models.users import User

logger = logging.getLogger(__name__)


async def create_user():
    """
    Безопасное создание пользователя в системе.
    Поддерживает non-interactive режим через EMAIL и PASSWORD env vars.
    """
    logger.info("Запуск скрипта создания пользователя")

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    if email and password:
        email = email.strip().lower()
    else:
        email = input("Введите email пользователя: ").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
            logger.error("Некорректный формат email: %s", email)
            return

        password = getpass("Введите пароль пользователя: ").strip()
        password_confirm = getpass("Повторите пароль: ").strip()

        if password != password_confirm:
            logger.error("Пароли не совпадают.")
            return

    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        logger.error("Некорректный формат email: %s", email)
        return
    if len(password) < 5:
        logger.error("Пароль слишком короткий (мин. 5 символов).")
        return

    async with async_session_maker() as session:
        try:
            result = await session.execute(User.__table__.select().where(User.email == email))
            existing_user = result.first()

            if existing_user:
                logger.warning("Пользователь с email %s уже существует.", email)
                return

            new_user = User(
                email=email,
                is_admin=False,
                is_active=True,
                email_verify=True,
            )
            new_user.set_password(password)

            session.add(new_user)
            await session.commit()
            logger.info("Создан новый пользователь: %s", email)

        except IntegrityError:
            await session.rollback()
            logger.error("Email (%s) уже используется.", email)
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception("Ошибка при работе с БД: %s", e)
        except Exception as e:
            await session.rollback()
            logger.exception("Непредвиденная ошибка при создании пользователя: %s", e)

    logger.info("Завершено создание пользователя")


if __name__ == "__main__":
    try:
        asyncio.run(create_user())
    except KeyboardInterrupt:
        logger.warning("Операция отменена пользователем.")
