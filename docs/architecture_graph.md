# Open Doc Intelligence: System Architecture & Codebase Graph

> **Automated Living Architecture Specification**  
> Generated deterministically via Python AST & NetworkX AST Extraction.

---

## 1. Architectural Summary & Statistics

| Metric | Measured Value | Description |
| :--- | :--- | :--- |
| **Total Python Modules** | `38` | Modules analyzed in `src/docintel` and `apps/api` |
| **Total Classes** | `40` | Distinct classes defined |
| **Total Functions & Coroutines** | `172` | Functions, endpoints, and coroutines |
| **Total Source Lines** | `5,593` | Non-empty code lines |
| **Dependency Graph Nodes** | `93` | Modules, Classes, and Endpoints |
| **Coupling Graph Edges** | `136` | Import and inheritance relationships |

---

## 2. High-Level Modular Dependency Diagram

```mermaid
flowchart TB
    classDef api fill:#1f6feb,stroke:#58a6ff,stroke-width:2px,color:#fff;
    classDef workflow fill:#8957e5,stroke:#bc8cff,stroke-width:2px,color:#fff;
    classDef ocr fill:#238636,stroke:#3fb950,stroke-width:2px,color:#fff;
    classDef core fill:#da3633,stroke:#f85149,stroke-width:2px,color:#fff;
    classDef eval fill:#d29922,stroke:#e3b341,stroke-width:2px,color:#fff;
    classDef storage fill:#30363d,stroke:#8b949e,stroke-width:1px,color:#c9d1d9;

    subgraph Ingestion_API [REST Ingestion & API Layer]
        API_Main[apps.api.main<br/>FastAPI Server]:::api
        API_Deps[apps.api.deps<br/>Engine Router & Context]:::api
    end

    subgraph Workflow_Engine [LangGraph Orchestration & Workflows]
        WF_Graph[docintel.workflows.graph<br/>StateGraph DAG Engine]:::workflow
        WF_Nodes[docintel.workflows.nodes<br/>Pipeline Coroutines]:::workflow
        WF_State[docintel.workflows.state<br/>WorkflowState Schema]:::workflow
    end

    subgraph Parsing_OCR [Document Parsing & Multimodal OCR]
        OCR_Router[docintel.ocr.engine_router<br/>Multi-Engine Dispatcher]:::ocr
        OCR_Handwriting[docintel.ocr.handwriting_engine<br/>Adaptive Line & Word OCR]:::ocr
        OCR_GLM[docintel.ocr.glm_ocr<br/>VLM Vision Engine]:::ocr
        OCR_Florence[docintel.ocr.florence2<br/>Florence-2 Dense OCR]:::ocr
        Parse_PDF[docintel.parsing.pdf_miner<br/>pypdfium2 Rasterizer]:::ocr
    end

    subgraph Evaluation_Platform [Automated Evaluation & Benchmarking]
        Eval_Metrics[docintel.evaluation.metrics_text<br/>jiwer CER / WER & Field F1]:::eval
        Eval_Charts[docintel.evaluation.charts<br/>Seaborn Boxplots & Bar Charts]:::eval
        Eval_Reports[docintel.evaluation.reports<br/>Markdown Report Engine]:::eval
    end

    subgraph Core_Storage [Core Schemas & Storage]
        Core_Schema[docintel.core.schemas<br/>CanonicalDocument Contract]:::core
        Core_Storage_Art[docintel.storage.artifacts<br/>ArtifactManager]:::storage
        Core_DB[docintel.db.models<br/>SQLAlchemy Engine]:::storage
    end

    %% Edge Connections
    API_Main --> API_Deps
    API_Main --> WF_Graph
    API_Main --> Eval_Reports
    WF_Graph --> WF_Nodes
    WF_Graph --> WF_State
    WF_Nodes --> OCR_Router
    WF_Nodes --> Parse_PDF
    WF_Nodes --> Core_Storage_Art
    OCR_Router --> OCR_Handwriting
    OCR_Router --> OCR_GLM
    OCR_Router --> OCR_Florence
    Eval_Reports --> Eval_Metrics
    Eval_Reports --> Eval_Charts
    Eval_Reports --> Core_Storage_Art
    WF_Nodes --> Core_Schema
```

---

## 3. Subsystem Breakdown

### 3.1 LangGraph Workflow Engine (`docintel.workflows`)
- **StateGraph**: Compiles directed acyclic graphs of processing tasks (`validate`, `route`, `render`, `extract_layout`, `persist`).
- **Conditional Routing**: Dynamically inspects document page counts and user-specified engine flags to choose optimal parsing strategies.
- **Checkpoints**: Atomic state snapshots stored via `MemorySaver`.

### 3.2 Multimodal OCR & Handwriting (`docintel.ocr`)
- **Multi-Engine Dispatch**: Seamlessly branches between Florence-2, GLM-OCR, and the specialized Handwriting Engine.
- **Handwriting Segmentation**: Line-by-line bounding box isolation, contour contrast normalization, and character-level confidence assignment.

### 3.3 Evaluation Engine (`docintel.evaluation`)
- **Character & Word Error Rates**: Industry-standard `jiwer` Levenshtein distances with fallback algorithms.
- **Publication-Grade Visualizations**: 300 DPI Seaborn boxplots and field-level F1 bar charts.

### 3.4 Ingestion & Storage (`docintel.storage` & `apps.api`)
- **Canonical Schema**: Pydantic v2 `CanonicalDocument` with strict bounding-box validation.
- **Artifact Manager**: Multi-stage directory hierarchy (`documents/`, `pages/`, `artifacts/`, `markdown/`).

---

## 4. Interactive 3D / Force-Directed Explorer
Open [docs/codebase_graph.html](file:///C:\Users\roari\Downloads\AI Projects\LLM OCR\docs\codebase_graph.html) in any web browser to interactively drag, zoom, filter, and inspect the codebase topology.
