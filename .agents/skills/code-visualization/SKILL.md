---
name: code-visualization
description: Instructions for using Graphify, Tree-sitter, and Mermaid to extract, map, and visualize codebase architecture and dependency topology.
---

# Codebase Topology & Visualization Playbook: Open Doc Intelligence

## Core Design Principles
1. **Deterministic AST Code Mapping via Graphify**:
   - Tool: `graphifyy` (installed via `uv tool install graphifyy` or executed through `python scripts/visualize_codebase.py`).
   - Uses Tree-sitter for multi-language AST extraction (functions, classes, routes, models).
   - Uses NetworkX and the Leiden clustering algorithm to detect architectural communities and "God Nodes".
2. **Interactive Visual Exploration**:
   - Generates `graphify-out/graph.html` (interactive 2D/3D clickable network).
   - Generates `graphify-out/GRAPH_REPORT.md` breaking down modular coupling and architectural hubs.
3. **Mermaid Pipeline Diagrams**:
   - Maintain readable Mermaid DAG flowcharts in `README.md` and architecture documentation representing LangGraph state transitions.
