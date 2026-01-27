# Testing the CACL Library

This document describes how to run the automated test suite for the `cacl` authentication library.

## Prerequisites

- Docker and Docker Compose
- The demo application containers running (`docker compose up -d`)

## Running Tests

Tests run inside the Docker container against a dedicated test database.

### 1. Ensure containers are running

```bash
docker compose up -d
```

### 2. Create the test database (first time only)

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE cacl_test;"
```

### 3. Run the test suite

```bash
docker compose exec web python -m pytest tests/ -v
```

## Test Structure

```
tests/
├── conftest.py           # Fixtures: engine, session, test users
├── test_jwt_tokens.py    # Token creation tests
├── test_verification.py  # Token verification tests
├── test_blacklist.py     # Token blacklisting tests
├── test_dependencies.py  # FastAPI dependency tests
└── test_edge_cases.py    # Edge cases (jti, inactive users, etc.)
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

## Expected Output

```
============================= test session starts ==============================
...
======================= 36 passed in X.XXs =====================================
```

## Running Tests Without Docker (CI)

For CI environments or local testing without Docker, set the following environment variables:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cacl_test
export JWT_SECRET_KEY=test_secret_key
export CACL_USER_MODEL=tests.conftest.TestUser
```

Then run:

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
pip install asyncpg
pip install -e ./cacl
python -m pytest tests/ -v
```

PostgreSQL must be running and the `cacl_test` database must exist.

## Notes

- Tests use a separate `cacl_test` database
- Each test creates and drops tables for isolation
- The TestUser model in conftest.py satisfies UserProtocol
- PostgreSQL is required (SQLite is not supported)
