---
name: frontend-development
description: Guidelines and best practices for building modern, accessible Neumorphic React applications with Vite, TypeScript, and Tailwind CSS.
---

# Frontend Development Playbook: Open Doc Intelligence

## Core Design Principles
1. **Accessible Neumorphism**:
   - Soft elevated cards with subtle dual drop shadows (`shadow-[6px_6px_12px_#d1d5db,-6px_-6px_12px_#ffffff]` in light mode; tailored dark mode equivalents).
   - Never sacrifice contrast for aesthetic. Text must strictly adhere to WCAG AA/AAA ratio (>4.5:1).
   - Interactive buttons must have distinct hover, active, and focus-visible rings (`focus-visible:ring-2 focus-visible:ring-offset-2`).
2. **State & Real-Time Tracking**:
   - Polling / Event-driven updates for document processing queue.
   - Show exact processing stage (`validating` -> `extracting` -> `ocr` -> `normalizing` -> `completed`) and page-by-page progress.
   - Never show fake 100% progress until artifacts are confirmed on disk.
3. **Split-Screen Document Viewer**:
   - Left Pane: Rendered source document/page image.
   - Right Pane: Extracted structured text, Markdown preview, and interactive tables.
   - Spatial Overlay: Highlight bounding boxes on hover of corresponding extracted text elements.
4. **Zero Placeholder Buttons**:
   - Every single button, export link, or toggle must be wired to real API endpoints.
