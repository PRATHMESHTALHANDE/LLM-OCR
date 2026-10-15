# Architecture Decision Records (ADRs): Open Doc Intelligence (`docintel`)

> **Master Reference**: [Agent.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Agent.md) | [Plan.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Plan.md)

---

## ADR 001: Python 3.11 with `uv` as the Primary Package Runtime

### Context
The host machine has Python 3.12, 3.14, and 3.11 available, and `uv` 0.12.5 installed. PyTorch, CUDA bindings, PaddleOCR, and Docling maintain maximal native wheel compatibility and stability on Python 3.11 for Windows.

### Decision
Use **Python 3.11** pinned via `uv` (`.python-version` set to `3.11`). Manage all dependencies via `pyproject.toml` and `uv.lock`.

### Consequences
- Maximum wheel compatibility across PyTorch, PaddleOCR, and Docling.
- Rapid dependency resolution and lockfile reproducibility via `uv`.

---

## ADR 002: PostgreSQL as Primary Database with SQLAlchemy 2.0 and Alembic Migrations

### Context
SQLite lacks concurrent write scaling and production enterprise deployment capabilities. The user specifically required a production database (PostgreSQL via Docker) with typed ORM models and automated schema migrations (alike Prisma).

### Decision
- **Primary Database**: PostgreSQL (`postgres:16-alpine`) running containerized via Docker Compose.
- **ORM**: SQLAlchemy 2.0 Async (`asyncpg` driver).
- **Migrations**: Alembic with automated migration generation (`alembic revision --autogenerate`).
- **Dev Fallback**: Maintain SQLAlchemy dialect compatibility so local isolated unit tests can run against in-memory SQLite if Docker is temporarily offline.

### Consequences
- Production-grade ACID durability, JSONB indexing for bounding box coordinates, and clean schema evolution.

---

## ADR 003: Docling as Primary Native Document Parser

### Context
The platform needs to ingest digital PDFs, Office Open XML (DOCX, PPTX, XLSX), and HTML without needlessly invoking heavy OCR models.

### Decision
Use **Docling** (IBM Research, MIT License) as the foundational parser. If a digital PDF has an intact text layer, Docling extracts its hierarchical structure natively. OCR is invoked only on scanned image pages or pages with broken text layers.

### Consequences
- Processing speed for digital documents is orders of magnitude faster than full-page OCR.
- 100% permissive MIT licensing.

---

## ADR 004: Dual-Tier OCR Architecture (PaddleOCR Baseline + Florence-2 / GOT-OCR 2.0 VLM)

### Context
The target machine has an NVIDIA GeForce RTX 3050 Laptop GPU with **4 GB VRAM**. Multi-billion parameter VLMs cause CUDA Out-of-Memory crashes on 4 GB GPUs.

### Decision
- **Baseline CPU OCR**: PaddleOCR / Docling backend. Always functions on CPU.
- **Primary Advanced VLM 1**: **Microsoft Florence-2** (`microsoft/Florence-2-base` & `large`). Requires <2.2 GB VRAM in FP16, outputs native `<OCR_WITH_REGION>` bounding boxes.
- **Primary Advanced VLM 2**: **GOT-OCR 2.0** (580M parameters). Operates in 4-bit quantization under 2.5 GB VRAM for direct Markdown/table generation.
- **Safety Fallback**: Any VRAM pressure or driver error automatically downgrades that specific page to the CPU baseline OCR.

### Consequences
- Eliminates OOM crashes while delivering state-of-the-art vision-language extraction and spatial provenance.

---

## ADR 005: LangGraph as the Unified Workflow Orchestration Engine

### Context
Document processing involves multi-stage branching: validation $\rightarrow$ format detection $\rightarrow$ native extraction vs. OCR $\rightarrow$ VLM escalation $\rightarrow$ normalization $\rightarrow$ persistence.

### Decision
Use **LangGraph** to model the execution as a directed acyclic graph (DAG) with explicit typed state (`WorkflowState`), checkpointing, step-level timeouts, and cancellation support.

### Consequences
- Resumability for interrupted jobs.
- Clear separation between workflow steps, preventing bloated monolith functions.

---

## ADR 006: Independent Evaluation Harness with Publication-Quality Seaborn Charts

### Context
Model and OCR performance must be measurable and visually transparent to developers and end users without relying on proprietary cloud evaluation platforms.

### Decision
Build an independent evaluation module using **`jiwer`** for CER/WER, exact-match/F1 for structured fields, and **Seaborn + Matplotlib** to generate 300+ DPI visual charts (boxplots, field F1 bar charts, table accuracy heatmaps, throughput vs. memory trade-off curves) embedded directly into evaluation reports and the UI dashboard.

### Consequences
- Stakeholders and users have immediate visual clarity into extraction quality across models.
