from __future__ import annotations

import json
import uuid

from groq import AsyncGroq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.logging import get_logger
from app.financial_engine.ratios import FinancialRatioCalculator
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.comparison import (
    AIComparisonEvaluation,
    CompanyMeta,
    ComparisonRequest,
    ComparisonResponse,
)

logger = get_logger(__name__)


# ── AI CFO Comparison Engine Instructions ─────────────────────────────────────
COMPARISON_SYSTEM_PROMPT = """
You are a Senior CFO, Auditor, and Expert Investment Analyst with 15+ years of experience.
Your job is to read a side-by-side financial ratio matrix comparing multiple corporate entities (or multiple years) and output a rigorous, objective comparative JSON report.

Strict Directives:
1. Compare entities directly. Do NOT write separate paragraphs summarizing A then B. You must compare them apples-to-apples in every category.
2. Calculate and state exact differences (e.g. "ROE của A cao hơn B là 7.4%"). Avoid vague terms.
3. Be objective. Base analysis strictly on the values provided.
4. Output strictly in JSON format. The JSON MUST match the following schema:
   {
     "profitability_comparison": "Direct side-by-side analysis of ROE, ROA, Net Margin in Vietnamese",
     "leverage_comparison": "Direct side-by-side analysis of Debt Ratio, Debt to Equity in Vietnamese",
     "liquidity_comparison": "Direct side-by-side analysis of Current and Quick Ratios in Vietnamese",
     "cfo_verdict": "Clear, authoritative recommendation on which entity has the healthiest financial structure and key warnings in Vietnamese"
   }
5. All text fields MUST be written in Vietnamese. Keep a formal, analytical CFO tone.
"""


class ComparisonService:
    """
    Company Comparison Engine.
    Leverages Groq Llama 3.3 in JSON Mode to output comparative audit analyses.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        
        if not settings.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY is not set. Comparison AI will fail at runtime.")
        self._groq = AsyncGroq(api_key=settings.GROQ_API_KEY)

    async def compare_companies(
        self,
        payload: ComparisonRequest,
        current_user: User,
    ) -> ComparisonResponse:
        """
        Gathers documents, calculates ratios side-by-side,
        and requests a comparative AI evaluation.
        """
        user_id = current_user.id
        doc_ids = payload.document_ids

        # ── 1. Fetch and validate all documents ──
        query = select(Document).where(
            Document.id.in_(doc_ids),
            Document.is_deleted.is_(False),
        )
        result = await self._db.execute(query)
        documents = result.scalars().all()

        # Check all documents resolved
        resolved_ids = {d.id for d in documents}
        for doc_id in doc_ids:
            if doc_id not in resolved_ids:
                raise NotFoundError("Document", doc_id)

        # Check ownership and state
        compared_entities = []
        company_ratios = {}
        
        for doc in documents:
            if doc.user_id != user_id:
                raise ForbiddenError(f"You do not have access to document: {doc.original_filename}")
            
            if doc.status != DocumentStatus.READY:
                raise ValidationFailedError(
                    f"Document {doc.original_filename} is not processed yet.",
                    details={"document_id": str(doc.id), "status": doc.status},
                )

            # Determine year from metadata or parsed data
            p_data = doc.parsed_data or {}
            normalized_data = p_data.get("normalized_data") or {}
            year = normalized_data.get("year")
            
            # Form clean label: "Company (Year)" or "Filename"
            company_name = doc.company_name or doc.original_filename.rsplit(".", 1)[0]
            label = f"{company_name} ({year})" if year else company_name

            compared_entities.append(CompanyMeta(
                document_id=doc.id,
                company_name=company_name,
                year=year,
                document_type=doc.document_type,
            ))

            # Compute ratios
            computed = await FinancialRatioCalculator.calculate_ratios(
                normalized_data,
                db=self._db,
                user_id=user_id,
                sector=doc.sector,
            )
            company_ratios[label] = computed

        # ── 2. Format Side-by-Side Matrix ──
        # Target flat matrix structure: {"roe": {"Label A": 0.20, "Label B": 0.12}}
        comparison_matrix: dict[str, dict[str, float | None]] = {}
        
        # Helper list of ratio keys to extract
        target_metrics = [
            ("profitability", "gross_margin"),
            ("profitability", "net_margin"),
            ("profitability", "roe"),
            ("profitability", "roa"),
            ("liquidity", "current_ratio"),
            ("liquidity", "quick_ratio"),
            ("solvency", "debt_ratio"),
            ("solvency", "debt_to_equity"),
            ("operations", "operating_margin"),
            ("operations", "ebitda"),
        ]

        for group_name, metric_name in target_metrics:
            comparison_matrix[metric_name] = {}
            for label, group_dict in company_ratios.items():
                val = group_dict.get(group_name, {}).get(metric_name, {}).get("value")
                comparison_matrix[metric_name][label] = val

        # ── 3. Call Groq for AI evaluation ──
        logger.info("requesting_ai_comparison_json_mode", count=len(doc_ids))
        
        prompt = f"""
Here is the side-by-side financial comparison matrix containing calculated ratios for the entities:
{json.dumps(comparison_matrix, indent=2)}

Please generate the comparative financial analyst report. Make sure to:
- Compare the numbers directly and calculate differences.
- Keep the tone professional, objective, and authoritative.
- Vietnamese is the required output language.
- Output ONLY valid JSON matching the schema.
"""

        try:
            response = await self._groq.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for highly analytical deterministic outputs
                response_format={"type": "json_object"},  # Force JSON Mode
            )

            raw_json = response.choices[0].message.content or "{}"
            
            # Validate output matches schema
            ai_eval = AIComparisonEvaluation.model_validate_json(raw_json)

            return ComparisonResponse(
                compared_entities=compared_entities,
                comparison_matrix=comparison_matrix,
                ai_evaluation=ai_eval,
            )

        except Exception as e:
            logger.exception("ai_comparison_generation_failed", error=str(e))
            raise ValidationFailedError(
                f"Failed to generate structured AI comparison: {e}",
                details={"document_ids": [str(i) for i in doc_ids]},
            )
