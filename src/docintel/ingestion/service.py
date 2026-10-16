"""
Open Doc Intelligence (docintel) - Ingestion Service
Orchestrates document intake, cryptographic deduplication, format validation,
atomic raw file storage, and relational job scheduling.
"""

import logging
from pathlib import Path
from typing import BinaryIO
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from docintel.core.schemas import IngestResponse
from docintel.ingestion.hashing import compute_file_hash
from docintel.ingestion.validation import (
    IngestionValidationError,
    sanitize_filename,
    validate_document_file,
)
from docintel.storage.artifacts import ArtifactManager
from docintel.storage.repositories import DocumentRepository, JobRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """Handles intake, validation, deduplication, and staging of documents."""

    def __init__(
        self,
        session: AsyncSession,
        artifact_manager: ArtifactManager | None = None,
    ) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.job_repo = JobRepository(session)
        self.artifact_mgr = artifact_manager or ArtifactManager()

    async def ingest_file(
        self,
        source_path: Path | str,
        reported_filename: str | None = None,
        reported_mime: str | None = None,
        metadata: dict | None = None,
    ) -> IngestResponse:
        """
        Ingest a document from an existing file path on disk.
        Performs hashing, format validation, deduplication, and initial job creation.
        """
        src = Path(source_path)
        if not src.is_file():
            raise IngestionValidationError(f"File not found at path: {src}")

        filename = sanitize_filename(reported_filename or src.name)
        mime_type, category = validate_document_file(src, reported_mime=reported_mime)
        file_size = src.stat().st_size
        file_hash = compute_file_hash(src)

        # 1. Deduplication check
        existing_doc = await self.doc_repo.get_by_hash(file_hash)
        if existing_doc:
            logger.info("Found existing document with identical content hash: %s", file_hash)
            latest_job = await self.job_repo.get_latest_for_document(existing_doc.id)
            job_id = latest_job.id if latest_job else str(uuid.uuid4())
            return IngestResponse(
                document_id=existing_doc.id,
                job_id=job_id,
                filename=existing_doc.filename,
                file_hash=file_hash,
                mime_type=existing_doc.mime_type,
                file_size_bytes=existing_doc.file_size_bytes,
                status=existing_doc.status,
                deduplicated=True,
                message="Identical document already ingested and processed",
            )

        # 2. Stage new document
        doc_id = str(uuid.uuid4())
        raw_target = self.artifact_mgr.save_raw_file(
            document_id=doc_id,
            filename=filename,
            content=src.read_bytes(),
        )

        doc_meta = metadata or {}
        doc_meta["category"] = category

        doc = await self.doc_repo.create(
            id=doc_id,
            filename=filename,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size_bytes=file_size,
            storage_path=str(raw_target),
            metadata=doc_meta,
            status="pending",
        )

        # 3. Schedule execution job
        job = await self.job_repo.create_job(
            document_id=doc.id,
            job_type="pipeline",
            status="queued",
        )

        await self.session.commit()

        return IngestResponse(
            document_id=doc.id,
            job_id=job.id,
            filename=doc.filename,
            file_hash=file_hash,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            deduplicated=False,
            message="Document accepted and queued for processing",
        )

    async def ingest_stream(
        self,
        filename: str,
        stream: BinaryIO,
        reported_mime: str | None = None,
        metadata: dict | None = None,
    ) -> IngestResponse:
        """
        Ingest document from an upload stream (e.g. FastAPI UploadFile).
        """
        clean_name = sanitize_filename(filename)
        doc_id = str(uuid.uuid4())

        # Save to raw artifact storage
        raw_target = self.artifact_mgr.save_raw_file(
            document_id=doc_id,
            filename=clean_name,
            content=stream,
        )

        # Validate saved file
        try:
            mime_type, category = validate_document_file(raw_target, reported_mime=reported_mime)
            file_size = raw_target.stat().st_size
            file_hash = compute_file_hash(raw_target)
        except Exception:
            # Clean up on validation failure
            self.artifact_mgr.delete_document_files(doc_id)
            raise

        # Check deduplication
        existing_doc = await self.doc_repo.get_by_hash(file_hash)
        if existing_doc:
            self.artifact_mgr.delete_document_files(doc_id)
            latest_job = await self.job_repo.get_latest_for_document(existing_doc.id)
            job_id = latest_job.id if latest_job else str(uuid.uuid4())
            return IngestResponse(
                document_id=existing_doc.id,
                job_id=job_id,
                filename=existing_doc.filename,
                file_hash=file_hash,
                mime_type=existing_doc.mime_type,
                file_size_bytes=existing_doc.file_size_bytes,
                status=existing_doc.status,
                deduplicated=True,
                message="Identical document already ingested and processed",
            )

        doc_meta = metadata or {}
        doc_meta["category"] = category

        doc = await self.doc_repo.create(
            id=doc_id,
            filename=clean_name,
            file_hash=file_hash,
            mime_type=mime_type,
            file_size_bytes=file_size,
            storage_path=str(raw_target),
            metadata=doc_meta,
            status="pending",
        )

        job = await self.job_repo.create_job(
            document_id=doc.id,
            job_type="pipeline",
            status="queued",
        )

        await self.session.commit()

        return IngestResponse(
            document_id=doc.id,
            job_id=job.id,
            filename=doc.filename,
            file_hash=file_hash,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            status=doc.status,
            deduplicated=False,
            message="Document accepted and queued for processing",
        )
