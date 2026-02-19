# Authentication End-to-End Verification

This document describes how to run the complete authentication verification suite for the CACL demo application.

## Prerequisites

- Docker and Docker Compose installed
- Ports available:
  - `8001` for the web application
  - `5432` for PostgreSQL (internal)
- Bash shell

## Running the Verification

From the repository root:

```bash
chmod +x scripts/verify_auth_e2e.sh
./scripts/verify_auth_e2e.sh
```

The script will:
1. Stop any existing containers and clean volumes
2. Build and start fresh containers
3. Run database migrations
4. Create test users (admin + regular user)
5. Execute all authentication tests
6. Print a summary and exit with appropriate code

## Token Transport Rules

**Important:** The transport mechanism differs between Cookie mode and Bearer mode.

| Operation | Cookie Mode | Bearer Mode |
|-----------|-------------|-------------|
| Protected routes | `access_token` cookie | `Authorization: Bearer <access_token>` |
| Refresh | `refresh_token` cookie | Request body: `{"refresh_token": "..."}` |
| Logout | `refresh_token` cookie | Request body: `{"refresh_token": "..."}` |

**Key rule:** In Bearer mode, the `Authorization` header is used ONLY for access tokens.
Refresh tokens are always sent in the request body, never in headers.

## Manual Testing (Bearer Mode)

### Login

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

Response:
```json
{
  "detail": "Login successful",
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

### Protected Route

```bash
curl http://localhost:8001/me \
  -H "Authorization: Bearer <access_token>"
```

### Refresh Tokens

```bash
curl -X POST http://localhost:8001/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Logout

```bash
curl -X POST http://localhost:8001/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

## Test Coverage

### Success Flows
| Test | Expected |
|------|----------|
| Regular user login | 200 |
| GET /me with valid token | 200 |
| Admin login | 200 |
| GET /admin/users with admin token | 200 |

### Failure Flows (Security)
| Test | Expected |
|------|----------|
| Login with wrong password | 401 |
| Admin login with non-admin user | 403 |
| GET /me without token | 401 |
| GET /me with invalid token | 401 |
| GET /admin/users with regular user | 403 |
| Refresh without body | 401 |
| Refresh with empty body `{}` | 422 (Pydantic validation) |
| Refresh with access token instead of refresh | 401 |
| Logout without body | 401 |
| Logout with empty body `{}` | 422 (Pydantic validation) |

### Token Lifecycle
| Test | Expected |
|------|----------|
| Refresh token rotation | 200 |
| Refresh reuse with old token | 401 |
| Logout | 200 |
| GET /me after logout | 401 |
| Refresh after logout | 401 |

## Expected Output

A successful run will show:

```
=== SUMMARY ===

Total tests: 18
Passed:      18
Failed:      0

ALL TESTS PASSED
```

Exit code: `0` on success, `1` on any failure.

## Troubleshooting

### Container fails to start
Check if ports 8001 or 5432 are already in use:
```bash
lsof -i :8001
lsof -i :5432
```

### Database connection errors
Ensure the database container is healthy:
```bash
docker compose ps
docker compose logs db
```

### Script permission denied
```bash
chmod +x scripts/verify_auth_e2e.sh
```

### Stale code after local changes
The container runs uvicorn without `--reload`. If you modify source files locally, the running Python process won't pick up changes automatically.

**Solution:** Restart the container after code changes:
```bash
docker restart cacl_demo_web
```

Or rebuild if you've changed dependencies:
```bash
docker compose build --no-cache && docker compose up -d
```

## Changing Auth Mode (Cookie vs Bearer)

**Important:** Changing `USE_COOKIE_AUTH` in `.env` requires container RECREATE, not just restart.

Environment variables are read at container creation time. A simple `docker compose restart` or `docker restart` will NOT reload the `.env` file.

**Correct way to switch auth modes:**
```bash
# 1. Edit .env
#    USE_COOKIE_AUTH=false  (for Bearer mode)
#    USE_COOKIE_AUTH=true   (for Cookie mode)

# 2. Recreate containers (required to pick up new env vars)
docker compose down && docker compose up -d

# Or use force-recreate:
docker compose up -d --force-recreate
```

The application validates that both the demo app and the CACL library see the same `USE_COOKIE_AUTH` value at startup. If they differ (due to stale container state), the application will fail to start with a clear error message.
