"""DocIntel OCR Subsystem Package."""

from docintel.ocr.base import BaseOCRProvider, OCRResult, OCRToken
from docintel.ocr.florence_adapter import Florence2Adapter
from docintel.ocr.glm_adapter import GLMOCRAdapter
from docintel.ocr.handwriting_adapter import HandwritingOCRAdapter
from docintel.ocr.paddle_adapter import PaddleOCRAdapter
from docintel.ocr.preprocessing import (
    classify_scanned_page,
    detect_handwriting_presence,
    enhance_contrast_and_binarize,
    enhance_handwritten_strokes,
    normalize_image_dpi,
)

__all__ = [
    "BaseOCRProvider",
    "OCRToken",
    "OCRResult",
    "Florence2Adapter",
    "GLMOCRAdapter",
    "HandwritingOCRAdapter",
    "PaddleOCRAdapter",
    "classify_scanned_page",
    "detect_handwriting_presence",
    "normalize_image_dpi",
    "enhance_contrast_and_binarize",
    "enhance_handwritten_strokes",
]

