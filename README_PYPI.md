<p align="center">
  <img
    src="https://raw.githubusercontent.com/CACL-project/CACL/main/docs/assets/logo_pypi.png"
    alt="CACL logo"
    width="360"
  />
</p>

<h1 align="center">CACL — Clear Authentication Control Library</h1>

<p align="center">
  <strong>Stop fighting authentication in FastAPI.</strong><br/>
  Controlled JWT auth with database-backed tokens, blacklist, and rotation.
</p>

---

## What is CACL?

**CACL is a production-grade authentication library for FastAPI.**

It provides **explicit, database-backed control** over JWT authentication:

- access & refresh tokens  
- forced token invalidation (blacklist)  
- refresh token rotation  
- cookie **or** Bearer header modes — switched by a single flag  

No hidden state.  
No opinionated framework behavior.  
No surprises in production.

You own the database and transactions — **CACL handles token mechanics.**

---

## Cookie or Bearer — without the headache

CACL supports both browser and API authentication flows:

- **Cookie-based auth** for web applications
- **Bearer tokens** via `Authorization` header for APIs and services

Switching between them requires **changing a single configuration flag**.

No duplicated logic.  
No conditional dependencies in routes.  
No separate auth implementations to maintain.

---

## Why CACL exists

Most JWT libraries treat tokens as **stateless forever**.

That approach breaks down the moment you need:
- real logout
- forced session invalidation
- compromised token handling
- refresh token reuse protection

CACL treats tokens as **controlled entities** stored in your database.

This allows you to:
- revoke tokens instantly
- track token lifecycle
- enforce refresh rotation
- audit authentication behavior

This is how authentication works in real production systems.

---

## Authentication philosophy

CACL follows a simple principle:

> **Authentication must be explicit, inspectable, and revocable.**

Stateless JWTs optimize for simplicity, not for control.  
CACL optimizes for **operational clarity**.

The library intentionally:
- does **not** create database engines
- does **not** manage transactions
- does **not** hide side effects

Your application owns the session lifecycle.  
CACL integrates into it — cleanly and predictably.

---

## Core principles

- **Library, not framework** — no imposed app structure
- **Database-backed** — tokens are real records
- **Explicit ownership** — you control commits and rollbacks
- **FastAPI-native** — async, dependencies, SQLAlchemy 2.x

---

## Installation

```bash
pip install cacl
```

---

## Minimal mental model

**Your application:**
- creates DB engine
- manages transactions
- verifies user credentials

**CACL:**
- creates JWT tokens
- verifies JWT tokens
- blacklists tokens
- enforces authentication rules

---

## Documentation & demo

- **Library documentation:** [cacl/](https://github.com/CACL-project/CACL/tree/main/cacl)
- **Demo FastAPI application:** [app/](https://github.com/CACL-project/CACL/tree/main/app)
- Design notes, testing, and verification docs are included in the repository

---

## When should you use CACL?

Use CACL if you need:

- real logout (not "just delete the cookie")
- forced token invalidation
- refresh token rotation without hacks
- clear and auditable auth boundaries

If you want "just slap JWT and forget about it" — this library is intentionally not for you.
