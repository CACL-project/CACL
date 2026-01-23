# CACL Repository

This repository contains:

- **`cacl/`** — Reusable FastAPI authentication library ([documentation](cacl/README.md))
- **`app/`** — Demo application demonstrating library usage

## Library Documentation

See [cacl/README.md](cacl/README.md) for installation, configuration, and usage.

## Testing

- **Library tests**: See [docs/testing.md](docs/testing.md)
- **E2E verification**: See [docs/verification/auth_e2e.md](docs/verification/auth_e2e.md)

## Quick Start (Demo App)

```bash
docker compose up -d --build
docker compose exec web alembic upgrade head
```

Then visit http://localhost:8001/docs for the API documentation.
