from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Custom Exception Hierarchy ─────────────────────────────────────────────────

class FiscalMindException(Exception):
    """
    Base exception for all application-specific errors.
    All custom exceptions should inherit from this class.
    """
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(FiscalMindException):
    """Resource not found (404)."""
    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with id '{identifier}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)},
        )


class UnauthorizedError(FiscalMindException):
    """Authentication required or credentials invalid (401)."""
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )


class ForbiddenError(FiscalMindException):
    """Access denied — authenticated but not permitted (403)."""
    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


class ConflictError(FiscalMindException):
    """Resource already exists (409)."""
    def __init__(self, resource: str, field: str, value: Any) -> None:
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            details={"resource": resource, "field": field, "value": str(value)},
        )


class ValidationFailedError(FiscalMindException):
    """Business rule validation failed (422)."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_FAILED",
            details=details or {},
        )


class DocumentProcessingError(FiscalMindException):
    """Error during document parsing/OCR/embedding."""
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DOCUMENT_PROCESSING_ERROR",
            details=details or {},
        )


# ── Error Response Builder ─────────────────────────────────────────────────────

def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: dict | None = None,
) -> JSONResponse:
    """
    Builds a standardized JSON error response.

    All errors follow this consistent shape:
    {
        "error": {
            "code": "NOT_FOUND",
            "message": "Document with id '123' not found.",
            "details": {}
        }
    }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": error_code,
                "message": message,
                "details": details or {},
            }
        },
    )


# ── Exception Handlers ─────────────────────────────────────────────────────────

async def fiscalmind_exception_handler(
    request: Request,
    exc: FiscalMindException,
) -> JSONResponse:
    """Handles all custom FiscalMind application exceptions."""
    logger.warning(
        "application_error",
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url),
        status_code=exc.status_code,
    )
    return _error_response(exc.status_code, exc.error_code, exc.message, exc.details)


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """Handles FastAPI's built-in HTTPExceptions."""
    logger.warning(
        "http_error",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url),
    )
    return _error_response(exc.status_code, "HTTP_ERROR", str(exc.detail))


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handles Pydantic request validation errors (422).
    Formats field errors into a readable structure.
    """
    field_errors: dict[str, list[str]] = {}
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        field_errors.setdefault(field, []).append(error["msg"])

    logger.warning(
        "validation_error",
        path=str(request.url),
        errors=field_errors,
    )
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"fields": field_errors},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.
    Logs full traceback but returns a safe generic message to the client.
    """
    logger.exception(
        "unhandled_exception",
        path=str(request.url),
        exc_info=exc,
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
    )
