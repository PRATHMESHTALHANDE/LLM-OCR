"""
Workflow State Schema for LangGraph Document Processing Pipeline.
Stores immutable document identifiers, processing metadata, extraction results,
and telemetry thoughts across DAG transitions.
"""

from typing import Any, TypedDict


class WorkflowThought(TypedDict, total=False):
    timestamp: str
    step: str
    title: str
    detail: str
    level: str


class WorkflowState(TypedDict, total=False):
    # Core Identifiers
    document_id: str
    job_id: str
    file_path: str
    filename: str
    mime_type: str
    file_hash: str
    file_size_bytes: int

    # Engine & Execution Parameters
    ocr_engine: str
    status: str
    current_step: str
    progress_percent: int
    is_resumed: bool

    # Extraction & Layout Results
    page_count: int
    pages: list[dict[str, Any]]
    elements: list[dict[str, Any]]
    canonical_document: dict[str, Any]
    markdown_content: str

    # Agent Live Chain-of-Thought Telemetry
    thoughts: list[WorkflowThought]
    error: str | None
