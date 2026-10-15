"""
Open Doc Intelligence (docintel) - File Hashing Utilities
Streaming cryptographic SHA-256 calculation for deduplication and integrity verification.
"""

import hashlib
from pathlib import Path


def compute_file_hash(file_path: Path | str, chunk_size: int = 65536) -> str:
    """
    Compute SHA-256 hash of a file using streaming 64KB chunks to maintain O(1) memory footprint.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found for hash calculation: {path}")

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_bytes_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw byte buffer."""
    return hashlib.sha256(data).hexdigest()
