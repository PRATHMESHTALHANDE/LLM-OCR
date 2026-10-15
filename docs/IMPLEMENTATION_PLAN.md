# Active Implementation Tracking: Open Doc Intelligence (`docintel`)

> **Master Reference**: [Agent.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Agent.md) | [Plan.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Plan.md)

---

## Active Task Matrix

### [x] Phase 0: Pre-Flight Hardware & Environment Audit
- [x] Inspect OS, CPU, RAM, GPU, VRAM, CUDA runtime, Python, Docker, Node.js, and disk space.
- [x] Verify Python 3.11 availability in `uv`.
- [x] Confirm 4 GB VRAM RTX 3050 mobile GPU; lock low-VRAM profile (Florence-2 / GOT-OCR 2.0).
- [x] Create `docs/STATUS.md`, `docs/DECISIONS.md`, and `docs/IMPLEMENTATION_PLAN.md`.

---

### [ ] Phase 1: Repository Scaffolding & Secret Hygiene
- [ ] Initialize Git repository (`git init`).
- [ ] Create strict `.gitignore` (protecting `.env`, weights, SQLite/PostgreSQL data, uploads, caches).
- [ ] Create `.env.example` with documented local defaults.
- [ ] Pin Python 3.11 via `uv` (`.python-version`).
- [ ] Initialize `pyproject.toml` with granular dependency groups.
- [ ] Scaffold folder structure (`apps/`, `src/docintel/`, `configs/`, `deploy/`, `.agents/skills/`).

---

### [ ] Phase 2: Resource Canopy & Data Catalog Architecture
- [ ] Create `RESOURCES.md` (Open-Source Resource Canopy).
- [ ] Create `docs/DATA_CATALOG.md` (Storage & Data Format Canopy).
- [ ] Create foundational `README.md` with Resource Canopy & Living Code Reference Registry.
- [ ] Implement `scripts/doctor.py` diagnostic verification script.

---

### [ ] Phase 3: Production Database Engine, ORM & Alembic Migrations
- [ ] Configure PostgreSQL service in `docker-compose.yml`.
- [ ] Implement database connection and session pooling in `src/docintel/storage/database.py`.
- [ ] Implement SQLAlchemy 2.0 ORM models in `src/docintel/storage/models.py`.
- [ ] Configure Alembic in `alembic.ini` and generate initial migration script.
- [ ] Implement `src/docintel/storage/repositories.py`.

---

### [ ] Phase 4: Core Ingestion & Native Extraction Engine
- [ ] Implement validation and hashing in `src/docintel/ingestion/`.
- [ ] Implement canonical schemas in `src/docintel/core/schemas.py`.
- [ ] Implement Docling native parser adapter in `src/docintel/extractors/docling_adapter.py`.
- [ ] Implement atomic artifact writer in `src/docintel/storage/artifacts.py`.
- [ ] Implement CLI `docintel process <file>` command.

---

### [ ] Phase 5: Baseline CPU OCR & Image Preprocessing
- [ ] Implement `OCRProvider` protocol in `src/docintel/ocr/base.py`.
- [ ] Implement image preprocessor in `src/docintel/ocr/preprocessing.py`.
- [ ] Implement PaddleOCR CPU adapter in `src/docintel/ocr/paddle_adapter.py`.
- [ ] Implement scan detection and page routing.

---

### [ ] Phase 6: Advanced Vision OCR (VLM) Subsystem
- [ ] Implement Florence-2 adapter in `src/docintel/ocr/florence_adapter.py` (<2.2 GB VRAM).
- [ ] Implement GOT-OCR 2.0 adapter in `src/docintel/ocr/got_ocr_adapter.py` (4-bit, ~2.5 GB VRAM).
- [ ] Implement ModelManager with residency locks and CPU baseline fallback.

---

### [ ] Phase 7: LangGraph Resumable Workflow Engine
- [ ] Define workflow state in `src/docintel/workflows/state.py`.
- [ ] Implement 16 DAG nodes in `src/docintel/workflows/nodes.py`.
- [ ] Implement conditional routing and checkpoint persistence.

---

### [ ] Phase 8: Local Evaluation Platform & Seaborn Visualizations
- [ ] Implement `jiwer` text metrics in `src/docintel/evaluation/metrics_text.py`.
- [ ] Implement field and table metrics.
- [ ] Implement Seaborn chart generator in `src/docintel/evaluation/charts.py`.
- [ ] Implement report generator in `src/docintel/evaluation/reports.py`.

---

### [ ] Phase 9: FastAPI Backend Service Layer
- [ ] Implement FastAPI application in `apps/api/main.py`.
- [ ] Implement endpoints under `/api/v1/` for documents, jobs, models, and evaluations.

---

### [ ] Phase 10: Accessible Neumorphic React UI
- [ ] Initialize React + Vite + TypeScript in `apps/web/`.
- [ ] Implement Neumorphic Tailwind design system.
- [ ] Build the 10 core screens (Dashboard, Upload, Queue, Viewer, Export, etc.).

---

### [ ] Phase 11: Codebase Topology, Graphify & Architecture Visualization
- [ ] Implement `scripts/visualize_codebase.py` with Graphify (`graphifyy`) integration.
- [ ] Implement document entity knowledge graph builder using NetworkX.
- [ ] Populate `.agents/skills/` playbooks.

---

### [ ] Phase 12: Unified Launch Scripts & Docker Profiles
- [ ] Implement `scripts/start.py` unified launcher.
- [ ] Create multi-stage `Dockerfile` and `docker-compose.yml` profiles (`core`, `cpu`, `gpu`, `demo`).

---

### [ ] Phase 13: Secret Audit, Documentation Finalization & GitHub Push
- [ ] Conduct automated secret audit (zero leaked keys/credentials).
- [ ] Verify `README.md` references and Resource Canopy are 100% synchronized.
- [ ] Request user review and approval before executing GitHub remote push.
