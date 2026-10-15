---
name: deployment-docker
description: Guidelines for multi-stage Docker builds, Docker Compose profiles, health checks, and container security for Open Doc Intelligence.
---

# Deployment & Docker Playbook: Open Doc Intelligence

## Core Design Principles
1. **Multi-Stage Containerization**:
   - Separate build dependencies from minimal production runtime images.
   - Run containers under an unprivileged user (`docintel:docintel`, UID 10001).
2. **Profile-Driven Compose**:
   - `core`: PostgreSQL database (`postgres:16-alpine`) with healthcheck and persistent volumes.
   - `cpu`: API + React UI + PostgreSQL + CPU OCR baseline.
   - `gpu`: GPU runtime utilizing NVIDIA Container Toolkit.
   - `vector`: Optional Qdrant container.
   - `demo`: Constrained CPU demo profile with sample documents.
3. **Volume & State Safety**:
   - Database files (`postgres_data/`) and document outputs (`data/runtime/`) must always be mounted on persistent named volumes or explicit host directories.
   - Container recreation must never result in loss of indexed documents or job history.
