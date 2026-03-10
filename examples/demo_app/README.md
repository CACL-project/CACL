# CACL Demo Application

This is a demonstration application showing how to use the CACL (Clear Authentication Control Library) in a FastAPI project.

## Prerequisites

- Docker and Docker Compose installed

## Quick Start

```bash
# Create .env file from sample
cp .env.sample .env

# Start containers
docker compose up -d --build

# Run migrations
docker compose exec web alembic upgrade head

# Create a test user
docker compose exec web python -m demo_app.scripts.create_user \
  --email test@example.com \
  --password testpass123
```

Visit http://localhost:8001/docs for the API documentation.

## Features Demonstrated

- JWT authentication with access and refresh tokens
- Token blacklisting and refresh rotation
- Cookie or Bearer header modes (configurable via `USE_COOKIE_AUTH`)
- Admin role protection
- PostgreSQL for token storage

## Configuration

See `.env.sample` for available configuration options.

## E2E Verification

```bash
./verify_auth_e2e.sh
```

See [docs/verification/auth_e2e.md](../../docs/verification/auth_e2e.md) for details.
