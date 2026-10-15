"""DocIntel Ingestion Package."""

from docintel.ingestion.hashing import compute_bytes_hash, compute_file_hash
from docintel.ingestion.service import IngestionService
from docintel.ingestion.validation import (
    IngestionValidationError,
    detect_mime_type_from_bytes,
    sanitize_filename,
    validate_document_file,
    validate_file_size,
)

__all__ = [
    "compute_file_hash",
    "compute_bytes_hash",
    "IngestionValidationError",
    "sanitize_filename",
    "validate_file_size",
    "detect_mime_type_from_bytes",
    "validate_document_file",
    "IngestionService",
]
