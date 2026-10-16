"""Unit tests for Codebase Architecture & Dependency Visualizer."""

from pathlib import Path
import pytest
from scripts.visualize_codebase import (
    CodebaseGraphExtractor,
    generate_mermaid_markdown,
    generate_interactive_html,
)


def test_codebase_graph_extractor(tmp_path: Path):
    extractor = CodebaseGraphExtractor(root_dir=Path("."))
    data = extractor.scan()

    assert "stats" in data
    stats = data["stats"]
    assert stats["total_modules"] > 0
    assert stats["total_classes"] > 0
    assert stats["total_nodes"] > 0
    assert stats["total_edges"] > 0
    assert len(data["nodes"]) == stats["total_nodes"]


def test_generate_visualizer_artifacts(tmp_path: Path):
    extractor = CodebaseGraphExtractor(root_dir=Path("."))
    data = extractor.scan()

    mermaid_file = tmp_path / "architecture_graph.md"
    html_file = tmp_path / "codebase_graph.html"

    mermaid_content = generate_mermaid_markdown(data, mermaid_file)
    assert mermaid_file.exists()
    assert "```mermaid" in mermaid_content
    assert "Workflow_Engine" in mermaid_content

    html_content = generate_interactive_html(data, html_file)
    assert html_file.exists()
    assert "<!DOCTYPE html>" in html_content
    assert "graphCanvas" in html_content
