"""
Open Doc Intelligence (docintel) - Document Extractor Protocol
Abstract base interface for native and multi-modal document extraction engines.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from docintel.core.schemas import CanonicalDocument


class BaseExtractor(ABC):
    """Abstract interface implemented by document extraction adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the extractor adapter."""
        pass

    @abstractmethod
    def supports_mime(self, mime_type: str) -> bool:
        """Return True if this extractor can process the given MIME type."""
        pass

    @abstractmethod
    async def extract(
        self,
        document_id: str,
        file_path: Path | str,
        mime_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalDocument:
        """
        Extract document structure, pages, elements, bounding boxes, and markdown.
        """
        pass
