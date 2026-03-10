# Testing the CACL Library

This document describes how to run the automated test suite for the `cacl` authentication library.

## Running Tests (Docker)

The recommended way to run tests locally is via Docker Compose from the library package directory:

```bash
cd packages/cacl
docker compose -f docker-compose.test.yml run --rm test
```

This command:
1. Starts a PostgreSQL 15 container
2. Installs pinned dependencies from `requirements.txt`
3. Installs the library in editable mode
4. Runs the full test suite
5. Cleans up containers on exit

No local Python or PostgreSQL installation required.

### Cleanup

```bash
docker compose -f docker-compose.test.yml down -v
```

## Running Tests (CI)

Tests run automatically in GitHub Actions on push/PR to main when library files change:
1. PostgreSQL service container starts
2. Pinned dependencies installed via `pip install -r requirements.txt`
3. Library installed via `pip install -e . --no-deps`
4. Runs `pytest tests/`

CI uses pinned dependencies (`==` versions) for deterministic builds.
See `.github/workflows/library-tests.yml` and `packages/cacl/requirements.txt` for details.

## Test Structure

```
packages/cacl/tests/
├── conftest.py           # Fixtures: engine, session, test users
├── test_jwt_tokens.py    # Token creation tests
├── test_verification.py  # Token verification tests
├── test_blacklist.py     # Token blacklisting tests
├── test_dependencies.py  # FastAPI dependency tests
├── test_edge_cases.py    # Edge cases (jti, inactive users, etc.)
└── test_bearer_mode.py   # Bearer mode: schemas, response format
```

## Test Coverage

The test suite validates:

1. **JWT Token Creation**
   - Unique tokens with jti claims
   - Correct payload structure (sub, type, exp, iat, jti)
   - Database records created
   - No commit inside library functions

2. **JWT Token Verification**
   - Valid tokens return user
   - Expired tokens rejected
   - Blacklisted tokens rejected
   - Wrong token type rejected
   - Malformed tokens rejected
   - Tokens not in DB rejected

3. **Blacklisting**
   - Tokens marked as blacklisted
   - Blacklisted tokens fail verification
   - No commit inside library functions

4. **FastAPI Dependencies**
   - get_current_user validates tokens
   - get_current_admin checks is_admin flag

5. **Edge Cases**
   - Inactive users rejected
   - Refresh token reuse rejected
   - Multiple tokens per user
   - Token uniqueness (jti)

6. **Bearer Mode**
   - Pydantic schema validation (RefreshRequest, LogoutRequest)
   - Token response format (set_auth_tokens)
   - Cookie mode body unchanged

## Notes

- Tests use a separate `cacl_test` database
- Each test creates and drops tables for isolation
- The TestUser model in conftest.py satisfies UserProtocol
- PostgreSQL is required (SQLite is not supported)
