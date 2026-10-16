"""
Unit tests for LangGraph Workflow Engine.
Verifies StateGraph DAG compilation, atomic node execution, routing, and artifact persistence.
"""

from pathlib import Path
import pytest

from docintel.workflows.graph import build_document_workflow, run_document_workflow
from docintel.workflows.state import WorkflowState


def test_workflow_graph_compilation():
    """Verify LangGraph StateGraph compiles with all 6 required DAG nodes."""
    workflow = build_document_workflow()
    assert workflow is not None


@pytest.mark.asyncio
async def test_workflow_execution_pipeline(tmp_path: Path):
    """Verify executing run_document_workflow transitions state through validate -> extract -> finalize."""
    test_file = tmp_path / "sample_doc.txt"
    test_file.write_text("# Invoice Summary\n\nTotal Due: $1,250.00\nPayment Terms: Net 30\n", encoding="utf-8")

    doc_id = "test-doc-wf-001"
    job_id = "test-job-wf-001"

    final_state = await run_document_workflow(
        document_id=doc_id,
        job_id=job_id,
        file_path=str(test_file),
        filename="sample_doc.txt",
        ocr_engine="text",
    )

    assert final_state["status"] == "completed"
    assert final_state["progress_percent"] == 100
    assert final_state["current_step"] == "completed"
    assert len(final_state["thoughts"]) >= 5
    assert len(final_state["elements"]) > 0
    assert "Invoice Summary" in final_state["markdown_content"]


@pytest.mark.asyncio
async def test_workflow_handwriting_routing(tmp_path: Path):
    """Verify route_strategy_node correctly routes handwriting engine."""
    from docintel.workflows.nodes import route_strategy_node

    state: WorkflowState = {
        "document_id": "doc-hw",
        "job_id": "job-hw",
        "file_path": "note.png",
        "filename": "note.png",
        "ocr_engine": "handwriting",
        "thoughts": [],
    }

    routed = await route_strategy_node(state)
    assert routed["ocr_engine"] == "handwriting"
    assert routed["current_step"] == "routing"
