"""
Tests that confirm FK decoupling between JWTToken and the users table.

Key scenarios:
1. Orphaned token (user hard-deleted) must be rejected by verify_jwt_token.
2. User model can live on a completely separate SQLAlchemy Base — CACL JWTToken
   must still work against the same database without sharing metadata.
"""
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import Column, String, Boolean, DateTime, text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

from cacl.models.base import Base as CACLBase
from cacl.models.jwt_token import JWTToken
from cacl.services.jwt_token_service import create_jwt_token, verify_jwt_token


# ---------------------------------------------------------------------------
# Independent Base — proves CACL does not require users to share CACLBase
# ---------------------------------------------------------------------------

class IndependentBase(DeclarativeBase):
    """A completely separate SQLAlchemy Base — not related to CACLBase."""
    pass


class IndependentUser(IndependentBase):
    """User model on its own Base, mirroring demo_app architecture."""
    __tablename__ = "users_independent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IndependentUser {self.email}>"


# ---------------------------------------------------------------------------
# Test 1: orphaned token is rejected after user hard-delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verify_token_rejected_after_user_hard_delete(session, active_user):
    """
    Verify that an orphaned JWT token (user deleted from DB) is rejected.

    This test proves that even without a DB-level FK constraint on jwt_tokens.user_id,
    the security guarantee is maintained: verify_jwt_token loads the user and raises
    HTTP 401 if the user no longer exists.
    """
    # Create a valid access token
    token = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    user_id = active_user.id

    # Hard-delete the user directly — no cascade because there is no FK anymore
    await session.execute(
        text("DELETE FROM users WHERE id = :uid"),
        {"uid": str(user_id)},
    )
    await session.commit()

    # Expire the session's identity map so SQLAlchemy does NOT serve the deleted
    # user from cache.  This replicates what would happen in a real request where
    # the session is fresh and has no in-memory state.
    session.expire_all()

    # Token record still exists in jwt_tokens (no CASCADE delete)
    # verify_jwt_token must reject it because the user is gone
    with pytest.raises(HTTPException) as exc_info:
        await verify_jwt_token(session, token, token_type="access")

    assert exc_info.value.status_code == 401
    # Error message should indicate user is inactive/missing
    assert "inactive" in exc_info.value.detail.lower() or "invalid" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Test 2: jwt_tokens row survives user deletion (no cascade without FK)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jwt_token_row_survives_user_deletion(session, active_user):
    """
    Without a DB-level FK, deleting a user does NOT automatically delete their tokens.
    The application is responsible for cleanup.

    This test documents the expected behavior and ensures no DB error on delete.
    """
    token_str = await create_jwt_token(session, user=active_user, token_type="access")
    await session.commit()

    user_id = active_user.id

    # Delete user — should NOT cascade to jwt_tokens (no FK)
    await session.execute(
        text("DELETE FROM users WHERE id = :uid"),
        {"uid": str(user_id)},
    )
    await session.commit()

    # Token record must still be present in the DB
    result = await session.execute(
        select(JWTToken).where(JWTToken.token == token_str)
    )
    db_token = result.scalar_one_or_none()

    assert db_token is not None, (
        "jwt_tokens row should survive user deletion when there is no DB-level FK. "
        "The application must run its own cleanup."
    )
    assert db_token.user_id == user_id


# ---------------------------------------------------------------------------
# Test 3: User on a separate Base — CACL JWTToken still works
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cacl_works_with_user_on_separate_base(engine):
    """
    Confirms that CACL's JWTToken can operate against a user model that lives
    on a completely different SQLAlchemy Base.

    This is the primary metadata-independence test: we create a users_independent
    table on IndependentBase (separate from CACLBase), save a user there, create
    a JWT token, then verify the token — all without the user table sharing
    CACL's declarative Base.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker as asm
    from cacl.utils import model_loader
    # Patch the settings object that model_loader.py actually uses (imported at module level)
    ml_settings = model_loader.settings

    original_user_model = ml_settings.CACL_USER_MODEL
    ml_settings.CACL_USER_MODEL = "tests.test_no_fk_decoupling.IndependentUser"
    model_loader._cached_user_model = None

    # Use a completely fresh session maker so there are no shared connections
    # with the CACLBase fixtures.
    session_maker = asm(engine, expire_on_commit=False)

    try:
        # Create the independent users table in its own transaction
        async with engine.begin() as conn:
            await conn.run_sync(IndependentBase.metadata.create_all)

        user_id = uuid.uuid4()

        async with session_maker() as session:
            # Persist the IndependentUser
            user = IndependentUser(
                id=user_id,
                email="independent@test.com",
                is_admin=False,
                is_active=True,
            )
            session.add(user)
            await session.commit()

            # Create a JWT token for the independent user
            token = await create_jwt_token(session, user=user, token_type="access")
            await session.commit()

        # Open a FRESH session to simulate a new request (no cached state)
        async with session_maker() as fresh_session:
            verified_user = await verify_jwt_token(fresh_session, token, token_type="access")

            assert verified_user.id == user_id
            assert verified_user.is_active is True

    finally:
        # Restore original CACL_USER_MODEL for other tests
        ml_settings.CACL_USER_MODEL = original_user_model
        model_loader._cached_user_model = None

        async with engine.begin() as conn:
            await conn.run_sync(IndependentBase.metadata.drop_all)


# ---------------------------------------------------------------------------
# Test 4: user_id column has no FK constraint in DB schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_jwt_tokens_user_id_has_no_fk_constraint(engine):
    """
    Introspects the database to confirm there is no FK constraint on
    jwt_tokens.user_id.  This guards against accidental re-introduction of the FK.
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT count(*)
                  FROM information_schema.table_constraints tc
                  JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                   AND tc.table_schema = kcu.table_schema
                 WHERE tc.constraint_type = 'FOREIGN KEY'
                   AND tc.table_name = 'jwt_tokens'
                   AND kcu.column_name = 'user_id'
                """
            )
        )
        fk_count = result.scalar()

    assert fk_count == 0, (
        f"Expected 0 FK constraints on jwt_tokens.user_id, found {fk_count}. "
        "CACL must not define a DB-level FK to the users table."
    )
