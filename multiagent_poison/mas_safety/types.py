"""Core data types for MAS safety evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AttackCategory(str, Enum):
    """Attack taxonomy (Table 1, arXiv:2503.12188v2)."""

    MAS_HIJACKING = "mas_hijacking"
    INDIRECT_PROMPT_INJECTION = "indirect_prompt_injection"
    PROMPT_INFECTION = "prompt_infection"
    DIRECT_ASK = "direct_ask"
    BENIGN = "benign"


class InputModality(str, Enum):
    LOCAL_FILE = "local_file"
    WEB_TEXT = "web_text"
    WEB_REDIRECT = "web_redirect"
    WEB_SINGLE = "web_single"
    WEB_IMAGE = "web_image"
    LOCAL_VIDEO = "local_video"
    INCIDENTAL_CONTACT = "incidental_contact"


class ErrorTemplate(str, Enum):
    PYTHON_TRACEBACK = "python_traceback"
    WORDPRESS_403 = "wordpress_403"
    ACCESS_DENIED = "access_denied"


class PayloadType(str, Enum):
    RCE_MARKER = "rce_marker"
    DATA_EXFIL = "data_exfil"


class OrchestratorType(str, Enum):
    CENTRAL = "central_orchestrator"
    CENTRAL_LEDGER = "central_orchestrator_ledger"
    ROUND_ROBIN = "round_robin"


@dataclass
class AttackScenario:
    """One evaluation scenario configuration."""

    name: str
    category: AttackCategory
    modality: InputModality
    error_template: ErrorTemplate | None = None
    payload_type: PayloadType = PayloadType.RCE_MARKER
    user_queries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Single message in an agent trace."""

    agent: str
    role: str
    content: str
    turn: int = 0


@dataclass
class TrialResult:
    """Outcome of a single trial run."""

    scenario: str
    trial_id: int
    success: bool
    refused: bool
    metadata_poisoned: bool
    control_flow_hijacked: bool
    payload_executed: bool
    confused_deputy_agent: str | None
    messages: list[AgentMessage] = field(default_factory=list)
    markers_found: list[str] = field(default_factory=list)
    unsafe_code_detected: bool = False
    notes: str = ""


@dataclass
class AttackResult:
    """Aggregated results for a scenario."""

    scenario: AttackScenario
    trials: int
    attack_success_rate: float
    refusal_rate: float
    metadata_poison_rate: float
    control_flow_hijack_rate: float
    trial_results: list[TrialResult] = field(default_factory=list)

    @property
    def successes(self) -> int:
        return sum(1 for t in self.trial_results if t.success)

    @property
    def refusals(self) -> int:
        return sum(1 for t in self.trial_results if t.refused)
