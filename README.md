<p align="center">
  <img
  src="https://raw.githubusercontent.com/CACL-project/CACL/main/docs/assets/logo.png"
  alt="CACL logo"
  width="300"
/>
</p>

# CACL - Clear Authentication Control Library

Maintainer: Anton Serebriakov

This monorepo contains:

- **`packages/cacl/`** — Reusable FastAPI authentication library ([documentation](packages/cacl/cacl/README.md))
- **`examples/demo_app/`** — Demo application demonstrating library usage (installs CACL from PyPI)

## Library Documentation

See [packages/cacl/cacl/README.md](packages/cacl/cacl/README.md) for installation, configuration, and usage.

## Testing

- **Library tests**: See [docs/testing.md](docs/testing.md)
- **E2E verification**: See [docs/verification/auth_e2e.md](docs/verification/auth_e2e.md)

## Quick Start (Demo App)

```bash
cd examples/demo_app
cp .env.sample .env
docker compose up -d --build
docker compose exec web alembic upgrade head
```

Then visit http://localhost:8001/docs for the API documentation.

## Running Library Tests

```bash
cd packages/cacl
docker compose -f docker-compose.test.yml run --rm test
```
