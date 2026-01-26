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
    Create a regular user in the system.
    Supports non-interactive mode via EMAIL and PASSWORD env vars.
    """
    logger.info("Starting user creation script")

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    if email and password:
        email = email.strip().lower()
    else:
        email = input("Enter user email: ").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
            logger.error("Invalid email format: %s", email)
            return

        password = getpass("Enter user password: ").strip()
        password_confirm = getpass("Confirm password: ").strip()

        if password != password_confirm:
            logger.error("Passwords do not match.")
            return

    if not re.match(r"^[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        logger.error("Invalid email format: %s", email)
        return
    if len(password) < 5:
        logger.error("Password too short (min 5 characters).")
        return

    async with async_session_maker() as session:
        try:
            result = await session.execute(User.__table__.select().where(User.email == email))
            existing_user = result.first()

            if existing_user:
                logger.warning("User with email %s already exists.", email)
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
            logger.info("Created new user: %s", email)

        except IntegrityError:
            await session.rollback()
            logger.error("Email (%s) already in use.", email)
        except SQLAlchemyError as e:
            await session.rollback()
            logger.exception("Database error: %s", e)
        except Exception as e:
            await session.rollback()
            logger.exception("Unexpected error creating user: %s", e)

    logger.info("User creation completed")


if __name__ == "__main__":
    try:
        asyncio.run(create_user())
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user.")
