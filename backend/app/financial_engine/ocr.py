from __future__ import annotations

import io
from abc import ABC, abstractmethod

import httpx
import pdfplumber
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OCRProcessor(ABC):
    """
    Abstract interface for OCR operations (Adapter Pattern).
    Allows transparent changes to OCR engines.
    """

    @abstractmethod
    async def extract_text_from_pdf(self, file_path: str) -> str:
        """Extracts text from a PDF file (handling both digital and scanned PDFs)."""
        ...


class PaddleOCRServiceProcessor(OCRProcessor):
    """
    OCR Processor using the external PaddleOCR serving microservice (Option B).

    Optimization Strategy:
    1. Try to read text directly (Digital PDF).
    2. If no text or very short text is found → Render pages to images in-memory and
       send them to the local PaddleOCR microservice via HTTP API.
    """

    def __init__(self, ocr_service_url: str | None = None) -> None:
        self.ocr_service_url = ocr_service_url or settings.OCR_SERVICE_URL
        self.client = httpx.AsyncClient(timeout=60.0)  # OCR can take time

    async def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extracts text page-by-page.
        Determines whether to use native text extraction or PaddleOCR.
        """
        extracted_pages: list[str] = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for idx, page in enumerate(pdf.pages):
                    # 1. Attempt native digital extraction
                    text = page.extract_text() or ""

                    # Threshold: if page text is very short, it's probably scanned or has missing fonts
                    if len(text.strip()) > 100:
                        logger.info(
                            "native_pdf_text_extracted",
                            page=idx + 1,
                            char_count=len(text),
                        )
                        extracted_pages.append(text)
                    else:
                        # 2. Trigger PaddleOCR microservice for scanned page
                        logger.info(
                            "scanned_pdf_page_detected",
                            page=idx + 1,
                            reason="low_native_text_length",
                        )
                        ocr_text = await self._ocr_page_via_service(page, idx + 1)
                        extracted_pages.append(ocr_text)

        except Exception as e:
            logger.error("pdf_extraction_failed", file_path=file_path, error=str(e))
            raise

        return "\n\n--- PAGE BREAK ---\n\n".join(extracted_pages)

    async def _ocr_page_via_service(
        self,
        page: pdfplumber.page.Page,
        page_num: int,
    ) -> str:
        """
        Renders PDF page to PNG in-memory and sends it to the OCR microservice.
        Zero dependencies on system binary packages (like poppler).
        """
        try:
            # Render page to PIL image
            im = page.to_image(resolution=150)
            img_bytes_io = io.BytesIO()
            im.original.save(img_bytes_io, format="PNG")
            img_bytes = img_bytes_io.getvalue()

            # Dispatch HTTP post request to ocr-service
            files = {"file": ("page.png", img_bytes, "image/png")}
            url = f"{self.ocr_service_url}/predict"

            response = await self.client.post(url, files=files)

            if response.status_code != 200:
                logger.error(
                    "ocr_service_error_response",
                    status_code=response.status_code,
                    page=page_num,
                )
                return ""

            data = response.json()
            results = data.get("results", [])

            # Join lines based on confidence threshold
            lines = [
                res["text"]
                for res in results
                if res.get("confidence", 0.0) > 0.5
            ]

            ocr_text = "\n".join(lines)
            logger.info(
                "ocr_service_page_complete",
                page=page_num,
                lines_extracted=len(lines),
            )
            return ocr_text

        except Exception as e:
            logger.exception(
                "ocr_page_service_failed",
                page=page_num,
                error=str(e),
            )
            return ""
