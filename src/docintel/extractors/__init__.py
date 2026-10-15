"""DocIntel Document Extractors Package."""

from docintel.extractors.base import BaseExtractor
from docintel.extractors.docling_adapter import DoclingAdapter
from docintel.extractors.text_extractor import TextExtractor

__all__ = [
    "BaseExtractor",
    "DoclingAdapter",
    "TextExtractor",
]
