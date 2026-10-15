"""
Open Doc Intelligence (docintel) - Canonical Pydantic v2 Schemas
Unified data contract for documents, bounding boxes, structural layout elements,
pages, artifacts, and processing job responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal
import uuid

from pydantic import BaseModel, ConfigDict, Field


class CoordSystem(str, Enum):
    """Coordinate system for bounding box representations."""
    PIXEL = "pixel"          # Absolute pixels (x0, y0, x1, y1) relative to page width/height
    NORM1000 = "norm1000"    # Normalized to [0, 1000] scale (standard for VLMs like Florence-2)
    UNIT = "unit"            # Normalized to [0.0, 1.0] scale


class ElementType(str, Enum):
    """Taxonomy of document layout and content elements."""
    TITLE = "title"
    SECTION_HEADER = "section_header"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_CELL = "table_cell"
    FIGURE = "figure"
    CAPTION = "caption"
    CODE = "code"
    FORMULA = "formula"
    HEADER = "header"
    FOOTER = "footer"
    FOOTNOTE = "footnote"
    KEY_VALUE = "key_value"
    UNKNOWN = "unknown"


class BoundingBox(BaseModel):
    """
    Standard bounding box model supporting pixel, unit, and norm1000 coordinates.
    Standardized to top-left origin (x0, y0) to bottom-right (x1, y1).
    """
    model_config = ConfigDict(frozen=True)

    x0: float = Field(..., description="Left coordinate")
    y0: float = Field(..., description="Top coordinate")
    x1: float = Field(..., description="Right coordinate")
    y1: float = Field(..., description="Bottom coordinate")
    coord_system: CoordSystem = Field(default=CoordSystem.PIXEL, description="Coordinate system")

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> dict[str, Any]:
        return {
            "x0": round(self.x0, 2),
            "y0": round(self.y0, 2),
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
            "width": round(self.width, 2),
            "height": round(self.height, 2),
            "coord_system": self.coord_system.value,
        }

    def to_norm1000(self, page_width: float, page_height: float) -> "BoundingBox":
        """Convert pixel coordinates to norm1000 [0..1000] system."""
        if self.coord_system == CoordSystem.NORM1000 or page_width <= 0 or page_height <= 0:
            return self
        return BoundingBox(
            x0=round((self.x0 / page_width) * 1000.0, 1),
            y0=round((self.y0 / page_height) * 1000.0, 1),
            x1=round((self.x1 / page_width) * 1000.0, 1),
            y1=round((self.y1 / page_height) * 1000.0, 1),
            coord_system=CoordSystem.NORM1000,
        )

    def to_pixel(self, page_width: float, page_height: float) -> "BoundingBox":
        """Convert norm1000 or unit coordinates to absolute pixels."""
        if self.coord_system == CoordSystem.PIXEL:
            return self
        if self.coord_system == CoordSystem.NORM1000:
            scale_x = page_width / 1000.0
            scale_y = page_height / 1000.0
        else:  # UNIT
            scale_x = page_width
            scale_y = page_height
        return BoundingBox(
            x0=round(self.x0 * scale_x, 2),
            y0=round(self.y0 * scale_y, 2),
            x1=round(self.x1 * scale_x, 2),
            y1=round(self.y1 * scale_y, 2),
            coord_system=CoordSystem.PIXEL,
        )


class PageMetadata(BaseModel):
    """Metadata describing a single page of a document."""
    page_number: int = Field(..., ge=1, description="1-based page index")
    width: float = Field(default=0.0, ge=0.0, description="Page width in points/pixels")
    height: float = Field(default=0.0, ge=0.0, description="Page height in points/pixels")
    dpi: int = Field(default=72, ge=1, description="Rasterization DPI")
    orientation: int = Field(default=0, description="Rotation degrees: 0, 90, 180, 270")
    text_density: float | None = Field(default=None, description="Chars per unit area")
    has_images: bool = Field(default=False, description="Whether page contains embedded images")
    is_scanned: bool = Field(default=False, description="Heuristic determination if page is a scan")


class DocumentElement(BaseModel):
    """
    Atomic structural document element representing text, headings, tables, or figures.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    page_number: int = Field(..., ge=1)
    element_type: ElementType = Field(default=ElementType.PARAGRAPH)
    text: str | None = Field(default=None)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    bbox: BoundingBox = Field(default_factory=lambda: BoundingBox(x0=0, y0=0, x1=0, y1=0))
    reading_order: int = Field(default=0, ge=0)
    reading_order_hierarchical: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    """High-level document metadata extracted from headers or file metadata."""
    title: str | None = None
    author: str | None = None
    creation_date: datetime | None = None
    producer: str | None = None
    page_count: int = 0
    language: str = "en"
    file_hash: str
    mime_type: str
    file_size_bytes: int
    extra: dict[str, Any] = Field(default_factory=dict)


class CanonicalDocument(BaseModel):
    """
    Root canonical document representation exported to document.json.
    Standardized interchange format for the entire DocIntel platform.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    id: str
    filename: str
    metadata: DocumentMetadata
    pages: list[PageMetadata] = Field(default_factory=list)
    elements: list[DocumentElement] = Field(default_factory=list)
    markdown: str = Field(default="", description="Clean, formatted Markdown representation")
    plain_text: str = Field(default="", description="Linear plain text extracted from reading order")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def elements_for_page(self, page_number: int) -> list[DocumentElement]:
        """Return all elements on a specific page sorted by reading order."""
        return sorted(
            [e for e in self.elements if e.page_number == page_number],
            key=lambda el: el.reading_order,
        )


class IngestResponse(BaseModel):
    """API response when a document is uploaded and accepted for processing."""
    document_id: str
    job_id: str
    filename: str
    file_hash: str
    mime_type: str
    file_size_bytes: int
    status: str = "queued"
    deduplicated: bool = False
    message: str = "Document accepted for processing"


class JobStatusResponse(BaseModel):
    """API response reporting current execution progress of a document job."""
    job_id: str
    document_id: str
    status: str
    progress_percent: float
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
