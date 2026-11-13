import asyncio
import logging
import os
import re
from pathlib import Path as FilePath
from threading import BoundedSemaphore
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import documents
from app.catalog import Product, search_catalog
from app.extraction import MAX_UPLOAD_BYTES, DocumentError
from app.logging_config import configure_logging
from app.provider import LLMProvider, ProviderCapabilities, ProviderError, configured_provider
from app.storage import DocumentStorage, LocalStorage

logger = logging.getLogger(__name__)
RowID = Annotated[int, Path(gt=0, le=2_147_483_647)]
SKU_PATTERN = r"^[A-Z0-9][A-Z0-9._-]{0,39}$"
Title = Annotated[str, Query(min_length=1, max_length=120, pattern=r"^[^\x00]*$")]


class CatalogResponse(BaseModel):
    products: list[Product]


class ArchiveRequest(BaseModel):
    archived: bool


def create_app(
    provider: LLMProvider | None = None, storage: DocumentStorage | None = None
) -> FastAPI:
    llm = configured_provider() if provider is None else provider
    assets = storage if storage is not None else LocalStorage(
        FilePath(os.getenv("COPILOT_STORAGE_DIR", ".data/pdfs"))
    )
    uploads = BoundedSemaphore(2)
    api = FastAPI(title="Industrial B2B AI Copilot", version="0.2.0")

    @api.exception_handler(documents.DocumentConflict)
    async def conflict(_request: Request, error: documents.DocumentConflict):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @api.exception_handler(DocumentError)
    async def invalid_document(_request: Request, error: DocumentError):
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @api.exception_handler(ProviderError)
    async def unavailable_provider(_request: Request, _error: ProviderError):
        logger.warning("document_provider_unavailable")
        return JSONResponse(status_code=503, content={"detail": "Extraction provider unavailable. Retry the upload."})

    @api.exception_handler(psycopg.Error)
    @api.exception_handler(OSError)
    async def unavailable_storage(_request: Request, error: Exception):
        logger.error("persistence_unavailable", extra={"error_type": type(error).__name__})
        return JSONResponse(status_code=503, content={"detail": "Document storage temporarily unavailable."})

    @api.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/v1/provider")
    def provider_capabilities() -> ProviderCapabilities:
        return llm.capabilities()

    @api.get("/v1/catalog")
    def catalog(q: Annotated[str, Query(max_length=120, pattern=r"^[^\x00]*$")] = "") -> CatalogResponse:
        try:
            return CatalogResponse(products=search_catalog(q.strip(), llm))
        except psycopg.Error as error:
            logger.error("catalog_unavailable", extra={"error_type": type(error).__name__})
            raise HTTPException(status_code=503, detail="Catalog temporarily unavailable") from error

    @api.get("/v1/compare")
    def compare(sku: Annotated[list[str], Query(min_length=2, max_length=4)]) -> CatalogResponse:
        if len(set(sku)) != len(sku) or not all(re.fullmatch(SKU_PATTERN, item) for item in sku):
            raise HTTPException(status_code=422, detail="Select two to four different valid SKUs.")
        products = {product.sku: product for product in search_catalog("", skus=sku)}
        if len(products) != len(sku):
            raise HTTPException(status_code=404, detail="One or more product models were not found.")
        return CatalogResponse(products=[products[item] for item in sku])

    @api.get("/v1/documents")
    def document_list() -> list[documents.DocumentSummary]:
        return documents.list_documents()

    @api.post("/v1/documents", status_code=201)
    async def upload(
        request: Request,
        sku: Annotated[str, Query(pattern=SKU_PATTERN)],
        name: Title,
        title: Title,
        revision: Annotated[str, Query(min_length=1, max_length=40, pattern=r"^[^\x00]*$")],
        is_demo: bool = False,
    ) -> documents.DocumentDetail:
        name, title, revision = name.strip(), title.strip(), revision.strip()
        if not all((name, title, revision)):
            raise HTTPException(status_code=422, detail="Model name, title, and revision are required.")
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/pdf":
            raise HTTPException(status_code=415, detail="Send the original PDF as application/pdf.")
        if not uploads.acquire(blocking=False):
            raise HTTPException(status_code=429, detail="Upload slots are busy. Try again shortly.")
        try:
            data = bytearray()
            try:
                async with asyncio.timeout(15):
                    async for chunk in request.stream():
                        if len(data) + len(chunk) > MAX_UPLOAD_BYTES:
                            raise HTTPException(status_code=413, detail="PDFs must be 8 MiB or smaller.")
                        data.extend(chunk)
            except TimeoutError as error:
                raise HTTPException(status_code=408, detail="PDF upload timed out.") from error
            document_id = await run_in_threadpool(
                documents.ingest, assets, llm, bytes(data),
                sku=sku, name=name, title=title, revision=revision, is_demo=is_demo,
            )
            return await run_in_threadpool(require_document, document_id)
        finally:
            uploads.release()

    @api.get("/v1/documents/{document_id}")
    def require_document(document_id: RowID) -> documents.DocumentDetail:
        document = documents.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        return document

    @api.get("/v1/documents/{document_id}/file")
    def document_file(document_id: RowID) -> Response:
        data = documents.download(assets, document_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Document not found.")
        return Response(data, media_type="application/pdf", headers={
            "Content-Disposition": f'attachment; filename="datasheet-{document_id}.pdf"',
            "Content-Security-Policy": "sandbox",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        })

    @api.patch("/v1/documents/{document_id}", status_code=204)
    def archive_document(document_id: RowID, request: ArchiveRequest) -> Response:
        if not documents.set_archive(document_id, request.archived):
            raise HTTPException(status_code=404, detail="Document not found.")
        return Response(status_code=204)

    @api.post("/v1/assertions/{assertion_id}/review", status_code=204)
    def review_assertion(assertion_id: RowID, request: documents.ReviewRequest) -> Response:
        if not documents.review(assertion_id, request):
            raise HTTPException(status_code=404, detail="Candidate not found.")
        return Response(status_code=204)

    return api


configure_logging()
app = create_app()
