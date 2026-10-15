"""
Open Doc Intelligence (docintel) - File Artifact Storage Manager
Manages physical storage of uploaded source files, canonical JSON documents,
extracted markdown, page raster images, and evaluation visualization artifacts.
Enforces atomic writes via temporary files to prevent corrupt or partial reads.
"""

import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, BinaryIO

from docintel.config.settings import get_settings
from docintel.core.schemas import CanonicalDocument

logger = logging.getLogger(__name__)


def atomic_write_bytes(target_path: Path, data: bytes) -> None:
    """Write bytes atomically to target path using a temp file and rename."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + f".tmp_{os.getpid()}")
    try:
        with open(temp_path, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def atomic_write_text(target_path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically to target path using a temp file and rename."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + f".tmp_{os.getpid()}")
    try:
        with open(temp_path, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target_path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


class ArtifactManager:
    """Manages files and structured directories for processed documents."""

    def __init__(self, base_data_dir: Path | str | None = None) -> None:
        settings = get_settings()
        self.data_dir = Path(base_data_dir or settings.DOCINTEL_DATA_DIR)
        self.documents_dir = self.data_dir / "documents"
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def get_document_dir(self, document_id: str) -> Path:
        """Get or create document root storage directory."""
        doc_dir = self.documents_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def save_raw_file(self, document_id: str, filename: str, content: bytes | BinaryIO) -> Path:
        """Save original uploaded document to <doc_dir>/raw/<filename>."""
        raw_dir = self.get_document_dir(document_id) / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        target_path = raw_dir / filename

        if isinstance(content, bytes):
            atomic_write_bytes(target_path, content)
        else:
            temp_path = target_path.with_suffix(target_path.suffix + f".tmp_{os.getpid()}")
            with open(temp_path, "wb") as f_out:
                shutil.copyfileobj(content, f_out)
                f_out.flush()
                os.fsync(f_out.fileno())
            os.replace(temp_path, target_path)

        return target_path

    def save_canonical_document(self, document: CanonicalDocument) -> Path:
        """Serialize canonical document structure to <doc_dir>/document.json."""
        target_path = self.get_document_dir(document.id) / "document.json"
        json_data = document.model_dump_json(indent=2)
        atomic_write_text(target_path, json_data)
        return target_path

    def save_markdown(self, document_id: str, markdown_text: str) -> Path:
        """Save formatted Markdown representation to <doc_dir>/document.md."""
        target_path = self.get_document_dir(document_id) / "document.md"
        atomic_write_text(target_path, markdown_text)
        return target_path

    def save_metadata(self, document_id: str, metadata: dict[str, Any]) -> Path:
        """Save document metadata to <doc_dir>/metadata.json."""
        target_path = self.get_document_dir(document_id) / "metadata.json"
        json_data = json.dumps(metadata, indent=2, default=str)
        atomic_write_text(target_path, json_data)
        return target_path

    def save_page_image(self, document_id: str, page_number: int, image_bytes: bytes) -> Path:
        """Save rasterized page image to <doc_dir>/pages/page_XXX.png."""
        pages_dir = self.get_document_dir(document_id) / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        target_path = pages_dir / f"page_{page_number:03d}.png"
        atomic_write_bytes(target_path, image_bytes)
        return target_path

    def get_artifact_path(self, document_id: str, artifact_type: str) -> Path | None:
        """Resolve expected path for standard artifact types."""
        doc_dir = self.get_document_dir(document_id)
        match artifact_type:
            case "document_json":
                path = doc_dir / "document.json"
            case "document_md":
                path = doc_dir / "document.md"
            case "metadata_json":
                path = doc_dir / "metadata.json"
            case _:
                return None
        return path if path.is_file() else None

    def get_page_image_path(self, document_id: str, page_number: int = 1) -> Path | None:
        """Get path to rasterized page preview image if available."""
        doc_dir = self.get_document_dir(document_id)
        candidates = [
            doc_dir / "pages" / f"page_{page_number:03d}.png",
            doc_dir / "pages" / f"page_{page_number}.png",
        ]
        for p in candidates:
            if p.is_file():
                return p
        return None

    def delete_document_files(self, document_id: str) -> bool:
        """Cleanly remove all physical storage associated with a document."""
        doc_dir = self.documents_dir / document_id
        if doc_dir.exists():
            shutil.rmtree(doc_dir, ignore_errors=True)
            return True
        return False
