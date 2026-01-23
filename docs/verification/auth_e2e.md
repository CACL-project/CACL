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
| Refresh without token | 401 |
| Logout without token | 401 |

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
