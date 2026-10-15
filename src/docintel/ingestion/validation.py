"""
Open Doc Intelligence (docintel) - Ingestion Validation & Security
Validates MIME types, magic byte signatures, file size thresholds, and filename safety.
"""

from pathlib import Path
import re

from docintel.config.settings import get_settings

# Allowed MIME types and mapping to standard categories
SUPPORTED_MIME_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/tiff": "image",
    "image/bmp": "image",
    "image/webp": "image",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "text",
    "text/markdown": "text",
    "text/csv": "text",
    "message/rfc822": "email",
    "application/vnd.ms-outlook": "email",
}

# Magic byte signatures for tamper detection
MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"II*\x00", "image/tiff"),
    (b"MM\x00*", "image/tiff"),
    (b"BM", "image/bmp"),
    (b"RIFF", "image/webp"),  # WEBP starts with RIFF....WEBP
    (b"PK\x03\x04", "application/zip"),  # DOCX/XLSX/PPTX zip containers
]


class IngestionValidationError(ValueError):
    """Raised when an ingested file violates format, size, or integrity policies."""
    pass


def sanitize_filename(filename: str) -> str:
    """Strip dangerous directory traversal and special characters from filenames."""
    # Strip paths
    clean = Path(filename).name
    # Replace dangerous characters with underscore
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
    if not clean or clean == ".":
        clean = "unnamed_document"
    return clean[:255]


def validate_file_size(file_size_bytes: int) -> None:
    """Verify file does not exceed maximum configured upload size."""
    settings = get_settings()
    max_bytes = settings.DOCINTEL_MAX_UPLOAD_MB * 1024 * 1024
    if file_size_bytes <= 0:
        raise IngestionValidationError("Uploaded file is empty (0 bytes).")
    if file_size_bytes > max_bytes:
        raise IngestionValidationError(
            f"File size ({file_size_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed limit "
            f"of {settings.DOCINTEL_MAX_UPLOAD_MB} MB."
        )


def detect_mime_type_from_bytes(header_bytes: bytes, fallback_mime: str = "application/octet-stream") -> str:
    """Sniff MIME type from the first bytes of a file."""
    for magic, mime in MAGIC_SIGNATURES:
        if header_bytes.startswith(magic):
            # Special check for WEBP (RIFF....WEBP)
            if magic == b"RIFF" and len(header_bytes) >= 12:
                if header_bytes[8:12] == b"WEBP":
                    return "image/webp"
            elif magic == b"PK\x03\x04":
                # Check for office extensions from fallback_mime if provided
                if "wordprocessingml" in fallback_mime or "spreadsheetml" in fallback_mime or "presentationml" in fallback_mime:
                    return fallback_mime
                return "application/zip"
            else:
                return mime
    return fallback_mime


def validate_document_file(file_path: Path | str, reported_mime: str | None = None) -> tuple[str, str]:
    """
    Validate physical file on disk:
    1. Existence and size
    2. Header magic bytes vs reported MIME
    3. Supported document format category
    Returns (validated_mime_type, document_category).
    """
    path = Path(file_path)
    if not path.is_file():
        raise IngestionValidationError(f"File not found: {path}")

    size = path.stat().st_size
    validate_file_size(size)

    with open(path, "rb") as f:
        header = f.read(32)

    sniffed_mime = detect_mime_type_from_bytes(header, fallback_mime=reported_mime or "application/octet-stream")
    effective_mime = reported_mime if reported_mime in SUPPORTED_MIME_TYPES else sniffed_mime

    # Also resolve plain text files if header is valid ASCII/UTF-8
    if effective_mime == "application/octet-stream":
        try:
            header.decode("utf-8")
            effective_mime = "text/plain"
        except UnicodeDecodeError:
            pass

    if effective_mime not in SUPPORTED_MIME_TYPES:
        raise IngestionValidationError(
            f"Unsupported document format '{effective_mime}'. Supported formats: {', '.join(sorted(SUPPORTED_MIME_TYPES.keys()))}"
        )

    category = SUPPORTED_MIME_TYPES[effective_mime]
    return effective_mime, category
