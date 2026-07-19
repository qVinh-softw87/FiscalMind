from __future__ import annotations

import mimetypes
from pathlib import Path

from app.core.logging import get_logger
from app.financial_engine.detector import StatementDetector
from app.financial_engine.extractor import FinancialTableExtractor
from app.financial_engine.normalizer import FinancialDataNormalizer
from app.financial_engine.ocr import PaddleOCRServiceProcessor
from app.models.document import DocumentType

logger = get_logger(__name__)


class FinancialParser:
    """
    Orchestrates the entire document parsing pipeline.

    Input: file_path (PDF, XLSX, CSV)
    Output:
        - document_type: DocumentType (detected classification)
        - tables: list of extracted tables
        - normalized_data: dict of standard metrics
        - raw_text: full text representation (for Qdrant RAG index)
    """

    def __init__(self, ocr_processor: PaddleOCRServiceProcessor | None = None) -> None:
        self.ocr_processor = ocr_processor or PaddleOCRServiceProcessor()

    async def parse_document(
        self,
        file_path: str,
        original_filename: str,
        mime_type: str | None = None,
    ) -> dict:
        """
        Runs the extraction pipeline based on file format.
        """
        ext = Path(original_filename).suffix.lower()
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(original_filename)

        raw_text = ""
        tables = []
        normalized_data = {}
        doc_type = DocumentType.UNKNOWN

        logger.info(
            "parsing_started",
            file_path=file_path,
            ext=ext,
            mime_type=mime_type,
        )

        try:
            # ── 1. Read files and extract tabular/text data ─────────────────────
            if ext in (".xlsx", ".xls"):
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                tables = FinancialTableExtractor.extract_from_excel(file_bytes)
                doc_type = DocumentType.ANNUAL_REPORT  # Excel spreadsheets are usually entire reports
                # Generate text mock from table content for vector embedding in RAG
                raw_text = self._build_text_fallback_from_tables(tables)

            elif ext == ".csv":
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                tables = FinancialTableExtractor.extract_from_csv(file_bytes)
                doc_type = DocumentType.OTHER
                raw_text = self._build_text_fallback_from_tables(tables)

            elif ext == ".pdf" or mime_type == "application/pdf":
                # PDF Pipeline (requires OCR + table extraction)
                raw_text = await self.ocr_processor.extract_text_from_pdf(file_path)

                # Attempt table extraction from native structure
                tables = FinancialTableExtractor.extract_from_pdf(file_path)

                # Fallback: if no tables extracted natively but OCR text exists, try regex heuristic
                if not tables and raw_text:
                    tables = FinancialTableExtractor.extract_from_ocr_text(raw_text)

                # Detect statement type using keywords on full text
                doc_type = StatementDetector.detect_type(raw_text)

            else:
                # Text files
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
                doc_type = DocumentType.OTHER

            # ── 2. Standardize financial variables ─────────────────────────────
            for table in tables:
                t_metrics = FinancialDataNormalizer.normalize_table(
                    headers=table.get("headers", []),
                    rows=table.get("rows", []),
                )
                normalized_data.update(t_metrics)

            logger.info(
                "parsing_completed",
                file_path=file_path,
                tables_extracted=len(tables),
                metrics_found=len(normalized_data),
                detected_type=doc_type.value,
            )

        except Exception as e:
            logger.exception("parsing_failed", file_path=file_path, error=str(e))
            raise

        return {
            "document_type": doc_type,
            "raw_text": raw_text,
            "tables": tables,
            "normalized_data": normalized_data,
        }

    def _build_text_fallback_from_tables(self, tables: list[dict]) -> str:
        """Helper that turns Excel tables into readable text lines for the RAG search index."""
        lines = []
        for t in tables:
            source = t.get("source", "table")
            lines.append(f"--- Table from {source} ---")
            for row in t.get("rows", []):
                lines.append(" | ".join(row))
        return "\n".join(lines)
