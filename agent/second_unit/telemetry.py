"""Export the agent graph's own execution as OpenTelemetry traces into Grafana
Tempo — so a judge (or an engineer) can debug the AI inside the partner's own
tool, the same way they'd debug any other service on the farm.

Required environment:
  OTEL_EXPORTER_OTLP_ENDPOINT       Grafana Cloud OTLP gateway URL
  OTEL_EXPORTER_OTLP_HEADERS        "Authorization=Basic <base64 instanceID:token>"
"""
from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured = False


def configure_tracing(service_name: str = "second-unit-agent") -> trace.Tracer:
    global _configured
    if not _configured:
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
        if endpoint:
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        _configured = True
    return trace.get_tracer(service_name)


tracer = configure_tracing()


def traced_stage(stage_name: str):
    """Decorator: wrap an agent stage function so its reasoning appears as a
    span in Tempo, labeled by stage (triage, evidence, verify, impact, ...).
    """

    def decorator(fn):
        def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(f"second_unit.{stage_name}") as span:
                result = fn(*args, **kwargs)
                # Agents attach human-readable reasoning as a span attribute so
                # it's visible directly in the Tempo trace view, not just in logs.
                reasoning = getattr(result, "reasoning", None)
                if reasoning:
                    span.set_attribute("second_unit.reasoning", str(reasoning)[:2000])
                return result

        return wrapper

    return decorator
