"""
Unit tests for DocIntel Document Extractors
Tests native TextExtractor and DoclingAdapter fallback and structured parsing.
"""

from pathlib import Path

import pytest

from docintel.core.schemas import ElementType
from docintel.extractors.docling_adapter import DoclingAdapter
from docintel.extractors.text_extractor import TextExtractor


@pytest.mark.asyncio
async def test_text_extractor_markdown(tmp_path: Path):
    """Test extracting Markdown document with headers, paragraphs, and reading order."""
    extractor = TextExtractor()
    assert extractor.supports_mime("text/markdown")
    assert extractor.supports_mime("text/plain")
    assert not extractor.supports_mime("application/pdf")

    md_content = """# Executive Summary

Open Doc Intelligence is a local-first platform for OCR and layout parsing.

## Key Capabilities

It processes PDF, images, and office documents with high precision.
"""
    test_file = tmp_path / "summary.md"
    test_file.write_text(md_content, encoding="utf-8")

    doc = await extractor.extract(
        document_id="doc_test_123",
        file_path=test_file,
        mime_type="text/markdown",
    )

    assert doc.id == "doc_test_123"
    assert doc.filename == "summary.md"
    assert len(doc.pages) == 1
    assert len(doc.elements) >= 3

    # Check element types
    types = [e.element_type for e in doc.elements]
    assert ElementType.SECTION_HEADER in types
    assert ElementType.PARAGRAPH in types

    # Check reading order is strictly ascending
    orders = [e.reading_order for e in doc.elements]
    assert orders == list(range(len(orders)))

    # Check markdown preserved
    assert "Executive Summary" in doc.markdown


@pytest.mark.asyncio
async def test_docling_adapter_mime_and_fallback(tmp_path: Path):
    """Test DoclingAdapter MIME support and resilient fallback execution."""
    adapter = DoclingAdapter()
    assert adapter.supports_mime("application/pdf")
    assert adapter.supports_mime("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert adapter.supports_mime("image/png")
    assert not adapter.supports_mime("video/mp4")

    # Create dummy PDF file
    test_pdf = tmp_path / "test_report.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 header\nDummy content for fallback testing.")

    doc = await adapter.extract(
        document_id="pdf_doc_456",
        file_path=test_pdf,
        mime_type="application/pdf",
    )

    assert doc.id == "pdf_doc_456"
    assert doc.filename == "test_report.pdf"
    assert len(doc.pages) >= 1
    assert len(doc.elements) >= 1
    assert doc.markdown != ""
