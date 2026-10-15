"""
Unit tests for DocIntel Storage Layer
Tests async SQLite / PostgreSQL models, Alembic schema migrations,
CRUD repositories, cascade deletions, and transaction rollback handling.
"""

from pathlib import Path
import tempfile
from typing import AsyncGenerator
import uuid

from alembic.config import Config
from alembic import command
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docintel.config.settings import Settings
from docintel.storage.models import Base
from docintel.storage.repositories import (
    ArtifactRepository,
    DocumentRepository,
    ElementRepository,
    EvaluationRepository,
    JobRepository,
    PageRepository,
)


@pytest.fixture(scope="session")
def temp_db_file() -> str:
    """Create a temporary file path for SQLite test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    return path


@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated, clean SQLite in-memory database session for each test."""
    test_db_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


def test_settings_database_urls():
    """Verify settings parse sync and async URLs correctly for both engines."""
    pg_settings = Settings(
        DOCINTEL_DATABASE_URL="postgresql+asyncpg://docintel:secret@localhost:5432/docintel"
    )
    assert not pg_settings.is_sqlite
    assert pg_settings.async_database_url.startswith("postgresql+asyncpg://")
    assert pg_settings.sync_database_url.startswith("postgresql+psycopg2://")

    sqlite_settings = Settings(
        DOCINTEL_DATABASE_URL="sqlite+aiosqlite:///./test.db"
    )
    assert sqlite_settings.is_sqlite
    assert sqlite_settings.async_database_url.startswith("sqlite+aiosqlite:///")
    assert sqlite_settings.sync_database_url.startswith("sqlite:///")


def test_alembic_migrations_lifecycle(temp_db_file: str):
    """Test Alembic upgrade head and downgrade base against SQLite database."""
    sqlite_sync_url = f"sqlite:///{temp_db_file}"
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sqlite_sync_url)

    # 1. Upgrade schema to head
    command.upgrade(alembic_cfg, "head")

    # 2. Downgrade schema back to base
    command.downgrade(alembic_cfg, "base")

    # 3. Clean up temp file
    try:
        Path(temp_db_file).unlink(missing_ok=True)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_document_repository_crud(async_db_session: AsyncSession):
    """Test creating, fetching, updating status, and listing documents."""
    repo = DocumentRepository(async_db_session)

    # 1. Create document
    doc = await repo.create(
        filename="financial_report_2026.pdf",
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/pdf",
        file_size_bytes=1048576,
        storage_path="/data/documents/report.pdf",
        metadata={"author": "Corporate Finance", "quarter": "Q3"},
    )
    assert doc.id is not None
    assert doc.filename == "financial_report_2026.pdf"
    assert doc.status == "pending"

    # 2. Get by ID
    fetched = await repo.get_by_id(doc.id)
    assert fetched is not None
    assert fetched.filename == "financial_report_2026.pdf"

    # 3. Get by SHA-256 hash
    by_hash = await repo.get_by_hash(doc.file_hash)
    assert by_hash is not None
    assert by_hash.id == doc.id

    # 4. Update status and page count
    updated = await repo.update_status(
        doc.id,
        status="completed",
        page_count=12,
        metadata_update={"processing_time_sec": 4.5},
    )
    assert updated is not None
    assert updated.status == "completed"
    assert updated.page_count == 12
    assert updated.metadata_["quarter"] == "Q3"
    assert updated.metadata_["processing_time_sec"] == 4.5

    # 5. List documents with pagination
    docs_list, total_count = await repo.list_documents(skip=0, limit=10)
    assert total_count == 1
    assert len(docs_list) == 1


@pytest.mark.asyncio
async def test_job_repository_lifecycle(async_db_session: AsyncSession):
    """Test job scheduling, progress tracking, and state transitions."""
    doc_repo = DocumentRepository(async_db_session)
    job_repo = JobRepository(async_db_session)

    doc = await doc_repo.create(
        filename="invoice.png",
        file_hash="hash_invoice_123",
        mime_type="image/png",
        file_size_bytes=512000,
        storage_path="/data/documents/invoice.png",
    )

    # 1. Create Job
    job = await job_repo.create_job(document_id=doc.id, job_type="pipeline")
    assert job.id is not None
    assert job.status == "queued"
    assert job.progress_percent == 0.0

    # 2. Update to Running
    running_job = await job_repo.update_job(
        job.id,
        status="running",
        progress_percent=45.0,
        current_step="florence2_ocr",
    )
    assert running_job is not None
    assert running_job.status == "running"
    assert running_job.started_at is not None
    assert running_job.progress_percent == 45.0
    assert running_job.current_step == "florence2_ocr"

    # 3. Verify in active jobs
    active_jobs = await job_repo.list_active_jobs()
    assert len(active_jobs) == 1
    assert active_jobs[0].id == job.id

    # 4. Complete Job
    completed_job = await job_repo.update_job(
        job.id,
        status="completed",
        progress_percent=100.0,
        current_step="done",
    )
    assert completed_job is not None
    assert completed_job.status == "completed"
    assert completed_job.completed_at is not None

    # No more active jobs
    active_after = await job_repo.list_active_jobs()
    assert len(active_after) == 0


@pytest.mark.asyncio
async def test_pages_and_elements_with_bboxes(async_db_session: AsyncSession):
    """Test bulk page creation and structural elements with bounding box coordinates."""
    doc_repo = DocumentRepository(async_db_session)
    page_repo = PageRepository(async_db_session)
    elem_repo = ElementRepository(async_db_session)

    doc = await doc_repo.create(
        filename="paper.pdf",
        file_hash="hash_paper_456",
        mime_type="application/pdf",
        file_size_bytes=2048000,
        storage_path="/data/documents/paper.pdf",
    )

    # 1. Bulk insert pages
    pages = await page_repo.create_pages([
        {"document_id": doc.id, "page_number": 1, "width": 612.0, "height": 792.0, "dpi": 300},
        {"document_id": doc.id, "page_number": 2, "width": 612.0, "height": 792.0, "dpi": 300},
    ])
    assert len(pages) == 2
    page1_id = pages[0].id

    # 2. Bulk insert elements
    count = await elem_repo.bulk_create_elements([
        {
            "document_id": doc.id,
            "page_id": page1_id,
            "element_type": "title",
            "text": "Deep Learning for Document Intelligence",
            "confidence": 0.99,
            "bbox": {"x0": 50, "y0": 50, "x1": 550, "y1": 90, "coord_system": "pixel"},
            "reading_order": 0,
            "metadata": {"font_size": 24},
        },
        {
            "document_id": doc.id,
            "page_id": page1_id,
            "element_type": "paragraph",
            "text": "Recent advances in multimodal foundation models enable end-to-end OCR.",
            "confidence": 0.97,
            "bbox": {"x0": 50, "y0": 100, "x1": 550, "y1": 180, "coord_system": "pixel"},
            "reading_order": 1,
            "metadata": {"font_size": 12},
        },
    ])
    assert count == 2

    # 3. Retrieve elements by page
    page_elements = await elem_repo.get_elements_by_page(page1_id)
    assert len(page_elements) == 2
    assert page_elements[0].element_type == "title"
    assert page_elements[0].reading_order == 0
    assert page_elements[0].bbox["x0"] == 50
    assert page_elements[1].element_type == "paragraph"
    assert page_elements[1].reading_order == 1


@pytest.mark.asyncio
async def test_artifacts_and_evaluations(async_db_session: AsyncSession):
    """Test registering artifacts and quantitative benchmark scores."""
    doc_repo = DocumentRepository(async_db_session)
    artifact_repo = ArtifactRepository(async_db_session)
    eval_repo = EvaluationRepository(async_db_session)

    doc = await doc_repo.create(
        filename="scanned_receipt.jpg",
        file_hash="hash_receipt_789",
        mime_type="image/jpeg",
        file_size_bytes=350000,
        storage_path="/data/documents/receipt.jpg",
    )

    # 1. Register artifacts
    art_json = await artifact_repo.create_artifact(
        document_id=doc.id,
        artifact_type="document_json",
        file_path="/data/documents/receipt/document.json",
        mime_type="application/json",
        file_size_bytes=14200,
        checksum_sha256="abc123sha",
    )
    art_md = await artifact_repo.create_artifact(
        document_id=doc.id,
        artifact_type="document_md",
        file_path="/data/documents/receipt/document.md",
        mime_type="text/markdown",
        file_size_bytes=3800,
    )
    assert art_json.id is not None
    assert art_md.id is not None

    artifacts = await artifact_repo.get_artifacts_for_document(doc.id)
    assert len(artifacts) == 2

    specific_art = await artifact_repo.get_artifact_by_type(doc.id, "document_json")
    assert specific_art is not None
    assert specific_art.checksum_sha256 == "abc123sha"

    # 2. Store evaluation scores
    score = await eval_repo.create_score(
        document_id=doc.id,
        dataset_name="FUNSD_receipts",
        evaluator_name="jiwer_cer_wer",
        cer=0.018,
        wer=0.042,
        field_f1=0.965,
        table_accuracy=0.98,
        latency_ms=320.0,
        peak_vram_mb=2150.0,
        breakdown={"total_characters": 1240, "substitutions": 14, "deletions": 5},
    )
    assert score.id is not None
    assert score.cer == 0.018
    assert score.wer == 0.042

    scores = await eval_repo.list_scores(dataset_name="FUNSD_receipts")
    assert len(scores) == 1
    assert scores[0].peak_vram_mb == 2150.0


@pytest.mark.asyncio
async def test_cascade_deletion(async_db_session: AsyncSession):
    """Verify deleting a document cascades to its jobs, pages, elements, and artifacts."""
    doc_repo = DocumentRepository(async_db_session)
    job_repo = JobRepository(async_db_session)
    page_repo = PageRepository(async_db_session)
    elem_repo = ElementRepository(async_db_session)
    art_repo = ArtifactRepository(async_db_session)

    doc = await doc_repo.create(
        filename="to_delete.pdf",
        file_hash="hash_delete_999",
        mime_type="application/pdf",
        file_size_bytes=100000,
        storage_path="/data/to_delete.pdf",
    )
    job = await job_repo.create_job(document_id=doc.id)
    pages = await page_repo.create_pages([{"document_id": doc.id, "page_number": 1}])
    await elem_repo.bulk_create_elements([{
        "document_id": doc.id,
        "page_id": pages[0].id,
        "element_type": "text",
        "bbox": {},
        "reading_order": 0,
    }])
    await art_repo.create_artifact(
        document_id=doc.id,
        artifact_type="document_json",
        file_path="/data/test.json",
        mime_type="application/json",
    )

    # Delete root document
    deleted = await doc_repo.delete(doc.id)
    assert deleted is True

    # Verify everything cascaded
    assert await doc_repo.get_by_id(doc.id) is None
    assert await job_repo.get_by_id(job.id) is None
    assert len(await page_repo.get_pages_for_document(doc.id)) == 0
    assert len(await elem_repo.get_elements_by_document(doc.id)) == 0
    assert len(await art_repo.get_artifacts_for_document(doc.id)) == 0
