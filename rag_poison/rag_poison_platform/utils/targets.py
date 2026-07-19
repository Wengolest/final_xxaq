"""Load security evaluation targets."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from utils.paths import TARGETS_PATH


@dataclass
class SecurityTarget:
    target_id: str
    question: str
    clean_expected: str
    attacker_target: str
    agent_spec: str = ""
    related_policies: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityTarget":
        return cls(
            target_id=data["target_id"],
            question=data["question"],
            clean_expected=data["clean_expected"],
            attacker_target=data["attacker_target"],
            agent_spec=data.get("agent_spec", ""),
            related_policies=list(data.get("related_policies", [])),
        )


def load_targets(path: Optional[Path] = None) -> List[SecurityTarget]:
    config_path = path or TARGETS_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return [SecurityTarget.from_dict(item) for item in payload["targets"]]


def get_target_by_id(
    target_id: str,
    targets: Optional[List[SecurityTarget]] = None,
) -> SecurityTarget:
    items = targets or load_targets()
    for target in items:
        if target.target_id == target_id:
            return target
    raise KeyError(f"Unknown target_id: {target_id}")
