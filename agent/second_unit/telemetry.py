"""Export both the agent graph's own execution AND the backlot render
workers' metrics/logs/traces into Grafana Cloud over one OTLP gateway — the
partner's love-language integration, and the fix for the CRITICAL finding
that no real telemetry had ever actually been pushed (the old code called a
Prometheus remote-write encoder that just `raise NotImplementedError`).

Required environment (see infra/01_secrets.sh):
  OTEL_EXPORTER_OTLP_ENDPOINT       Grafana Cloud OTLP gateway URL, e.g.
                                     https://otlp-gateway-prod-<region>.grafana.net/otlp
  OTEL_EXPORTER_OTLP_HEADERS        "Authorization=Basic <base64 instanceID:token>"
"""
from __future__ import annotations

import os

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_configured_services: set[str] = set()
_log_handlers: dict[str, LoggingHandler] = {}


def configure_tracing(service_name: str = "second-unit-agent") -> trace.Tracer:
    """Configure tracing, metrics, and logging for `service_name` in one call
    (all three share the same OTLP gateway and resource attributes). Kept the
    name `configure_tracing` since render_worker.py and server.py already
    call it for spans; it's now also the entrypoint for metrics/logs.
    """
    if service_name not in _configured_services:
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        resource = Resource.create({SERVICE_NAME: service_name})

        tracer_provider = TracerProvider(resource=resource)
        if endpoint:
            tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

        if endpoint:
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
            )
            metrics.set_meter_provider(meter_provider)

            logger_provider = LoggerProvider(resource=resource)
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
            set_logger_provider(logger_provider)
            _log_handlers[service_name] = LoggingHandler(logger_provider=logger_provider)

        _configured_services.add(service_name)
    return trace.get_tracer(service_name)


def get_meter(service_name: str = "second-unit-agent"):
    return metrics.get_meter(service_name)


def get_log_handler(service_name: str = "second-unit-agent") -> LoggingHandler | None:
    """Returns the OTLP logging handler for `service_name`, or None if OTLP
    isn't configured (e.g. running locally without OTEL_EXPORTER_OTLP_ENDPOINT).
    configure_tracing(service_name) must be called first.
    """
    return _log_handlers.get(service_name)


# No auto-run here. OTel's global tracer/meter/logger providers can only be
# set once per process — a module-level `configure_tracing()` call here used
# to win that race unconditionally with the default "second-unit-agent" name,
# so backlot/worker/render_worker.py's later `configure_tracing(service_name=
# "second-unit-backlot")` was silently ignored and every backlot span/metric/
# log ended up mislabeled under the agent service's name in Grafana. Every
# real caller (agent/second_unit/agent.py, render_worker.py) now calls
# configure_tracing(service_name=...) explicitly and is the first (only)
# caller in its own process.
#
# No custom per-stage span decorator here. Once the global tracer provider
# above is set, google-adk's own instrumentation (google/adk/telemetry/
# tracing.py) already emits a full span tree for every run — invoke_agent
# <name> per sub-agent, call_llm/generate_content per model call, and
# execute_tool per tool call — with the model's actual response text
# attached as a span attribute (gen_ai semconv, content capture on by
# default). Verified live: a real POST /runs against the deployed agent
# produced a 35-span trace in Tempo including "invoke_agent EyesAgent" and
# "invoke_agent MetricsAgent" nodes with real reasoning text on them.
# A hand-rolled traced_stage() decorator here would just be reimplementing,
# worse, telemetry the framework already provides for free.
