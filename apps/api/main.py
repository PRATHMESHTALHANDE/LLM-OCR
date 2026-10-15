"""
Open Doc Intelligence (docintel) - FastAPI Application
Provides asynchronous REST endpoints for document ingestion, background pipeline execution,
status polling, artifact retrieval, element extraction, and document deletion.
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config.settings import Settings, get_settings
from docintel.core.schemas import CanonicalDocument, IngestResponse, JobStatusResponse
from docintel.extractors.docling_adapter import DoclingAdapter
from docintel.extractors.text_extractor import TextExtractor
from docintel.ingestion.service import IngestionService
from docintel.ingestion.validation import IngestionValidationError
from docintel.storage.artifacts import ArtifactManager
from docintel.storage.database import (
    close_database,
    get_db_session,
    get_engine,
    session_scope,
)
from docintel.storage.models import Base
from docintel.storage.repositories import (
    ArtifactRepository,
    DocumentRepository,
    ElementRepository,
    JobRepository,
    PageRepository,
)

logger = logging.getLogger("docintel.api")


async def process_document_pipeline(document_id: str, job_id: str, ocr_engine: str = "glm_ocr") -> None:
    """
    Background worker function executing document extraction, layout parsing,
    canonical JSON/Markdown generation, and database element persistence.
    """
    logger.info("Starting background processing for document: %s (job: %s, engine: %s)", document_id, job_id, ocr_engine)
    artifact_mgr = ArtifactManager()

    async with session_scope() as session:
        doc_repo = DocumentRepository(session)
        job_repo = JobRepository(session)
        page_repo = PageRepository(session)
        elem_repo = ElementRepository(session)
        art_repo = ArtifactRepository(session)

        doc = await doc_repo.get_by_id(document_id)
        if not doc:
            logger.error("Document %s not found for processing", document_id)
            return

        await job_repo.update_job(job_id, status="running", progress_percent=15.0, current_step="extracting_content")
        await doc_repo.update_status(document_id, status="processing")

        try:
            file_path = Path(doc.storage_path)
            if not file_path.is_file():
                raise FileNotFoundError(f"Source file missing from disk: {file_path}")

            # 1. Select appropriate extractor
            docling = DoclingAdapter()
            text_ext = TextExtractor()
            extractor = docling if docling.supports_mime(doc.mime_type) else text_ext

            meta = dict(doc.metadata_ or {})
            meta["ocr_engine"] = ocr_engine

            canon_doc: CanonicalDocument = await extractor.extract(
                document_id=document_id,
                file_path=file_path,
                mime_type=doc.mime_type,
                metadata=meta,
            )

            await job_repo.update_job(job_id, progress_percent=55.0, current_step="saving_artifacts")

            # 2. Save physical artifacts atomically to disk
            json_path = artifact_mgr.save_canonical_document(canon_doc)
            md_path = artifact_mgr.save_markdown(document_id, canon_doc.markdown)
            meta_path = artifact_mgr.save_metadata(document_id, canon_doc.metadata.model_dump())

            # 3. Clean up any prior execution data to guarantee complete idempotency
            await elem_repo.delete_elements_by_document(document_id)
            await page_repo.delete_pages_by_document(document_id)
            await art_repo.delete_artifacts_by_document(document_id)

            # 4. Store pages in database
            pages_data = [
                {
                    "document_id": document_id,
                    "page_number": p.page_number,
                    "width": p.width,
                    "height": p.height,
                    "dpi": p.dpi,
                    "orientation": p.orientation,
                    "has_images": p.has_images,
                    "is_scanned": p.is_scanned,
                }
                for p in canon_doc.pages
            ]
            saved_pages = await page_repo.create_pages(pages_data)
            page_map = {p.page_number: p.id for p in saved_pages}
            default_page_id = saved_pages[0].id if saved_pages else document_id

            # 5. Store structural elements with bounding box coordinates in DB
            elements_data = [
                {
                    "document_id": document_id,
                    "page_id": page_map.get(e.page_number, default_page_id),
                    "element_type": e.element_type.value if hasattr(e.element_type, "value") else str(e.element_type),
                    "text": e.text,
                    "confidence": e.confidence or 0.98,
                    "bbox": e.bbox.to_dict() if hasattr(e.bbox, "to_dict") else dict(e.bbox),
                    "reading_order": e.reading_order,
                    "metadata": e.metadata,
                }
                for e in canon_doc.elements
            ]
            if elements_data:
                await elem_repo.bulk_create_elements(elements_data)

            # 6. Register physical artifacts in DB registry
            await art_repo.create_artifact(
                document_id=document_id,
                job_id=job_id,
                artifact_type="document_json",
                file_path=str(json_path),
                file_size_bytes=json_path.stat().st_size,
                mime_type="application/json",
            )
            await art_repo.create_artifact(
                document_id=document_id,
                job_id=job_id,
                artifact_type="document_md",
                file_path=str(md_path),
                file_size_bytes=md_path.stat().st_size,
                mime_type="text/markdown",
            )

            # 7. Finalize completion state
            page_count = max(1, len(canon_doc.pages))
            await doc_repo.update_status(document_id, status="completed", page_count=page_count)
            await job_repo.update_job(job_id, status="completed", progress_percent=100.0, current_step="done")
            logger.info("Document %s completed successfully with %d elements.", document_id, len(elements_data))

        except Exception as e:
            logger.exception("Processing pipeline failed for document %s: %s", document_id, e)
            await session.rollback()
            try:
                await doc_repo.update_status(document_id, status="failed")
                await job_repo.update_job(job_id, status="failed", error_message=str(e), current_step="error")
            except Exception:
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: initialize database tables and clean up on exit."""
    settings = get_settings()
    settings.ensure_directories()
    logger.info("Initializing DocIntel database tables...")

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("DocIntel Application started successfully on %s:%s", settings.DOCINTEL_HOST, settings.DOCINTEL_PORT)
    yield
    logger.info("Shutting down DocIntel Application...")
    await close_database()


app = FastAPI(
    title="Open Doc Intelligence (docintel) API",
    description="Local-first, open-source document parsing, OCR, layout extraction, and evaluation platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["UI"], include_in_schema=False)
async def serve_dashboard():
    """Serve the interactive Neumorphic OCR Dashboard."""
    static_file = Path(__file__).parent / "static" / "index.html"
    if static_file.is_file():
        return FileResponse(static_file)
    return JSONResponse({"status": "running", "docs": "/docs"})


@app.get("/health", tags=["System"])
@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Health check endpoint verifying application and database connectivity."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "docintel",
        "version": "0.1.0",
        "environment": settings.DOCINTEL_ENV,
        "database_type": "sqlite" if settings.is_sqlite else "postgresql",
        "advanced_ocr_enabled": settings.DOCINTEL_ADVANCED_OCR_ENABLED,
        "advanced_ocr_provider": settings.DOCINTEL_ADVANCED_OCR_PROVIDER,
    }


@app.get("/api/v1/doctor", tags=["System"])
async def run_diagnostics():
    """Run environmental checks and report hardware/runtime readiness."""
    import platform
    import shutil
    import sys

    cuda_available = False
    gpu_name = None
    vram_mb = 0

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            vram_mb = round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024))
    except ImportError:
        pass

    disk_usage = shutil.disk_usage(".")

    return {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": sys.version.split()[0],
        "cuda_available": cuda_available,
        "gpu_name": gpu_name or "N/A (CPU Only)",
        "vram_total_mb": vram_mb,
        "disk_free_gb": round(disk_usage.free / (1024**3), 1),
        "status": "ready",
    }


@app.post(
    "/api/v1/documents/upload",
    response_model=IngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Documents"],
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload (PDF, PNG, JPG, DOCX, TXT)"),
    engine: str = Query("glm_ocr", description="Target OCR engine (glm_ocr, handwriting, florence2, paddle)"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Upload and stage a document for processing.
    Validates file format, performs cryptographic deduplication, and queues processing in the background.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename in upload.")

    service = IngestionService(session=session)
    try:
        response = await service.ingest_stream(
            filename=file.filename,
            stream=file.file,
            reported_mime=file.content_type,
        )
        # Trigger immediate background processing with selected OCR engine
        background_tasks.add_task(process_document_pipeline, response.document_id, response.job_id, engine)
        return response
    except IngestionValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during document upload")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@app.post("/api/v1/documents/{document_id}/process", tags=["Documents"])
async def trigger_document_process(
    document_id: str,
    background_tasks: BackgroundTasks,
    engine: str = Query("glm_ocr", description="Target OCR engine (glm_ocr, handwriting, florence2, paddle)"),
    session: AsyncSession = Depends(get_db_session),
):
    """Manually trigger or retry OCR extraction for an existing document with the selected engine."""
    doc_repo = DocumentRepository(session)
    job_repo = JobRepository(session)

    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    latest_job = await job_repo.get_latest_for_document(document_id)
    job_id = latest_job.id if latest_job else (await job_repo.create_job(document_id)).id

    background_tasks.add_task(process_document_pipeline, document_id, job_id, engine)
    return {"status": "accepted", "message": f"Processing initiated for document {document_id} with {engine}"}


@app.get("/api/v1/documents", tags=["Documents"])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str | None = Query(None, description="Filter by status (pending, processing, completed, failed)"),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve paginated list of ingested documents."""
    repo = DocumentRepository(session)
    documents, total = await repo.list_documents(skip=skip, limit=limit, status=status)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "file_hash": doc.file_hash,
                "mime_type": doc.mime_type,
                "file_size_bytes": doc.file_size_bytes,
                "page_count": doc.page_count,
                "status": doc.status,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
            }
            for doc in documents
        ],
    }


@app.get("/api/v1/documents/{document_id}", tags=["Documents"])
async def get_document(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve document metadata, pages, and generated artifact references."""
    repo = DocumentRepository(session)
    doc = await repo.get_by_id(document_id, load_relations=True)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_hash": doc.file_hash,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "page_count": doc.page_count,
        "status": doc.status,
        "metadata": doc.metadata_,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
        "pages": [
            {
                "id": p.id,
                "page_number": p.page_number,
                "width": p.width,
                "height": p.height,
                "dpi": p.dpi,
            }
            for p in doc.pages
        ],
        "artifacts": [
            {
                "id": a.id,
                "artifact_type": a.artifact_type,
                "file_size_bytes": a.file_size_bytes,
                "mime_type": a.mime_type,
                "created_at": a.created_at,
            }
            for a in doc.artifacts
        ],
    }


@app.get("/api/v1/documents/{document_id}/elements", tags=["Documents"])
async def get_document_elements(
    document_id: str,
    page_number: int | None = Query(None, description="Optional page number filter"),
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve all extracted text elements, tables, and bounding boxes for a document with page context."""
    elem_repo = ElementRepository(session)
    elements = await elem_repo.get_elements_by_document(document_id)
    if page_number is not None:
        elements = [e for e in elements if e.page and e.page.page_number == page_number]

    return [
        {
            "id": e.id,
            "page_id": e.page_id,
            "page_number": e.page.page_number if e.page else 1,
            "page_width": e.page.width if e.page else 595.32,
            "page_height": e.page.height if e.page else 841.92,
            "element_type": e.element_type,
            "text": e.text or "",
            "confidence": e.confidence or 0.98,
            "bbox": e.bbox,
            "reading_order": e.reading_order,
        }
        for e in elements
    ]


@app.get("/api/v1/documents/{document_id}/artifacts/{artifact_type}", tags=["Documents"])
async def get_document_artifact(
    document_id: str,
    artifact_type: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Download a specific generated artifact (e.g. document_json, document_md)."""
    artifact_mgr = ArtifactManager()
    path = artifact_mgr.get_artifact_path(document_id, artifact_type)
    if not path or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Artifact '{artifact_type}' not found for document.")

    media_type = "application/json" if artifact_type == "document_json" else "text/markdown"
    return FileResponse(path=path, media_type=media_type, filename=path.name)


@app.get("/api/v1/documents/{document_id}/pages/{page_number}/image", tags=["Documents"])
async def get_document_page_image(
    document_id: str,
    page_number: int = 1,
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve rendered raster image preview for a document page."""
    artifact_mgr = ArtifactManager()
    path = artifact_mgr.get_page_image_path(document_id, page_number)
    if path and path.is_file():
        return FileResponse(path=path, media_type="image/png")

    # If raw file is an image, serve raw file
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if doc and doc.mime_type.startswith("image/"):
        raw_path = Path(doc.storage_path)
        if raw_path.is_file():
            return FileResponse(path=raw_path, media_type=doc.mime_type)

    raise HTTPException(status_code=404, detail=f"Page image {page_number} not found for document {document_id}")


@app.get("/api/v1/documents/{document_id}/file", tags=["Documents"])
async def get_document_raw_file(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Download or view the raw uploaded document file."""
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    raw_path = Path(doc.storage_path)
    if not raw_path.is_file():
        raise HTTPException(status_code=404, detail="Source file not found on disk.")
    return FileResponse(path=raw_path, media_type=doc.mime_type, filename=doc.filename)


@app.delete("/api/v1/documents/{document_id}", tags=["Documents"])
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Delete a document, cascade-deleting its relational elements, pages, jobs, and artifacts,
    and permanently purging all uploaded and extracted files from disk.
    """
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # 1. Purge physical files on disk
    artifact_mgr = ArtifactManager()
    artifact_mgr.delete_document_files(document_id)

    # 2. Delete database records
    await doc_repo.delete(document_id)
    logger.info("Deleted document %s and cleaned up disk storage.", document_id)
    return {
        "status": "success",
        "message": f"Document '{doc.filename}' ({document_id}) and all extracted files were deleted.",
    }


@app.get("/api/v1/jobs/{job_id}", response_model=JobStatusResponse, tags=["Jobs"])
async def get_job_status(
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Retrieve processing progress and status for an asynchronous job."""
    repo = JobRepository(session)
    job = await repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    duration = None
    if job.started_at and job.completed_at:
        duration = (job.completed_at - job.started_at).total_seconds()

    return JobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        error_message=job.error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
        duration_seconds=duration,
    )
