"""
Open Doc Intelligence (docintel) - Native Text Extractor
Lightweight, zero-overhead parser for text/plain, text/markdown, and text/csv files.
Generates structured paragraphs, headings, and clean canonical document models.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from docintel.core.schemas import (
    BoundingBox,
    CanonicalDocument,
    CoordSystem,
    DocumentElement,
    DocumentMetadata,
    ElementType,
    PageMetadata,
)
from docintel.extractors.base import BaseExtractor
from docintel.ingestion.hashing import compute_file_hash


class TextExtractor(BaseExtractor):
    """Extractor for text-based document formats."""

    @property
    def name(self) -> str:
        return "text_extractor"

    def supports_mime(self, mime_type: str) -> bool:
        return mime_type in ("text/plain", "text/markdown", "text/csv")

    async def extract(
        self,
        document_id: str,
        file_path: Path | str,
        mime_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalDocument:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        file_size = path.stat().st_size
        file_hash = compute_file_hash(path)

        lines = content.splitlines()
        elements: list[DocumentElement] = []
        reading_order = 0

        # Heuristic parsing of paragraphs and markdown headers
        current_para: list[str] = []
        y_pos = 50.0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_para:
                    para_text = " ".join(current_para)
                    elements.append(
                        DocumentElement(
                            page_number=1,
                            element_type=ElementType.PARAGRAPH,
                            text=para_text,
                            bbox=BoundingBox(
                                x0=50.0, y0=y_pos, x1=750.0, y1=y_pos + 20.0,
                                coord_system=CoordSystem.PIXEL,
                            ),
                            reading_order=reading_order,
                        )
                    )
                    reading_order += 1
                    y_pos += 30.0
                    current_para = []
                continue

            if stripped.startswith("#"):
                if current_para:
                    elements.append(
                        DocumentElement(
                            page_number=1,
                            element_type=ElementType.PARAGRAPH,
                            text=" ".join(current_para),
                            bbox=BoundingBox(
                                x0=50.0, y0=y_pos, x1=750.0, y1=y_pos + 20.0,
                                coord_system=CoordSystem.PIXEL,
                            ),
                            reading_order=reading_order,
                        )
                    )
                    reading_order += 1
                    y_pos += 30.0
                    current_para = []

                elements.append(
                    DocumentElement(
                        page_number=1,
                        element_type=ElementType.SECTION_HEADER,
                        text=stripped.lstrip("#").strip(),
                        bbox=BoundingBox(
                            x0=50.0, y0=y_pos, x1=750.0, y1=y_pos + 25.0,
                            coord_system=CoordSystem.PIXEL,
                        ),
                        reading_order=reading_order,
                    )
                )
                reading_order += 1
                y_pos += 35.0
            else:
                current_para.append(stripped)

        if current_para:
            elements.append(
                DocumentElement(
                    page_number=1,
                    element_type=ElementType.PARAGRAPH,
                    text=" ".join(current_para),
                    bbox=BoundingBox(
                        x0=50.0, y0=y_pos, x1=750.0, y1=y_pos + 20.0,
                        coord_system=CoordSystem.PIXEL,
                    ),
                    reading_order=reading_order,
                )
            )

        page_meta = PageMetadata(
            page_number=1,
            width=800.0,
            height=max(1000.0, y_pos + 100.0),
            dpi=72,
            orientation=0,
            has_images=False,
            is_scanned=False,
        )

        doc_meta = DocumentMetadata(
            title=path.stem,
            page_count=1,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size_bytes=file_size,
            extra=metadata or {},
        )

        return CanonicalDocument(
            id=document_id,
            filename=path.name,
            metadata=doc_meta,
            pages=[page_meta],
            elements=elements,
            markdown=content,
            plain_text="\n\n".join(e.text for e in elements if e.text),
            created_at=datetime.utcnow(),
        )
