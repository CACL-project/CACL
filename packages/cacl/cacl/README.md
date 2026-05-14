# CACL — Clear Authentication Control Library

A reusable JWT authentication library for FastAPI with database-backed token storage, blacklisting, and refresh token rotation.

## Features

- JWT access and refresh tokens with configurable expiration
- Database-backed token records (PostgreSQL)
- Token blacklisting for logout and rotation
- Unique tokens via `jti` claim (prevents collisions)
- Cookie or Bearer header authentication modes
- FastAPI dependencies for route protection
- Admin role support (`is_admin` flag)

## What CACL Does NOT Do

CACL is a **library**, not an application. It does **not**:

- Create database engines or sessions
- Run Alembic migrations
- Commit or rollback transactions
- Define HTTP endpoints
- Verify user credentials (password checking)

Your application owns the database connection, session lifecycle, and transaction control.

## Integration Contract

Your application must:

- Create the SQLAlchemy async engine and `async_sessionmaker`
- Call `register_session_maker(async_session_maker)` at startup, before any requests
- Define a User model satisfying `UserProtocol` (see below)
- Set `CACL_USER_MODEL` environment variable to the dotted path of your User model
- Call `await session.commit()` after `create_jwt_token()` or `blacklist_token()`
- Include CACL's `JWTToken` model in Alembic migrations

CACL will:

- Provide `get_db_session()` FastAPI dependency using your registered session maker
- Add token records to the session (without committing)
- Mark tokens as blacklisted (without committing)
- Roll back the session on exceptions in `get_db_session()`

## Installation

```bash
pip install cacl
```

Or for development:

```bash
pip install -e ./cacl
```

## Database Requirements

**PostgreSQL is required.** CACL uses PostgreSQL-specific features (UUID columns) and is not compatible with SQLite or other databases.

CACL does not bundle, configure, or start a database. Your application must:

1. Provision a PostgreSQL database
2. Provide the connection URL to SQLAlchemy
3. Run migrations to create the `jwt_tokens` table

Example connection URL format:

```
postgresql+asyncpg://user:password@host:5432/dbname
```

For testing, provide a separate test database (e.g., `cacl_test`).

## Required Environment Variables

```bash
# Required
CACL_USER_MODEL=your_app.models.User  # Dotted path to your User model
JWT_SECRET_KEY=your-secret-key        # CHANGE THIS in production

# Optional (with defaults)
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=1
USE_COOKIE_AUTH=true                  # false for Bearer header mode

# Cookie settings (when USE_COOKIE_AUTH=true)
COOKIE_ACCESS_NAME=access_token
COOKIE_REFRESH_NAME=refresh_token
COOKIE_DOMAIN=
COOKIE_SECURE=false                   # true in production with HTTPS
COOKIE_SAMESITE=Lax
```

## Quick Start

### 1. Define Your User Model

Your User model must satisfy `UserProtocol` from `cacl.protocols`:

```python
from typing import Protocol

class UserProtocol(Protocol):
    id: str       # UUID as string or UUID object
    is_active: bool
    is_admin: bool
```

CACL requires only these three fields. Your model may include additional fields (email, password_hash, etc.), but CACL does not access them. Credential verification is your application's responsibility.

**Minimal example:**

```python
import uuid
from sqlalchemy import Column, Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase

# Your application's own Base — not CACL's.
# CACL does not require your models to share its Base.
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    # Application-specific fields (not used by CACL):
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
```

### 2. Register Session Maker at Startup

Use FastAPI's `lifespan` context manager so registration happens at app startup,
not at import time:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from cacl.db import register_session_maker

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_session_maker(async_session_maker)
    yield


app = FastAPI(lifespan=lifespan)
```

> **Note:** calling `register_session_maker()` at module level also works and remains
> supported, but the `lifespan` pattern is preferred — it ties registration to the
> application lifecycle and avoids side effects at import time.

### 3. Use Dependencies in Routes

```python
from fastapi import Depends
from cacl.dependencies import get_current_user, get_current_admin

@app.get("/me")
async def get_profile(user=Depends(get_current_user)):
    return {"id": str(user.id), "email": user.email}

@app.get("/admin/users")
async def list_users(admin=Depends(get_current_admin)):
    # Only accessible to users with is_admin=True
    ...
```

### 4. Create and Verify Tokens

```python
from cacl.services.jwt_token_service import (
    create_jwt_token,
    verify_jwt_token,
    blacklist_token,
)

# Create tokens (caller must commit)
access_token = await create_jwt_token(session, user=user, token_type="access")
refresh_token = await create_jwt_token(session, user=user, token_type="refresh")
await session.commit()

# Verify token (returns user or raises HTTPException)
user = await verify_jwt_token(session, token, token_type="access")

# Blacklist token (caller must commit)
await blacklist_token(session, token)
await session.commit()
```

### 5. Set Response Tokens

```python
from fastapi.responses import JSONResponse
from cacl.utils.security import set_auth_tokens, clear_auth_tokens

# On login
response = JSONResponse(content={"detail": "Login successful"})
set_auth_tokens(response, access_token, refresh_token)
return response

# On logout
response = JSONResponse(content={"detail": "Logged out"})
clear_auth_tokens(response)
return response
```

## Token Verification Flow

When `get_current_user` or `verify_jwt_token` is called:

1. Extract token from cookie (`access_token`) or `Authorization: Bearer` header
2. Reject if token length exceeds 2048 characters (DoS protection)
3. Decode JWT and verify signature using `JWT_SECRET_KEY`
4. Reject if token is expired (`exp` claim)
5. Reject if `token_type` claim does not match expected type
6. Query `jwt_tokens` table for matching token record
7. Reject if token not found or `is_blacklisted=True`
8. Load user by `user_id` from token record
9. Reject if user not found or `is_active=False`
10. Return user object

All rejections raise `HTTPException` with status 401 (Unauthorized).

## Security Notes

### Token Uniqueness

Each token includes a `jti` (JWT ID) claim with a UUID, ensuring tokens are unique even when created in the same second.

### Blacklist Behavior

- `blacklist_token()` marks a token as invalid in the database
- `verify_jwt_token()` rejects blacklisted tokens with 401
- Blacklisting is permanent (tokens cannot be un-blacklisted)

### Refresh Token Rotation

On refresh, your application should:
1. Verify the refresh token
2. Blacklist the old refresh token
3. Create new access + refresh tokens
4. Commit the transaction

This prevents refresh token reuse attacks.

### DoS Protection

- Token length is limited to 2048 characters
- Oversized tokens are rejected before database lookup

## Database Schema

CACL requires a `jwt_tokens` table. Include this in your Alembic migrations:

```python
from cacl.models.jwt_token import JWTToken  # Import for metadata
```

The model uses:
- `id`: UUID primary key
- `user_id`: Plain UUID column with index (no foreign key — see note below)
- `token`: Unique token string
- `token_type`: "access" or "refresh"
- `is_blacklisted`: Boolean flag
- `created_at`, `expires_at`: Timestamps

### No foreign key to users

**CACL does not define a database-level foreign key from `jwt_tokens.user_id` to `users.id`.**

This is intentional — a DB-level FK would force your `User` model to share CACL's
`DeclarativeBase`, breaking the "library, not framework" promise.

**Security is preserved:** `verify_jwt_token()` still loads the current user via
`get_user_model()` and raises HTTP 401 if the user does not exist or `is_active` is `False`.

**Orphaned tokens:** if your application hard-deletes users, the `jwt_tokens` rows for
those users will not be deleted automatically. You must handle cleanup in your
application layer (e.g. `DELETE FROM jwt_tokens WHERE user_id = :uid` before deleting the
user) or run a periodic cleanup job.

### Alembic setup with two metadata objects

Because `User` and `JWTToken` live on separate `Base` classes, pass both metadata
objects to Alembic's `target_metadata` so autogenerate detects all tables:

```python
# alembic/env.py

from your_app.core.base import Base as AppBase   # your application's Base
from cacl.models.base import Base as CACLBase    # CACL's Base

# Import models so metadata is populated before autogenerate runs
from your_app.models.users import User           # noqa
from cacl.models.jwt_token import JWTToken       # noqa

target_metadata = [AppBase.metadata, CACLBase.metadata]
```

## Testing

See `docs/testing.md` in the repository for library test instructions.

For end-to-end verification of a demo app, see `docs/verification/auth_e2e.md` in the repository.

## Compatibility

- Python >= 3.11
- FastAPI
- SQLAlchemy 2.x (async)
- PostgreSQL (for UUID support)

## Demo Application

This repository includes a full FastAPI demo application
showing real-world usage of CACL with PostgreSQL, Alembic,
and JWT flows.

 https://github.com/CACL-project/CACL

## Versioning

This project follows [Semantic Versioning](https://semver.org/).
