"""DocIntel OCR Subsystem Package."""

from docintel.ocr.base import BaseOCRProvider, OCRResult, OCRToken
from docintel.ocr.florence_adapter import Florence2Adapter
from docintel.ocr.paddle_adapter import PaddleOCRAdapter
from docintel.ocr.preprocessing import (
    classify_scanned_page,
    enhance_contrast_and_binarize,
    normalize_image_dpi,
)

__all__ = [
    "BaseOCRProvider",
    "OCRToken",
    "OCRResult",
    "Florence2Adapter",
    "PaddleOCRAdapter",
    "classify_scanned_page",
    "normalize_image_dpi",
    "enhance_contrast_and_binarize",
]
