"""
Open Doc Intelligence (docintel) - SQLAlchemy 2.0 ORM Models
Defines PostgreSQL/SQLite compatible relational schema for documents, processing jobs,
extracted pages, layout elements with bounding boxes, generated artifacts, model runs,
and visual evaluation metrics.
"""

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

# Use JSONB on PostgreSQL and generic JSON on SQLite
JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


def generate_uuid() -> str:
    """Generate RFC 4122 compliant UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Declarative base class for all DocIntel ORM entities."""
    pass


class DocumentModel(Base):
    """
    Ingested document root entity representing an uploaded PDF, image, or office file.
    Tracks raw file metadata, content hash, ingestion status, and page breakdown.
    """
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    pages: Mapped[list["PageModel"]] = relationship(
        "PageModel", back_populates="document", cascade="all, delete-orphan", order_by="PageModel.page_number"
    )
    jobs: Mapped[list["JobModel"]] = relationship(
        "JobModel", back_populates="document", cascade="all, delete-orphan", order_by="desc(JobModel.created_at)"
    )
    elements: Mapped[list["ElementModel"]] = relationship(
        "ElementModel", back_populates="document", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["ArtifactModel"]] = relationship(
        "ArtifactModel", back_populates="document", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["EvaluationScoreModel"]] = relationship(
        "EvaluationScoreModel", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DocumentModel(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class JobModel(Base):
    """
    Asynchronous processing job or workflow execution unit for a document.
    Tracks state transitions, error messages, retry counts, and execution progress.
    """
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(50), nullable=False, default="pipeline")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="jobs")
    model_runs: Mapped[list["ModelRunModel"]] = relationship(
        "ModelRunModel", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<JobModel(id={self.id}, doc_id={self.document_id}, status='{self.status}')>"


class PageModel(Base):
    """
    Individual document page metadata (dimensions, orientation, scan classification).
    """
    __tablename__ = "pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    width: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    height: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=72)
    orientation: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    text_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_images: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_scanned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="pages")
    elements: Mapped[list["ElementModel"]] = relationship(
        "ElementModel", back_populates="page", cascade="all, delete-orphan", order_by="ElementModel.reading_order"
    )

    __table_args__ = (
        Index("ix_pages_doc_page_number", "document_id", "page_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PageModel(id={self.id}, doc_id={self.document_id}, page={self.page_number})>"


class ElementModel(Base):
    """
    Atomic structural document element (title, paragraph, table, code, formula)
    extracted by Docling or OCR, with normalized bounding boxes and reading order.
    """
    __tablename__ = "elements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    element_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    reading_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    reading_order_hierarchical: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON_TYPE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="elements")
    page: Mapped["PageModel"] = relationship("PageModel", back_populates="elements")

    __table_args__ = (
        Index("ix_elements_page_reading_order", "page_id", "reading_order"),
    )

    def __repr__(self) -> str:
        return f"<ElementModel(id={self.id}, type='{self.element_type}', order={self.reading_order})>"


class ArtifactModel(Base):
    """
    Generated physical file artifact created during document processing
    (e.g., document.json, document.md, metadata.json, page PNGs, debug overlays).
    """
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="artifacts")

    def __repr__(self) -> str:
        return f"<ArtifactModel(id={self.id}, type='{self.artifact_type}', path='{self.file_path}')>"


class ModelRunModel(Base):
    """
    Tracks inference telemetry for VLM and OCR models
    (model name, runtime duration, peak VRAM allocated, and OOM fallbacks).
    """
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    vram_allocated_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    job: Mapped["JobModel | None"] = relationship("JobModel", back_populates="model_runs")

    def __repr__(self) -> str:
        return f"<ModelRunModel(id={self.id}, model='{self.model_name}', status='{self.status}')>"


class EvaluationScoreModel(Base):
    """
    Stores quantitative evaluation metrics (CER, WER, Field F1, Table accuracy, latency)
    associated with ground-truth comparison benchmarks.
    """
    __tablename__ = "evaluation_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    evaluator_name: Mapped[str] = mapped_column(String(100), nullable=False)
    cer: Mapped[float | None] = mapped_column(Float, nullable=True)
    wer: Mapped[float | None] = mapped_column(Float, nullable=True)
    field_f1: Mapped[float | None] = mapped_column(Float, nullable=True)
    table_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_vram_mb: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<EvaluationScoreModel(id={self.id}, dataset='{self.dataset_name}', cer={self.cer})>"
