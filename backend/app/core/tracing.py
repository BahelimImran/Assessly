import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode

from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Why:
# Both the FastAPI process and the worker process import this same module.
# OTEL_SERVICE_NAME differentiates them in Jaeger/Grafana even though
# they share one codebase (set via env var per process, see docker-compose below).
_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "Assessly-AI")
_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")

_tracer_provider = None


def setup_tracing():
    global _tracer_provider
    if _tracer_provider is not None:
        return trace.get_tracer(_SERVICE_NAME)

    resource = Resource.create({"service.name": _SERVICE_NAME})
    RequestsInstrumentor().instrument() #ADD AFTER Redis instrumentation-check??
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _tracer_provider = provider
    return trace.get_tracer(_SERVICE_NAME)


tracer = setup_tracing()


def mark_span_error(span, exc: Exception):
    """Small helper so worker.py and routes don't repeat this every except block."""
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))

def add_span_event(span, name: str, **attrs):
    span.add_event(name, attributes=attrs or {})