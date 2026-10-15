"""
Unit tests for DocIntel FastAPI Application
Tests health checks, diagnostic doctor endpoints, document uploads, and job status polling.
"""

from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.main import app
from docintel.storage.database import get_db_session
from docintel.storage.models import Base


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Isolate API tests on in-memory SQLite database via dependency override."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db_session():
        async with test_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    yield
    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_root_dashboard_ui():
    """Verify root GET / serves the Neumorphic dashboard HTML."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Open Doc Intelligence" in resp.text
        assert "Neumorphic OCR & Vision Dashboard" in resp.text


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify health check returns healthy status and service version."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "docintel"


@pytest.mark.asyncio
async def test_doctor_endpoint():
    """Verify system diagnostics endpoint returns OS, python, and CUDA details."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/doctor")
        assert resp.status_code == 200
        data = resp.json()
        assert "os" in data
        assert "python_version" in data
        assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_document_upload_and_status_flow():
    """Verify uploading a document returns 202 Accepted, and document can be queried."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload sample PDF
        pdf_bytes = b"%PDF-1.4 header\nAPI test upload document sample."
        files = {"file": ("test_upload.pdf", pdf_bytes, "application/pdf")}
        upload_resp = await client.post("/api/v1/documents/upload", files=files)
        assert upload_resp.status_code == 202
        ingest_data = upload_resp.json()
        doc_id = ingest_data["document_id"]
        job_id = ingest_data["job_id"]
        assert doc_id is not None
        assert job_id is not None

        # 2. Query document details
        doc_resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert doc_data["id"] == doc_id
        assert doc_data["filename"] == "test_upload.pdf"

        # 3. Query job status
        job_resp = await client.get(f"/api/v1/jobs/{job_id}")
        assert job_resp.status_code == 200
        job_data = job_resp.json()
        assert job_data["job_id"] == job_id
        assert job_data["document_id"] == doc_id
        assert job_data["status"] in ("queued", "running", "completed")

        # 4. List documents
        list_resp = await client.get("/api/v1/documents")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert any(item["id"] == doc_id for item in items)

        # 5. Elements retrieval
        elem_resp = await client.get(f"/api/v1/documents/{doc_id}/elements")
        assert elem_resp.status_code == 200
        assert isinstance(elem_resp.json(), list)

        # 6. Raw file download
        file_resp = await client.get(f"/api/v1/documents/{doc_id}/file")
        assert file_resp.status_code == 200
        assert file_resp.content == pdf_bytes

        # 7. Delete document permanently
        del_resp = await client.delete(f"/api/v1/documents/{doc_id}")
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["status"] == "success"

        # Verify document is gone
        check_resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert check_resp.status_code == 404
