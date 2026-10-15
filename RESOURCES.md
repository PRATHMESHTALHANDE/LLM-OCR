# Open-Source Resource Canopy: Open Doc Intelligence (`docintel`)

> **Master Reference**: [Agent.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Agent.md) | [Plan.md](file:///c:/Users/roari/Downloads/AI%20Projects/LLM%20OCR/Plan.md)  
> **Purpose**: A complete, transparent canopy cataloging every open-source model, library, engine, algorithm, and dataset used in this platform.

---

## 1. Vision & Language Models (VLMs / OCR)

| Model Name | Exact Repository / Hub ID | Parameters | License | Minimum VRAM / RAM | Primary Task & Capabilities | Official URL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Microsoft Florence-2-base** | `microsoft/Florence-2-base` | ~230M | **MIT** | < 1.0 GB VRAM / 2 GB RAM | Native `<OCR_WITH_REGION>` bounding box text extraction | [HuggingFace](https://huggingface.co/microsoft/Florence-2-base) |
| **Microsoft Florence-2-large** | `microsoft/Florence-2-large` | ~770M | **MIT** | ~2.0–2.2 GB VRAM / 4 GB RAM | High-accuracy `<OCR_WITH_REGION>` with spatial coordinates | [HuggingFace](https://huggingface.co/microsoft/Florence-2-large) |
| **GOT-OCR 2.0** | `sberbank-ai/GOT-OCR2_0` | ~580M | **Open Research Weights** | ~2.5 GB VRAM (4-bit) / 4 GB RAM | Formatted Markdown, LaTeX formulas, complex table parsing | [HuggingFace](https://huggingface.co/sberbank-ai/GOT-OCR2_0) |
| **PP-OCR v4 / PaddleOCR** | `PaddlePaddle/PaddleOCR` | Lightweight CNN+RNN | **Apache-2.0** | CPU-Only (< 1 GB RAM) | Ultra-fast baseline conventional OCR for scanned images | [GitHub](https://github.com/PaddlePaddle/PaddleOCR) |
| **GLM-OCR** *(High-Spec Alternative)* | `zai-org/GLM-OCR` | ~0.9B | **Open Weights / Apache** | ~4.5 GB VRAM (FP16) | High-capacity document layout and formula extraction | [GitHub](https://github.com/zai-org/GLM-OCR) |

---

## 2. Document Conversion & Workflow Engines

| Tool / Framework | PyPI Package / Dependency | Version Pin | License | Primary Responsibility in Platform | Official Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Docling** | `docling` | `>=2.0.0` | **MIT** | Primary hierarchical parser for digital PDF, DOCX, PPTX, XLSX, HTML | [IBM Docling](https://github.com/docling-project/docling) |
| **LangGraph** | `langgraph` | `>=0.2.0` | **MIT** | Orchestration DAG state machine, checkpointing, resumability | [LangGraph](https://github.com/langchain-ai/langgraph) |
| **PostgreSQL** | `postgres:16-alpine` | `16-alpine` | **PostgreSQL License** | Production-grade relational persistence, ACID transactions, JSONB | [PostgreSQL](https://www.postgresql.org/) |
| **SQLAlchemy** | `sqlalchemy` | `>=2.0.30` | **MIT** | Modern typed async ORM (connecting API/worker to PostgreSQL) | [SQLAlchemy](https://www.sqlalchemy.org/) |
| **Alembic** | `alembic` | `>=1.13.1` | **MIT** | Automated database schema migrations (alike Prisma Migrate) | [Alembic](https://alembic.sqlalchemy.org/) |
| **FastAPI** | `fastapi` | `>=0.111.0` | **MIT** | High-performance async REST API with automatic OpenAPI specs | [FastAPI](https://fastapi.tiangolo.com/) |
| **React + Vite** | `react`, `vite` | `18.x`, `5.x` | **MIT** | Frontend UI client with hot module replacement | [React](https://react.dev/) \| [Vite](https://vitejs.dev/) |
| **Tailwind CSS** | `tailwindcss` | `3.x` | **MIT** | Utility-first accessible Neumorphic styling system | [Tailwind](https://tailwindcss.com/) |
| **Graphify** | `graphifyy` | Latest | **MIT** | Codebase topology extraction via Tree-sitter & NetworkX | [PyPI](https://pypi.org/project/graphifyy/) |
| **NetworkX** | `networkx` | `>=3.3` | **BSD-3-Clause** | Entity-relationship knowledge graphs & graph traversal | [NetworkX](https://networkx.org/) |
| **Seaborn & Matplotlib** | `seaborn`, `matplotlib` | `>=0.13.2`, `>=3.8.4` | **BSD-3-Clause** | Publication-quality statistical evaluation charts (300+ DPI) | [Seaborn](https://seaborn.pydata.org/) |
| **jiwer** | `jiwer` | `>=3.0.4` | **Apache-2.0** | Character Error Rate (CER) and Word Error Rate (WER) metrics | [jiwer](https://github.com/jitsi/jiwer) |

---

## 3. Data & Model Weight Storage Locations

* **Model Weights Cache**: `data/models/` (excluded from Git). Downloaded on-demand at user setup or runtime; never bundled in Git repository.
* **Database State**: PostgreSQL persistent container volume `postgres_data` (excluded from Git).
* **Document Artifacts**: `data/runtime/documents/<document-id>/` (excluded from Git).
* **Evaluation Datasets**: `eval/datasets/` (public golden samples with documented permissive licenses).
