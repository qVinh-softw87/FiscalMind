from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentUser, DBSession
from app.core.exceptions import ForbiddenError, NotFoundError
from app.financial_engine.ratios import FinancialRatioCalculator
from app.models.benchmark import CustomBenchmark
from app.models.document import Document
from app.repositories.document_repository import DocumentRepository
from app.schemas.benchmarks import CustomBenchmarkCreate, DocumentBenchmarkReport

# We register under the "Financial Analysis" tags group
router = APIRouter(prefix="/analysis", tags=["Financial Analysis"])


@router.get(
    "/documents/{document_id}/benchmark",
    response_model=DocumentBenchmarkReport,
    summary="Retrieve comparison of document ratios against resolved benchmarks",
)
async def get_document_benchmarks(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> DocumentBenchmarkReport:
    """
    Retrieves the 10 core financial ratios of the document compared side-by-side
    against resolved thresholds (User, Org, Industry, or System).

    Useful for drawing Radar Charts and comparative tables on the Frontend.
    """
    repo = DocumentRepository(db)
    document = await repo.get_by_id(document_id)

    if not document:
        raise NotFoundError("Document", document_id)

    if document.user_id != current_user.id:
        raise ForbiddenError("You do not have access to this document.")

    p_data = document.parsed_data or {}
    normalized_data = p_data.get("normalized_data") or {}

    # Calculate dynamic ratios
    ratios = await FinancialRatioCalculator.calculate_ratios(
        normalized_data=normalized_data,
        db=db,
        user_id=current_user.id,
        sector=document.sector,
    )

    return DocumentBenchmarkReport(
        document_id=document.id,
        filename=document.original_filename,
        sector=document.sector,
        ratios=ratios,
    )


@router.post(
    "/benchmarks/custom",
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a custom benchmark override",
)
async def create_custom_benchmark(
    payload: CustomBenchmarkCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Configures a personalized or organizational custom threshold override.

    - If `owner_type` is "USER", the thresholds apply only to the requesting user.
    - If `owner_type` is "ORGANIZATION", they apply to the entire org (checks validation org_id).
    """
    owner_id = current_user.id
    if payload.owner_type == "ORGANIZATION":
        if not payload.org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="org_id is required when owner_type is ORGANIZATION.",
            )
        owner_id = payload.org_id

    # Check if custom benchmark already exists (if so, update it)
    query = select(CustomBenchmark).where(
        CustomBenchmark.owner_id == owner_id,
        CustomBenchmark.owner_type == payload.owner_type,
        CustomBenchmark.sector == payload.sector.lower(),
        CustomBenchmark.metric == payload.metric.lower(),
    )
    result = await db.execute(query)
    custom = result.scalar_one_or_none()

    if custom:
        # Update existing
        custom.healthy_boundary = payload.healthy_boundary
        custom.warning_boundary = payload.warning_boundary
        custom.direction = payload.direction.value
    else:
        # Create new
        custom = CustomBenchmark(
            owner_id=owner_id,
            owner_type=payload.owner_type,
            sector=payload.sector.lower(),
            metric=payload.metric.lower(),
            healthy_boundary=payload.healthy_boundary,
            warning_boundary=payload.warning_boundary,
            direction=payload.direction.value,
        )
        db.add(custom)

    await db.commit()
    return {
        "message": "Custom benchmark configured successfully.",
        "sector": payload.sector,
        "metric": payload.metric,
        "healthy_boundary": payload.healthy_boundary,
        "warning_boundary": payload.warning_boundary,
    }
