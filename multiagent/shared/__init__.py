"""Shared attack components — payloads, templates, fixtures, trace analysis."""

from .payloads import rce_marker_payload, exfil_payload, MARKER_PREFIX, EXFIL_PREFIX
from .templates import build_hijack_content, ORCHESTRATOR_INSTRUCTIONS, ErrorTemplate, PayloadType
from .fixtures import FixtureGenerator
from .trace_analyzer import TraceAnalyzer, TrialResult

__all__ = [
    "rce_marker_payload", "exfil_payload", "MARKER_PREFIX", "EXFIL_PREFIX",
    "build_hijack_content", "ORCHESTRATOR_INSTRUCTIONS", "ErrorTemplate", "PayloadType",
    "FixtureGenerator", "TraceAnalyzer", "TrialResult",
]
