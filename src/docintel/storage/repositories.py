"""
Open Doc Intelligence (docintel) - Data Access Layer (Repositories)
Encapsulates CRUD operations, pagination, atomic updates, and relational queries
across documents, jobs, pages, elements, artifacts, and evaluations.
"""

from datetime import datetime, timezone
import logging
from typing import Any

from sqlalchemy import delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from docintel.storage.models import (
    ArtifactModel,
    DocumentModel,
    ElementModel,
    EvaluationScoreModel,
    JobModel,
    ModelRunModel,
    PageModel,
)

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository handling document lifecycle and relational retrieval."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        filename: str,
        file_hash: str,
        mime_type: str,
        file_size_bytes: int,
        storage_path: str,
        metadata: dict[str, Any] | None = None,
        page_count: int = 0,
        status: str = "pending",
        id: str | None = None,
    ) -> DocumentModel:
        """Create and persist a new DocumentModel record."""
        doc_kwargs: dict[str, Any] = {
            "filename": filename,
            "file_hash": file_hash,
            "mime_type": mime_type,
            "file_size_bytes": file_size_bytes,
            "storage_path": storage_path,
            "metadata_": metadata or {},
            "page_count": page_count,
            "status": status,
        }
        if id is not None:
            doc_kwargs["id"] = id
        doc = DocumentModel(**doc_kwargs)
        self.session.add(doc)
        await self.session.flush()
        return doc

    async def get_by_id(self, document_id: str, load_relations: bool = False) -> DocumentModel | None:
        """Retrieve a document by ID with optional eager loading of pages and artifacts."""
        stmt = select(DocumentModel).where(DocumentModel.id == document_id)
        if load_relations:
            stmt = stmt.options(
                selectinload(DocumentModel.pages),
                selectinload(DocumentModel.artifacts),
                selectinload(DocumentModel.jobs),
            )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(self, file_hash: str) -> DocumentModel | None:
        """Retrieve a document matching content SHA-256 hash for deduplication."""
        stmt = select(DocumentModel).where(DocumentModel.file_hash == file_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        document_id: str,
        status: str,
        page_count: int | None = None,
        metadata_update: dict[str, Any] | None = None,
    ) -> DocumentModel | None:
        """Update processing status and page count of a document."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        doc.status = status
        if page_count is not None:
            doc.page_count = page_count
        if metadata_update:
            current_meta = dict(doc.metadata_ or {})
            current_meta.update(metadata_update)
            doc.metadata_ = current_meta
        doc.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return doc

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[DocumentModel], int]:
        """List documents paginated with total count."""
        count_stmt = select(func.count(DocumentModel.id))
        query_stmt = select(DocumentModel).order_by(desc(DocumentModel.created_at))

        if status:
            count_stmt = count_stmt.where(DocumentModel.status == status)
            query_stmt = query_stmt.where(DocumentModel.status == status)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        docs_result = await self.session.execute(query_stmt.offset(skip).limit(limit))
        docs = list(docs_result.scalars().all())
        return docs, total

    async def delete(self, document_id: str) -> bool:
        """Delete a document and cascade delete its related entities."""
        doc = await self.get_by_id(document_id)
        if not doc:
            return False
        await self.session.delete(doc)
        await self.session.flush()
        return True


class JobRepository:
    """Repository handling asynchronous job scheduling and state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_job(
        self,
        document_id: str,
        job_type: str = "pipeline",
        status: str = "queued",
    ) -> JobModel:
        """Create and queue a new processing job."""
        job = JobModel(
            document_id=document_id,
            job_type=job_type,
            status=status,
            progress_percent=0.0,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: str) -> JobModel | None:
        """Retrieve a job by its ID."""
        stmt = select(JobModel).where(JobModel.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_document(self, document_id: str) -> JobModel | None:
        """Retrieve the most recent job for a specific document."""
        stmt = (
            select(JobModel)
            .where(JobModel.document_id == document_id)
            .order_by(desc(JobModel.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_job(
        self,
        job_id: str,
        status: str | None = None,
        progress_percent: float | None = None,
        current_step: str | None = None,
        error_message: str | None = None,
    ) -> JobModel | None:
        """Update progress, step, status, or failure message on a job."""
        job = await self.get_by_id(job_id)
        if not job:
            return None

        now = datetime.now(timezone.utc)
        if status is not None:
            job.status = status
            if status == "running" and job.started_at is None:
                job.started_at = now
            elif status in ("completed", "failed", "cancelled"):
                job.completed_at = now

        if progress_percent is not None:
            job.progress_percent = progress_percent
        if current_step is not None:
            job.current_step = current_step
        if error_message is not None:
            job.error_message = error_message

        job.updated_at = now
        await self.session.flush()
        return job

    async def list_active_jobs(self) -> list[JobModel]:
        """List all currently active or queued jobs."""
        stmt = (
            select(JobModel)
            .where(JobModel.status.in_(["queued", "running"]))
            .order_by(JobModel.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PageRepository:
    """Repository handling document page records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pages(self, pages_data: list[dict[str, Any]]) -> list[PageModel]:
        """Bulk insert page records for a document."""
        models = [PageModel(**data) for data in pages_data]
        self.session.add_all(models)
        await self.session.flush()
        return models

    async def get_pages_for_document(self, document_id: str) -> list[PageModel]:
        """Retrieve all pages for a document ordered by page number."""
        stmt = (
            select(PageModel)
            .where(PageModel.document_id == document_id)
            .order_by(PageModel.page_number)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_pages_by_document(self, document_id: str) -> int:
        """Delete all existing page records for a document."""
        stmt = delete(PageModel).where(PageModel.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount


class ElementRepository:
    """Repository handling atomic structural elements and bounding boxes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create_elements(self, elements_data: list[dict[str, Any]]) -> int:
        """Bulk insert structural elements."""
        models = [ElementModel(**data) for data in elements_data]
        self.session.add_all(models)
        await self.session.flush()
        return len(models)

    async def get_elements_by_page(self, page_id: str) -> list[ElementModel]:
        """Retrieve all elements for a specific page ordered by reading order."""
        stmt = (
            select(ElementModel)
            .where(ElementModel.page_id == page_id)
            .order_by(ElementModel.reading_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_elements_by_document(self, document_id: str) -> list[ElementModel]:
        """Retrieve all elements for an entire document eagerly loading page metadata."""
        stmt = (
            select(ElementModel)
            .where(ElementModel.document_id == document_id)
            .options(selectinload(ElementModel.page))
            .order_by(ElementModel.reading_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_elements_by_document(self, document_id: str) -> int:
        """Delete all existing elements for a document."""
        stmt = delete(ElementModel).where(ElementModel.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount


class ArtifactRepository:
    """Repository handling file artifact registries."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_artifact(
        self,
        document_id: str,
        artifact_type: str,
        file_path: str,
        mime_type: str,
        file_size_bytes: int = 0,
        checksum_sha256: str | None = None,
        job_id: str | None = None,
    ) -> ArtifactModel:
        """Register a generated artifact in the database."""
        artifact = ArtifactModel(
            document_id=document_id,
            job_id=job_id,
            artifact_type=artifact_type,
            file_path=file_path,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum_sha256=checksum_sha256,
        )
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def get_artifacts_for_document(self, document_id: str) -> list[ArtifactModel]:
        """List all generated artifacts for a document."""
        stmt = (
            select(ArtifactModel)
            .where(ArtifactModel.document_id == document_id)
            .order_by(ArtifactModel.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_artifacts_by_document(self, document_id: str) -> int:
        """Delete all existing artifact records for a document."""
        stmt = delete(ArtifactModel).where(ArtifactModel.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_artifact_by_type(self, document_id: str, artifact_type: str) -> ArtifactModel | None:
        """Retrieve a specific artifact type for a document (e.g. document_json)."""
        stmt = (
            select(ArtifactModel)
            .where(
                ArtifactModel.document_id == document_id,
                ArtifactModel.artifact_type == artifact_type,
            )
            .order_by(desc(ArtifactModel.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class EvaluationRepository:
    """Repository handling quantitative evaluation benchmarks."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_score(
        self,
        document_id: str,
        dataset_name: str,
        evaluator_name: str,
        cer: float | None = None,
        wer: float | None = None,
        field_f1: float | None = None,
        table_accuracy: float | None = None,
        latency_ms: float | None = None,
        peak_vram_mb: float | None = None,
        breakdown: dict[str, Any] | None = None,
    ) -> EvaluationScoreModel:
        """Store benchmark evaluation scores for a processed document."""
        score = EvaluationScoreModel(
            document_id=document_id,
            dataset_name=dataset_name,
            evaluator_name=evaluator_name,
            cer=cer,
            wer=wer,
            field_f1=field_f1,
            table_accuracy=table_accuracy,
            latency_ms=latency_ms,
            peak_vram_mb=peak_vram_mb,
            breakdown=breakdown or {},
        )
        self.session.add(score)
        await self.session.flush()
        return score

    async def list_scores(
        self,
        dataset_name: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EvaluationScoreModel]:
        """List evaluation scores with optional dataset filtering."""
        stmt = select(EvaluationScoreModel).order_by(desc(EvaluationScoreModel.created_at))
        if dataset_name:
            stmt = stmt.where(EvaluationScoreModel.dataset_name == dataset_name)
        result = await self.session.execute(stmt.offset(skip).limit(limit))
        return list(result.scalars().all())
