"""Observability helpers for LangSmith + OpenTelemetry instrumentation."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

_TRACER = None
_TRACER_INITIALIZED = False


def init_langsmith(project: str = "CensorshipCrossChecker") -> None:
    """Enable LangSmith tracing if credentials are present."""
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ.setdefault("LANGCHAIN_PROJECT", project)
        logger.info("LangSmith tracing enabled for project %s", project)
    else:
        logger.info("LangSmith API key not found. Tracing will be local.")


def _ensure_tracer() -> Optional["Tracer"]:
    global _TRACER_INITIALIZED, _TRACER
    if _TRACER_INITIALIZED:
        return _TRACER

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:  # pragma: no cover
        logger.warning("OpenTelemetry not installed; spans will be no-ops.")
        _TRACER_INITIALIZED = True
        _TRACER = None
        return None

    resource = Resource.create({"service.name": "censorship-cross-checker"})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _TRACER = trace.get_tracer(__name__)
    _TRACER_INITIALIZED = True
    return _TRACER


def get_tracer():
    return _ensure_tracer()


@contextmanager
def otel_span(name: str) -> Iterator[None]:
    tracer = _ensure_tracer()
    if tracer is None:
        yield
        return

    with tracer.start_as_current_span(name):
        yield
