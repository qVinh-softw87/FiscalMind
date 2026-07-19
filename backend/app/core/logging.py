from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict, Processor


def _add_app_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Injects application-level context into every log entry."""
    event_dict.setdefault("app", "fiscalmind")
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """
    Configures structured JSON logging using structlog.

    In development: colored, human-readable console output.
    In production: machine-parseable JSON for log aggregators (Datadog, CloudWatch).

    Why structured logging?
    - Every log line is a JSON object with consistent fields
    - Easy to filter/search by request_id, user_id, trace_id
    - Enables alerting on specific error patterns
    """
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_app_context,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if debug:
        # Human-readable output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON output for production log aggregation
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if debug else logging.WARNING
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Returns a named structured logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("document_uploaded", user_id=user.id, filename="report.pdf")
    """
    return structlog.get_logger(name)
