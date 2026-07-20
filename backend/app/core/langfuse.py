import os
from langfuse import Langfuse
from opentelemetry.trace import get_current_span
print("LF HOST:", os.getenv("LANGFUSE_HOST"))
_langfuse = None


def get_langfuse():
    global _langfuse
    if _langfuse:
        return _langfuse

    # _langfuse = Langfuse(
    #     public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    #     secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    #     host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    # )
    #     LANGFUSE_SECRET_KEY="sk-lf-1c8406f7-bb12-4e6c-a3fb-dd426d80a2d7"
    # LANGFUSE_PUBLIC_KEY="pk-lf-dc4e56e9-1bc1-4506-8c0a-e99e12eb4691"
    # LANGFUSE_BASE_URL="https://cloud.langfuse.com"
    _langfuse = Langfuse(
    public_key="pk-lf-dc4e56e9-1bc1-4506-8c0a-e99e12eb4691",
    secret_key="sk-lf-1c8406f7-bb12-4e6c-a3fb-dd426d80a2d7",
    host="https://cloud.langfuse.com"
    )
    return _langfuse


def get_trace_context():
    """
    Bridge OpenTelemetry → Langfuse
    """
    span = get_current_span()
    ctx = span.get_span_context()

    return {
        "trace_id": format(ctx.trace_id, "032x") if ctx.trace_id else None,
        "span_id": format(ctx.span_id, "016x") if ctx.span_id else None,
    }