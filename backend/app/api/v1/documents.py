from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse

from app.core.dependencies import CurrentUser, DBSession
from app.models.document import DocumentStatus, DocumentType
from app.schemas.document import (
    DeleteDocumentResponse,
    DocumentListParams,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from app.services.document_service import DocumentService
from app.storage.factory import get_storage

router = APIRouter(prefix="/documents", tags=["Documents"])


def _service(db: DBSession) -> DocumentService:
    """Wires DocumentService with injected dependencies."""
    return DocumentService(db=db, storage=get_storage())


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=202,   # 202 Accepted: file received, processing async
    summary="Upload a financial document",
    responses={
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Validation error"},
    },
)
async def upload_document(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(
        ...,
        description="PDF, Excel (.xlsx/.xls), or CSV file. Max 50MB.",
    ),
) -> DocumentResponse:
    """
    Uploads a financial document for processing.

    **Accepted formats**: PDF, XLSX, XLS, CSV  
    **Max size**: 50MB  

    After upload, the document enters **async processing**:
    - OCR (if scanned PDF)
    - Financial statement parsing
    - AI embedding + indexing

    Poll `GET /documents/{id}/status` to track progress.  
    Status transitions: `pending → processing → ready | failed`
    """
    return await _service(db).upload(file=file, current_user=current_user)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
)
async def list_documents(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: DocumentStatus | None = Query(default=None, description="Filter by status"),
    document_type: DocumentType | None = Query(default=None, description="Filter by type"),
) -> DocumentListResponse:
    """
    Returns a paginated list of the authenticated user's documents.

    Supports filtering by `status` and `document_type`.
    """
    params = DocumentListParams(
        page=page,
        page_size=page_size,
        status=status,
        document_type=document_type,
    )
    return await _service(db).list_documents(current_user=current_user, params=params)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
    responses={
        404: {"description": "Document not found"},
        403: {"description": "Access denied"},
    },
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> DocumentResponse:
    """Returns full metadata for a single document."""
    return await _service(db).get_document(
        document_id=document_id,
        current_user=current_user,
    )


@router.get(
    "/{document_id}/status",
    response_model=DocumentStatusResponse,
    summary="Check document processing status",
)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> DocumentStatusResponse:
    """
    Lightweight endpoint for polling document processing status.

    Poll every 2-3 seconds until `status` is `ready` or `failed`.
    """
    return await _service(db).get_status(
        document_id=document_id,
        current_user=current_user,
    )


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    summary="Delete a document",
    responses={
        404: {"description": "Document not found"},
        403: {"description": "Access denied"},
    },
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> DeleteDocumentResponse:
    """
    Permanently removes a document.

    - File is deleted from storage
    - Record is soft-deleted in DB (audit trail preserved)
    - Associated vector embeddings will be cleaned from Qdrant (Phase 5)
    """
    return await _service(db).delete_document(
        document_id=document_id,
        current_user=current_user,
    )
