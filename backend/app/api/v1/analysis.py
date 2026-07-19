from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DBSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.financial_engine.ratios import FinancialRatioCalculator
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository

router = APIRouter(prefix="/analysis", tags=["Financial Analysis"])


@router.get(
    "/documents/{document_id}/ratios",
    summary="Compute financial ratios for a document",
)
async def get_document_ratios(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Computes 10 core financial ratios from the normalized data of an uploaded statement.

    Checks document ownership (IDOR protection).
    Requires: `Authorization: Bearer <access_token>`
    """
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id)

    if not document:
        raise NotFoundError("Document", document_id)

    if document.user_id != current_user.id:
        raise ForbiddenError("You do not have access to this document.")

    # Extract parsed data from JSONB
    parsed_data = document.parsed_data or {}
    normalized_data = parsed_data.get("normalized_data") or {}

    ratios = await FinancialRatioCalculator.calculate_ratios(
        normalized_data,
        db=db,
        user_id=current_user.id,
        sector=document.sector,
    )

    return {
        "document_id": document.id,
        "filename": document.original_filename,
        "document_type": document.document_type,
        "created_at": document.created_at,
        "ratios": ratios,
        "raw_variables_used": normalized_data,
    }


@router.get(
    "/documents/{document_id}/trends",
    summary="Generate historical financial trends",
)
async def get_financial_trends(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Analyzes historical trends by comparing ratios across all uploaded versions
    of the same document name.

    Returns:
        Sorted list of yearly metrics from oldest version (v1) to latest version.
    """
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id)

    if not document:
        raise NotFoundError("Document", document_id)

    if document.user_id != current_user.id:
        raise ForbiddenError("You do not have access to this document.")

    # Find all versions of this document (matching by filename and user ownership)
    result = await db.execute(
        select(Document)
        .where(
            Document.user_id == current_user.id,
            Document.original_filename == document.original_filename,
            Document.is_deleted.is_(False),
        )
        .order_by(Document.version.asc())
    )
    all_versions = result.scalars().all()

    trends = []
    for ver in all_versions:
        p_data = ver.parsed_data or {}
        n_data = p_data.get("normalized_data") or {}
        computed_ratios = await FinancialRatioCalculator.calculate_ratios(
            n_data,
            db=db,
            user_id=current_user.id,
            sector=ver.sector,
        )
        
        trends.append({
            "version": ver.version,
            "document_id": ver.id,
            "created_at": ver.created_at,
            "ratios": computed_ratios,
        })

    return {
        "filename": document.original_filename,
        "total_versions_analyzed": len(trends),
        "history": trends,
    }
