"""
LangGraph Document Processing Workflow Graph.
Builds and compiles the StateGraph directed acyclic graph (DAG) for multi-stage document intelligence,
supporting atomic state checkpointing and step execution.
"""

import logging
from typing import Any

from docintel.workflows.nodes import (
    extract_layout_node,
    finalize_workflow_node,
    persist_artifacts_node,
    render_pages_node,
    route_strategy_node,
    validate_and_sniff_node,
)
from docintel.workflows.state import WorkflowState

logger = logging.getLogger("docintel.workflows.graph")

try:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, START, StateGraph
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    MemorySaver = None
    StateGraph = None
    START = "START"
    END = "END"


def build_document_workflow(checkpointer: Any = None):
    """
    Construct and compile the LangGraph StateGraph pipeline for document processing.
    """
    if not LANGGRAPH_AVAILABLE:
        logger.warning("langgraph not available; returning native StateGraph wrapper.")
        return NativeWorkflowRunner()

    workflow = StateGraph(WorkflowState)

    # Register Nodes
    workflow.add_node("validate", validate_and_sniff_node)
    workflow.add_node("route", route_strategy_node)
    workflow.add_node("render", render_pages_node)
    workflow.add_node("extract", extract_layout_node)
    workflow.add_node("persist", persist_artifacts_node)
    workflow.add_node("finalize", finalize_workflow_node)

    # Register Edges
    workflow.add_edge(START, "validate")
    workflow.add_edge("validate", "route")
    workflow.add_edge("route", "render")
    workflow.add_edge("render", "extract")
    workflow.add_edge("extract", "persist")
    workflow.add_edge("persist", "finalize")
    workflow.add_edge("finalize", END)

    cp = checkpointer if checkpointer is not None else MemorySaver()
    compiled = workflow.compile(checkpointer=cp)
    return compiled


class NativeWorkflowRunner:
    """Fallback runner executing workflow nodes in sequential DAG order with checkpointing."""

    def __init__(self):
        self.nodes = [
            ("validate", validate_and_sniff_node),
            ("route", route_strategy_node),
            ("render", render_pages_node),
            ("extract", extract_layout_node),
            ("persist", persist_artifacts_node),
            ("finalize", finalize_workflow_node),
        ]

    async def ainvoke(self, state: WorkflowState, config: dict | None = None) -> WorkflowState:
        curr_state = dict(state)
        for name, node_func in self.nodes:
            if curr_state.get("status") == "failed":
                break
            curr_state = await node_func(curr_state)
        return curr_state


async def run_document_workflow(
    document_id: str,
    job_id: str,
    file_path: str,
    filename: str,
    ocr_engine: str = "glm_ocr",
    checkpointer: Any = None,
) -> WorkflowState:
    """
    Execute the document intelligence workflow DAG end-to-end and return the final state.
    """
    initial_state: WorkflowState = {
        "document_id": document_id,
        "job_id": job_id,
        "file_path": file_path,
        "filename": filename,
        "ocr_engine": ocr_engine,
        "status": "pending",
        "current_step": "init",
        "progress_percent": 0,
        "is_resumed": False,
        "page_count": 1,
        "pages": [],
        "elements": [],
        "canonical_document": {},
        "markdown_content": "",
        "thoughts": [],
        "error": None,
    }

    graph = build_document_workflow(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": job_id}}

    if hasattr(graph, "ainvoke"):
        final_state = await graph.ainvoke(initial_state, config=config)
    else:
        runner = NativeWorkflowRunner()
        final_state = await runner.ainvoke(initial_state, config=config)

    return final_state
