"""Check experiment closure: A-F outputs, sample pool, poison matrix, reports (read-only)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))

from target_agents.bulk_common import RESULTS_DIR
from target_agents.poison_tests.case_loader import validate_cases

# A-F canonical outputs (do not rename or overwrite)
AF_OUTPUTS = {
    "mock_asr": RESULTS_DIR / "mock_asr.csv",
    "tool_poison_mock": RESULTS_DIR / "tool_poison_mock.csv",
}

CLOSURE_FILES = [
    "agent_api_env_check.csv",
    "agent_sample_pool.csv",
    "agent_sample_pool_summary.json",
    "local_rag_variants.csv",
    "bulk_agent_poison_smoke_test.csv",
    "poison_experiment_matrix.csv",
    "poison_experiment_summary.csv",
    "poison_experiment_summary.json",
    "poison_experiment_report.md",
    "bulk_agent_deployment_report.md",
    "external_agent_candidate_shortlist.csv",
    "external_agent_adapter_probe.csv",
    "external_agent_poison_smoke.csv",
]


def _status(path: Path) -> dict:
    if not path.is_file():
        return {"exists": False, "size": 0, "rows": 0}
    size = path.stat().st_size
    rows = 0
    if path.suffix == ".csv" and size > 0:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = max(0, sum(1 for _ in csv.reader(f)) - 1)
    return {"exists": True, "size": size, "rows": rows}


def main() -> None:
    print("=== Experiment Closure Check ===")
    print(f"RESULTS_DIR: {RESULTS_DIR}")
    print()

    print("-- A-F Main Experiments (canonical filenames) --")
    for name, path in AF_OUTPUTS.items():
        st = _status(path)
        note = ""
        if name == "mock_asr":
            note = " (runners/run_mock_asr.py -> mock_asr.csv)"
        elif name == "tool_poison_mock":
            note = " (runners/run_tool_poison_mock.py -> tool_poison_mock.csv)"
        flag = "OK" if st["exists"] and st["rows"] > 0 else "MISSING"
        print(f"  [{flag}] {path.name}{note} rows={st['rows']} size={st['size']}")

    for extra in ("mock_asr.summary.json", "tool_poison_mock.summary.json"):
        p = RESULTS_DIR / extra
        print(f"  [{'OK' if p.is_file() else 'MISS'}] {extra}")

    print()
    print("-- Poison Matrix Validation --")
    v = validate_cases()
    print(f"  styles_complete={v['styles_complete']} fields_complete={v.get('fields_complete')}")
    print(f"  by_style={v['by_style']}")

    print()
    print("-- Closure Artifacts --")
    ok = 0
    for fname in CLOSURE_FILES:
        st = _status(RESULTS_DIR / fname)
        flag = "OK" if st["exists"] else "MISS"
        if st["exists"]:
            ok += 1
        extra = f" rows={st['rows']}" if fname.endswith(".csv") else ""
        print(f"  [{flag}] {fname}{extra}")

    print()
    print(f"closure_files: {ok}/{len(CLOSURE_FILES)}")
    pool = RESULTS_DIR / "agent_sample_pool_summary.json"
    if pool.is_file():
        data = json.loads(pool.read_text(encoding="utf-8"))
        print(f"pool_complete={data.get('pool_complete')} total={data.get('total_samples')} poison_supported={data.get('poison_test_supported_count')}")

    poison_sum = RESULTS_DIR / "poison_experiment_summary.json"
    if poison_sum.is_file():
        data = json.loads(poison_sum.read_text(encoding="utf-8"))
        overall = next((s for s in data.get("summaries", []) if s.get("dimension") == "overall"), {})
        print(
            "poison_matrix: "
            f"rows={data.get('matrix_row_count')} "
            f"retrieval={overall.get('poison_retrieval_hit_rate')} "
            f"keyword_hit={overall.get('poison_answer_keyword_hit_rate')} "
            f"strict_attack={overall.get('poison_strict_attack_success_rate')}"
        )


if __name__ == "__main__":
    main()
