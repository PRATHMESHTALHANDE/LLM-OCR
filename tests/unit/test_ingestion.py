"""
Unit tests for DocIntel Ingestion Engine & Artifact Storage
Tests file sanitization, magic byte sniffing, streaming cryptographic hashing,
deduplication pipelines, and atomic artifact file persistence.
"""

from pathlib import Path
import tempfile

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docintel.core.schemas import (
    BoundingBox,
    CanonicalDocument,
    CoordSystem,
    DocumentElement,
    DocumentMetadata,
    ElementType,
    PageMetadata,
)
from docintel.ingestion.hashing import compute_bytes_hash, compute_file_hash
from docintel.ingestion.service import IngestionService
from docintel.ingestion.validation import (
    IngestionValidationError,
    detect_mime_type_from_bytes,
    sanitize_filename,
    validate_document_file,
    validate_file_size,
)
from docintel.storage.artifacts import ArtifactManager
from docintel.storage.models import Base


@pytest_asyncio.fixture
async def async_test_session() -> AsyncSession:
    """Provide an isolated, in-memory SQLite database session for ingestion testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def temp_artifact_dir() -> Path:
    """Create a temporary directory for artifact storage testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_sanitize_filename():
    """Verify paths and hazardous characters are stripped safely."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Windows\\System32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("my report (final) & v2.pdf") == "my_report__final____v2.pdf"
    assert sanitize_filename("") == "unnamed_document"
    assert sanitize_filename(".") == "unnamed_document"


def test_validate_file_size():
    """Verify 0-byte and oversize files are rejected."""
    with pytest.raises(IngestionValidationError, match="0 bytes"):
        validate_file_size(0)

    # Valid 1 MB
    validate_file_size(1024 * 1024)

    # Over 100 MB limit
    with pytest.raises(IngestionValidationError, match="exceeds maximum"):
        validate_file_size(101 * 1024 * 1024)


def test_magic_byte_sniffing():
    """Verify format detection based on raw header bytes."""
    assert detect_mime_type_from_bytes(b"%PDF-1.7 header") == "application/pdf"
    assert detect_mime_type_from_bytes(b"\x89PNG\r\n\x1a\n\x00") == "image/png"
    assert detect_mime_type_from_bytes(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_mime_type_from_bytes(b"PK\x03\x04\x14\x00", fallback_mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document") == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_compute_file_hash(tmp_path: Path):
    """Verify streaming SHA-256 calculation."""
    test_file = tmp_path / "sample.txt"
    test_file.write_bytes(b"DocIntel High Performance Document Processing")

    h1 = compute_file_hash(test_file)
    h2 = compute_bytes_hash(b"DocIntel High Performance Document Processing")
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_ingestion_service_pipeline_and_deduplication(
    async_test_session: AsyncSession,
    temp_artifact_dir: Path,
):
    """Test full document intake, raw storage, and subsequent deduplication bypass."""
    artifact_mgr = ArtifactManager(base_data_dir=temp_artifact_dir)
    service = IngestionService(session=async_test_session, artifact_manager=artifact_mgr)

    # Create dummy PDF
    pdf_content = b"%PDF-1.5 test document content for ingestion pipeline verification."
    doc_path = temp_artifact_dir / "sample_contract.pdf"
    doc_path.write_bytes(pdf_content)

    # 1. First Ingestion
    resp1 = await service.ingest_file(
        source_path=doc_path,
        reported_filename="sample_contract.pdf",
        metadata={"client": "Acme Corp"},
    )
    assert resp1.document_id is not None
    assert resp1.job_id is not None
    assert resp1.deduplicated is False
    assert resp1.status == "pending"

    # Verify physical file stored in raw/
    raw_path = temp_artifact_dir / "documents" / resp1.document_id / "raw" / "sample_contract.pdf"
    assert raw_path.exists()
    assert raw_path.read_bytes() == pdf_content

    # 2. Second Ingestion with same content (Deduplication)
    resp2 = await service.ingest_file(
        source_path=doc_path,
        reported_filename="sample_contract_copy.pdf",
    )
    assert resp2.document_id == resp1.document_id
    assert resp2.deduplicated is True
    assert resp2.file_hash == resp1.file_hash


def test_artifact_manager_atomic_lifecycle(temp_artifact_dir: Path):
    """Test atomic serialization of canonical JSON, markdown, and page images."""
    mgr = ArtifactManager(base_data_dir=temp_artifact_dir)
    doc_id = "test_doc_001"

    # 1. Save Raw File
    raw_path = mgr.save_raw_file(doc_id, "doc.pdf", b"%PDF-1.4 raw data")
    assert raw_path.exists()

    # 2. Save Canonical Document
    canon = CanonicalDocument(
        id=doc_id,
        filename="doc.pdf",
        metadata=DocumentMetadata(
            title="Quarterly Review",
            file_hash="fake_hash",
            mime_type="application/pdf",
            file_size_bytes=1000,
            page_count=1,
        ),
        pages=[PageMetadata(page_number=1, width=800, height=1000)],
        elements=[
            DocumentElement(
                page_number=1,
                element_type=ElementType.TITLE,
                text="Financial Summary",
                bbox=BoundingBox(x0=50, y0=50, x1=500, y1=100, coord_system=CoordSystem.PIXEL),
                reading_order=0,
            )
        ],
        markdown="# Financial Summary\n\nRevenue grew by 24%.",
        plain_text="Financial Summary Revenue grew by 24%.",
    )
    json_path = mgr.save_canonical_document(canon)
    assert json_path.exists()

    # 3. Save Markdown
    md_path = mgr.save_markdown(doc_id, canon.markdown)
    assert md_path.exists()
    assert md_path.read_text(encoding="utf-8") == canon.markdown

    # 4. Save Page Image
    img_path = mgr.save_page_image(doc_id, 1, b"\x89PNG fake image")
    assert img_path.exists()

    # 5. Retrieve Artifact Paths
    assert mgr.get_artifact_path(doc_id, "document_json") == json_path
    assert mgr.get_artifact_path(doc_id, "document_md") == md_path

    # 6. Delete Document Files
    assert mgr.delete_document_files(doc_id) is True
    assert not (temp_artifact_dir / "documents" / doc_id).exists()
