"""
Open Doc Intelligence (docintel) - OCR Provider Protocol
Standard abstract contract, token representations, and result containers for
CPU OCR engines (PaddleOCR) and Vision-Language Models (Florence-2, GOT-OCR 2.0).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docintel.core.schemas import BoundingBox, CoordSystem


@dataclass
class OCRToken:
    """Atomic recognized word or token with spatial coordinates and confidence."""
    text: str
    confidence: float
    bbox: BoundingBox
    polygon: list[list[float]] = field(default_factory=list)


@dataclass
class OCRResult:
    """Aggregated OCR output for a page or image."""
    text: str
    tokens: list[OCRToken] = field(default_factory=list)
    markdown: str = ""
    language: str = "en"
    latency_ms: float = 0.0
    vram_used_mb: float = 0.0
    model_name: str = "unknown"
    extra: dict[str, Any] = field(default_factory=dict)


class BaseOCRProvider(ABC):
    """Abstract interface implemented by all CPU OCR and VLM backends."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g., 'paddle', 'florence2', 'got_ocr')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if model weights and runtime dependencies are available."""
        pass

    @abstractmethod
    async def process_image(
        self,
        image_input: Path | bytes | Any,
        options: dict[str, Any] | None = None,
    ) -> OCRResult:
        """
        Execute OCR / VLM inference on an image.
        Returns recognized text, tokens with bounding boxes, and performance metrics.
        """
        pass
