"""
Open Doc Intelligence (docintel) - Image Preprocessing & Scan Classification
Provides orientation correction, DPI normalization, contrast enhancement,
and scanned-vs-native document classification heuristics.
"""

import io
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def classify_scanned_page(
    selectable_char_count: int,
    page_width: float,
    page_height: float,
    has_raster_images: bool,
) -> tuple[bool, float]:
    """
    Heuristic rule classifying whether a document page is a scanned image or digital PDF.
    Returns (is_scanned, text_density_chars_per_sq_inch).
    """
    area_sq_inches = (page_width / 72.0) * (page_height / 72.0)
    if area_sq_inches <= 0:
        area_sq_inches = 1.0

    density = selectable_char_count / area_sq_inches

    # If selectable text is negligible (< 15 characters per page) and images exist, it's a scan
    if selectable_char_count < 15 and has_raster_images:
        return True, density

    # If density is very low (< 0.5 chars/sq in) with raster images, classify as scanned
    if density < 0.5 and has_raster_images:
        return True, density

    return False, density


def normalize_image_dpi(
    image_bytes: bytes,
    target_dpi: int = 300,
) -> bytes:
    """
    Normalize image to target DPI using PIL, ensuring sharp rendering for OCR recognition.
    """
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Check current DPI
        current_dpi = img.info.get("dpi", (72, 72))
        dpi_val = current_dpi[0] if isinstance(current_dpi, tuple) else current_dpi
        
        if dpi_val < target_dpi:
            scale_factor = target_dpi / float(dpi_val)
            new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        out_buf = io.BytesIO()
        img.save(out_buf, format="PNG", dpi=(target_dpi, target_dpi))
        return out_buf.getvalue()
    except Exception as e:
        logger.debug("DPI normalization fallback: %s", e)
        return image_bytes


def enhance_contrast_and_binarize(
    image_bytes: bytes,
) -> bytes:
    """
    Apply grayscale conversion and contrast stretching for degraded, faded, or shadowed documents.
    """
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8)
        
        # Light unsharp mask to crispen text borders
        img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=150, threshold=3))
        
        out_buf = io.BytesIO()
        img.save(out_buf, format="PNG")
        return out_buf.getvalue()
    except Exception as e:
        logger.debug("Contrast enhancement fallback: %s", e)
        return image_bytes
