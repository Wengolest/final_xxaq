"""
普适 Agent 多步推理链投毒评测 runner。

用法:
  python -m runners.run_agent_chain_poison
  python -m runners.run_agent_chain_poison --limit 5 --fast
  python -m runners.run_agent_chain_poison --limit 20 --fast
  python -m runners.run_agent_chain_poison --resume outputs/agent_chain_poison/xxx.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from agent_chain_poison.agent_runner import AgentChainRunner
from agent_chain_poison.cases import get_cases
from agent_chain_poison.evaluator import aggregate_summary, evaluate_case_result, render_summary_markdown
from utils.deepseek_env import deepseek_available, load_deepseek_env

CSV_FIELDS = [
    "run_id",
    "case_id",
    "task_type",
    "poison_type",
    "injection_step",
    "target_drift",
    "clean_final_risk",
    "poisoned_final_risk",
    "plan_shift",
    "evidence_shift",
    "reasoning_shift",
    "decision_shift",
    "tool_action_shift",
    "final_answer_shift",
    "autonomous_action",
    "risk_downgrade",
    "strict_success",
    "clean_final_answer",
    "poisoned_final_answer",
    "clean_trajectory_json",
    "poisoned_trajectory_json",
    "error",
]


def _make_run_id() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"agent_chain_poison_{stamp}_{uuid.uuid4().hex[:8]}"


def _find_latest_csv(output_dir: Path) -> Optional[Path]:
    candidates = sorted(output_dir.glob("agent_chain_poison_*.csv"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def _load_completed_case_ids(csv_path: Path) -> Set[str]:
    if not csv_path.is_file():
        return set()
    done: Set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cid = (row.get("case_id") or "").strip()
            if cid:
                done.add(cid)
    return done


def _load_existing_rows(csv_path: Path) -> List[Dict[str, Any]]:
    if not csv_path.is_file():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_run_id(csv_path: Path, fallback: str) -> str:
    rows = _load_existing_rows(csv_path)
    if rows and rows[0].get("run_id"):
        return str(rows[0]["run_id"])
    return fallback


def _ensure_csv_header(csv_path: Path) -> None:
    if csv_path.is_file() and csv_path.stat().st_size > 0:
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()


def _append_csv_row(csv_path: Path, row: Dict[str, Any]) -> None:
    with csv_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writerow(row)


def _error_row(case: Dict[str, Any], run_id: str, exc: Exception) -> Dict[str, Any]:
    return {
        "run_id": run_id,
        "case_id": case["case_id"],
        "task_type": case["task_type"],
        "poison_type": case["poison_type"],
        "injection_step": case["injection_step"],
        "target_drift": case.get("target_drift", ""),
        "clean_final_risk": "",
        "poisoned_final_risk": "",
        "plan_shift": 0,
        "evidence_shift": 0,
        "reasoning_shift": 0,
        "decision_shift": 0,
        "tool_action_shift": 0,
        "final_answer_shift": 0,
        "autonomous_action": 0,
        "risk_downgrade": 0,
        "strict_success": 0,
        "clean_final_answer": "",
        "poisoned_final_answer": "",
        "clean_trajectory_json": "[]",
        "poisoned_trajectory_json": "[]",
        "error": str(exc),
    }


def _write_summaries(
    rows: List[Dict[str, Any]],
    *,
    run_id: str,
    run_meta: Dict[str, Any],
    summary_json_path: Path,
    summary_md_path: Path,
) -> Dict[str, Any]:
    summary = aggregate_summary(rows)
    summary_payload = {**summary, "run_meta": run_meta}
    summary_json_path.write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_md_path.write_text(
        render_summary_markdown(summary, run_meta=run_meta),
        encoding="utf-8",
    )
    return summary


def run_experiment(
    *,
    limit: int = 20,
    case_id: str | None = None,
    poison_type: str | None = None,
    output_dir: Path,
    model: str,
    temperature: float,
    max_retries: int,
    fast: bool = True,
    resume: str | None = None,
) -> Dict[str, Any]:
    if not deepseek_available():
        raise RuntimeError(
            "Missing DEEPSEEK_API_KEY.\n"
            "PowerShell:\n"
            '  $env:DEEPSEEK_API_KEY="你的key"\n'
            '  $env:DEEPSEEK_BASE_URL="https://api.deepseek.com"\n'
            '  $env:DEEPSEEK_MODEL="deepseek-chat"\n'
            "或在 rag_poison_platform\\.env 中配置。"
        )

    cases = get_cases(limit=limit, case_id=case_id, poison_type=poison_type)
    if not cases:
        raise RuntimeError("No cases matched the given filters.")

    output_dir.mkdir(parents=True, exist_ok=True)

    resume_path: Optional[Path] = None
    if resume:
        resume_path = Path(resume)
        if not resume_path.is_absolute():
            resume_path = PLATFORM_ROOT / resume_path
    elif resume is not None:
        resume_path = _find_latest_csv(output_dir)

    new_run_id = _make_run_id()
    if resume_path and resume_path.is_file():
        csv_path = resume_path
        run_id = _read_run_id(csv_path, new_run_id)
        completed = _load_completed_case_ids(csv_path)
        rows = _load_existing_rows(csv_path)
        print(f"Resume from {csv_path} ({len(completed)} cases already done)")
    else:
        csv_path = output_dir / f"{new_run_id}.csv"
        run_id = new_run_id
        completed = set()
        rows = []
        _ensure_csv_header(csv_path)

    summary_json_path = csv_path.with_suffix(".summary.json")
    summary_md_path = csv_path.with_suffix(".summary.md")

    runner = AgentChainRunner(
        model=model,
        temperature=temperature,
        max_retries=max_retries,
        fast=fast,
    )

    pending = [c for c in cases if c["case_id"] not in completed]
    total = len(cases)
    mode = "fast" if fast else "standard"

    env = load_deepseek_env()
    run_meta = {
        "run_id": run_id,
        "model": model or env.get("DEEPSEEK_MODEL", "deepseek-chat"),
        "temperature": temperature,
        "max_retries": max_retries,
        "fast": fast,
        "mode": mode,
        "case_count": len(cases),
        "filters": {
            "limit": limit,
            "case_id": case_id,
            "poison_type": poison_type,
            "resume": str(resume_path) if resume_path else None,
        },
    }

    print(f"Run {run_id} | mode={mode} | total={total} | pending={len(pending)}")

    for idx, case in enumerate(cases, start=1):
        if case["case_id"] in completed:
            continue
        try:
            run_result = runner.run_case(case)
            row = evaluate_case_result(case, run_result)
            row["run_id"] = run_id
            if not row.get("error"):
                row["error"] = ""
        except Exception as exc:
            row = _error_row(case, run_id, exc)

        _append_csv_row(csv_path, row)
        rows.append(row)

        strict = int(row.get("strict_success", 0))
        print(
            f"[{idx}/{total}] {case['case_id']} {case['poison_type']} strict_success={strict}",
            flush=True,
        )

    summary = _write_summaries(
        rows,
        run_id=run_id,
        run_meta=run_meta,
        summary_json_path=summary_json_path,
        summary_md_path=summary_md_path,
    )

    print(f"\nWrote CSV -> {csv_path}")
    print(f"Wrote summary JSON -> {summary_json_path}")
    print(f"Wrote summary MD -> {summary_md_path}")
    print(f"strict_success_rate: {summary['strict_success_rate']:.2%}")

    return {
        "csv": csv_path,
        "summary_json": summary_json_path,
        "summary_md": summary_md_path,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent chain poison experiment runner")
    parser.add_argument("--limit", type=int, default=20, help="Max cases to run (default: 20)")
    parser.add_argument("--case-id", type=str, default=None, help="Run single case by id")
    parser.add_argument("--poison-type", type=str, default=None, help="Filter by poison type")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/agent_chain_poison",
        help="Output directory",
    )
    parser.add_argument("--model", type=str, default="deepseek-chat", help="DeepSeek model")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM temperature")
    parser.add_argument("--max-retries", type=int, default=2, help="LLM retry count")
    parser.add_argument(
        "--fast",
        action="store_true",
        default=True,
        help="Fast mode: 4 LLM calls per case (default: on)",
    )
    parser.add_argument(
        "--no-fast",
        action="store_false",
        dest="fast",
        help="Standard 4-step mode: 6 LLM calls per case",
    )
    parser.add_argument(
        "--resume",
        nargs="?",
        const="",
        default=None,
        help="Resume from CSV (optional path; default: latest in output-dir)",
    )
    args = parser.parse_args()

    output_dir = PLATFORM_ROOT / args.output_dir
    run_experiment(
        limit=args.limit,
        case_id=args.case_id,
        poison_type=args.poison_type,
        output_dir=output_dir,
        model=args.model,
        temperature=args.temperature,
        max_retries=args.max_retries,
        fast=args.fast,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
