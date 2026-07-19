from __future__ import annotations

import json
import uuid

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
    ValidationFailedError,
)
from app.core.logging import get_logger
from app.financial_engine.ratios import FinancialRatioCalculator
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.schemas.insight import FinancialInsightReport

logger = get_logger(__name__)


# ── AI Insight Generator System Instructions ──────────────────────────────────
INSIGHT_SYSTEM_PROMPT = """
You are a Senior CFO and Lead Financial Auditor with 15+ years of experience.
Your job is to read computed financial ratios and output a highly structured, objective, and analytical JSON report.

Requirements:
1. Act like an elite advisor. Do not write generic, high-level filler sentences. Be specific to the metrics provided.
2. Output strictly in JSON format. The JSON MUST match the following schema:
   {
     "summary": "Detailed summary paragraph analyzing the overall financial status in Vietnamese (markdown format)",
     "strengths": [{"metric": "Name in Vietnamese", "value": "Formatted value", "analysis": "Detailed explanation in Vietnamese"}],
     "weaknesses": [{"metric": "Name in Vietnamese", "value": "Formatted value", "analysis": "Detailed explanation in Vietnamese"}],
     "recommendations": [{"action": "Actionable item in Vietnamese", "priority": "HIGH|MEDIUM|LOW", "detail": "Detailed resolution steps in Vietnamese"}]
   }
3. Base your strengths and weaknesses on the actual values and their health statuses. Highlight risk vectors (e.g. Current Ratio < 1.0 represents a liquidity alert).
4. All text fields (summary, analysis, action, detail) MUST be written in Vietnamese.
"""


class InsightService:
    """
    Financial Insight Engine.
    Leverages Groq Llama 3.3 in JSON Mode to output structured financial advice reports.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = DocumentRepository(db)

        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. AI insights will fail at runtime.")
        self._groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def generate_insights(
        self,
        document_id: uuid.UUID,
        current_user: User,
    ) -> FinancialInsightReport:
        """
        Calculates ratios and requests a structured JSON insight report from Groq.
        """
        # Fetch document
        document = await self._repo.get_by_id(document_id)
        if not document:
            raise NotFoundError("Document", document_id)

        if document.user_id != current_user.id:
            raise ForbiddenError("You do not have access to this document.")

        # ── 1. Compute ratios ──
        p_data = document.parsed_data or {}
        normalized_data = p_data.get("normalized_data") or {}

        if not normalized_data:
            raise ValidationFailedError(
                "Document does not contain any normalized financial variables to analyze.",
                details={"document_id": str(document_id)},
            )

        # Run calculations
        ratios = await FinancialRatioCalculator.calculate_ratios(
            normalized_data,
            db=self._db,
            user_id=current_user.id,
            sector=document.sector,
        )

        # ── 2. Formulate Prompt ──
        prompt = f"""
Here is the raw normalized financial data:
{json.dumps(normalized_data, indent=2)}

Here are the pre-calculated financial ratios and their health classifications:
{json.dumps(ratios, indent=2)}

Generate the structured CFO financial report. Remember:
- Keep the tone professional, objective, and authoritative.
- Vietnamese is the required output language.
- Output ONLY valid JSON matching the schema.
"""

        # ── 3. Call Groq in JSON Mode ──
        logger.info("requesting_ai_insights_json_mode", document_id=str(document_id))
        try:
            response = await self._groq.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for highly analytical deterministic outputs
                response_format={"type": "json_object"},  # Force JSON Mode
            )

            raw_json = response.choices[0].message.content or "{}"
            
            # ── 4. Validate output JSON matches Pydantic Schema ──
            insight_report = FinancialInsightReport.model_validate_json(raw_json)

            logger.info("ai_insights_generation_success", document_id=str(document_id))
            return insight_report

        except Exception as e:
            logger.exception("ai_insights_generation_failed", document_id=str(document_id), error=str(e))
            raise ValidationFailedError(
                f"Failed to generate structured AI insights: {e}",
                details={"document_id": str(document_id)},
            )
