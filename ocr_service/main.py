from __future__ import annotations

import io
import logging

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from paddleocr import PaddleOCR
from PIL import Image

# Disable verbose logging from PaddleOCR
logging.getLogger("ppocr").setLevel(logging.WARNING)

app = FastAPI(
    title="PaddleOCR Serving API",
    description="Microservice exposing high-precision OCR endpoint using PaddleOCR.",
)

# Initialize PaddleOCR engine once at start
# - lang="vi" supports high-precision Vietnamese OCR
# - use_angle_cls=True auto-corrects rotated documents
ocr = PaddleOCR(use_angle_cls=True, lang="vi", show_log=False)


@app.get("/health")
def health() -> dict:
    """Readiness endpoint."""
    return {"status": "ok", "service": "paddleocr"}


@app.post("/predict")
async def predict(file: UploadFile = File(...)) -> dict:
    """
    Accepts an image file and returns OCR-extracted text regions.

    Returns:
        results: list of {text: str, confidence: float, box: list}
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only image files are accepted.",
        )

    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")

        # Convert PIL to numpy array (required by PaddleOCR)
        img_array = np.array(image)

        # Execute OCR inference
        result = ocr.ocr(img_array, cls=True)

        extracted_regions = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                box = line[0]  # Coordinates of bounding box: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                extracted_regions.append({
                    "text": text,
                    "confidence": float(confidence),
                    "box": box,
                })

        return {"results": extracted_regions}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR engine failure: {str(e)}",
        )
