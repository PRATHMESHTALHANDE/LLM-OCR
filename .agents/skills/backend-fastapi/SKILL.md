---
name: backend-fastapi
description: Architectural guidelines for building production-grade FastAPI applications with async SQLAlchemy 2.0 ORM, Alembic migrations, and Pydantic v2 schemas.
---

# Backend FastAPI & Storage Playbook: Open Doc Intelligence

## Core Design Principles
1. **Pydantic v2 Contract First**:
   - Every endpoint request and response must use strictly typed Pydantic v2 models.
   - Separate internal database ORM entities from public API response schemas.
2. **Decoupled Database Sessions & Heavy Inference**:
   - Never hold a database transaction open during CPU/GPU-heavy model inference.
   - Pattern: Update state -> Commit transaction -> Run async worker inference -> Open new session -> Write artifacts & update status -> Commit.
3. **Alembic Migration Discipline**:
   - Never manually execute `ALTER TABLE` or `CREATE TABLE` in production.
   - Define model changes declaratively in `src/docintel/storage/models.py`.
   - Run `alembic revision --autogenerate -m "..."` and review the generated script before applying with `alembic upgrade head`.
4. **Resilient Domain Error Handling**:
   - Map domain exceptions (`DocumentNotFoundError`, `UnsupportedFormatError`, `OOMFallbackError`) to consistent JSON error envelopes with safe public error codes.
   - Never leak internal stack traces or database connection strings to API clients.
