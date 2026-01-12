# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CACL (Claude Authentication Control Library) is a reusable FastAPI authentication library that provides JWT-based authentication with support for both cookie and header-based token delivery. The repository contains both the library (`cacl/`) and a demo application (`app/`) that demonstrates its usage.

## Development Commands

### Running with Docker
```bash
docker-compose up --build        # Start services (app on localhost:8001)
docker-compose down              # Stop services
```

### Running locally
```bash
pip install -r requirements.txt
pip install -e ./cacl            # Install CACL library in dev mode
uvicorn app.main:app --reload    # Run the demo app
```

### Database migrations (Alembic)
```bash
alembic upgrade head             # Apply migrations
alembic revision --autogenerate -m "message"  # Create migration
```

## Architecture

### Two-Package Structure
- **`cacl/`** - The reusable authentication library (installed as editable package)
- **`app/`** - Demo FastAPI application that integrates CACL

### CACL Library Integration Pattern
The library is designed to be database-agnostic. Host applications must:

1. Register their SQLAlchemy async session maker at startup:
   ```python
   from cacl.db import register_session_maker
   register_session_maker(async_session_maker)
   ```

2. Define `CACL_USER_MODEL` in environment (e.g., `app.models.users.User`)

3. User model must implement `UserProtocol` (see `cacl/types.py`):
   - `id: UUID`
   - `is_active: bool`
   - `is_admin: bool`

### Database & Session Rules

**Ownership:**
- `app/` owns the SQLAlchemy engine and `async_session_maker`
- `cacl/` never creates engines, sessions, or DB settings

**Registration:**
- App calls `register_session_maker(async_session_maker)` at startup
- CACL stores reference in `cacl.db.async_session_maker` (internal use only)

**Session dependency:**
- `cacl/db.py` exposes `get_db_session()` FastAPI dependency
- Dependencies (e.g., `get_current_user`) receive session via `Depends(get_db_session)`
- Rollback on exception is handled in `get_db_session()`

**Transaction rules (non-negotiable):**
- Services/utilities must NOT call `session.commit()`
- Services/utilities must NOT call `session.rollback()`
- Services/utilities must NOT create sessions internally
- Caller (endpoint or workflow) owns transaction lifecycle
- Caller explicitly commits after all operations succeed
- Caller MUST call `await session.commit()` after `create_jwt_token()` or `blacklist_token()`

### Key Components

**`cacl/dependencies.py`** - FastAPI dependencies for route protection:
- `get_current_user` - Validates token and returns user (401 if unauthorized)
- `get_current_admin` - Extends `get_current_user` with admin check (403 if not admin)

**`cacl/services/jwt_token_service.py`** - Token management:
- `create_jwt_token()` - Creates and persists JWT tokens
- `verify_jwt_token()` - Validates tokens against DB (checks blacklist/expiry)
- `blacklist_token()` - Revokes tokens

**`cacl/utils/security.py`** - Token delivery helpers:
- `set_auth_tokens()` - Sets cookies or JSON response based on `USE_COOKIE_AUTH`
- `clear_auth_tokens()` - Clears auth cookies on logout

**`cacl/models/jwt_token.py`** - JWTToken model stored in `jwt_tokens` table

### Authentication Modes
Controlled by `USE_COOKIE_AUTH` environment variable:
- `true` (default): HttpOnly cookies for access/refresh tokens
- `false`: Bearer token in Authorization header, tokens returned in JSON body

### Environment Configuration
Key settings loaded from `.env`:
- `CACL_USER_MODEL` - Dotted path to User model class
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` - JWT signing configuration
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` - Token lifetimes
- `USE_COOKIE_AUTH`, `COOKIE_*` - Cookie delivery settings
