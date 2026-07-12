"""
原生 Agent MCP 投毒评估入口（各框架自有 SDK + 独立 venv）。

各 Agent 使用 agents/{id}/venv 内原生 SDK；输出文件名带 native 前缀。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.agent_runners.common import load_deepseek_env
from src.agent_runners.native.adapters import FC_TIER_NATIVE, MCP_TIER_NATIVE, NATIVE_AGENTS
from src.agent_runners.native.base import agent_venv_python
from src.attacks.samples import collect_all_samples, export_manifest
from src.evaluation.reporting import build_summary, extract_agent_fields, jsonl_to_csv, markov_chain, write_csv, write_json
from src.evaluation.sanity_check import check_batch, check_single_row

RESULT_ROOT = ROOT.parent / "MCP_result"
BATCH_CHECK_SIZE = int(os.getenv("MCP_EVAL_BATCH_CHECK", "6"))


def _child_env() -> dict[str, str]:
    """子进程环境：DeepSeek API + UTF-8。"""
    ds = load_deepseek_env()
    env = os.environ.copy()
    env["DEEPSEEK_API_KEY"] = ds["api_key"]
    env["DEEPSEEK_API_BASE"] = ds["base_url"]
    env["DEEPSEEK_MODEL"] = ds["model"]
    env["OPENAI_API_KEY"] = ds["api_key"]
    env["OPENAI_BASE_URL"] = f"{ds['base_url']}/v1"
    env["OTEL_SDK_DISABLED"] = "true"
    env["CREWAI_DISABLE_TELEMETRY"] = "true"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def run_one(agent_id: str, payload: dict, *, sanitized: bool) -> dict:
    """在 agents/{id}/venv 子进程中调用 worker_native。"""
    py = agent_venv_python(agent_id)
    worker = ROOT / "src" / "agent_runners" / "worker_native.py"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(payload, tf, ensure_ascii=False)
        payload_path = tf.name
    out_path = payload_path + ".out.json"
    t0 = time.perf_counter()
    cmd = [str(py), str(worker), "--agent", agent_id, "--payload", payload_path, "--output", out_path]
    if sanitized:
        cmd.append("--sanitized")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(os.getenv("MCP_EVAL_TIMEOUT_SEC", "300")),
            cwd=str(ROOT),
            env=_child_env(),
        )
        latency = int((time.perf_counter() - t0) * 1000)
        if not Path(out_path).is_file():
            return {
                "agent_error": True,
                "invoke_path": "subprocess_fail",
                "error_message": (proc.stderr or proc.stdout or f"exit {proc.returncode}")[:2000],
                "latency_ms": latency,
            }
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        data["latency_ms"] = data.get("latency_ms") or latency
        return data
    except subprocess.TimeoutExpired:
        return {
            "agent_error": True,
            "invoke_path": "timeout",
            "error_message": "timeout",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
        }
    except Exception as e:
        return {
            "agent_error": True,
            "invoke_path": "error",
            "error_message": str(e),
            "latency_ms": int((time.perf_counter() - t0) * 1000),
        }
    finally:
        Path(payload_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)


def build_row(*, run_id: str, mode: str, agent_id: str, tier: str, case, result: dict) -> dict:
    """组装 CSV 行，含 invoke_path 标识原生调用链。"""
    tool_calls = result.get("tool_calls") or []
    audit = result.get("audit_log") or []
    chain = markov_chain(audit, bool(result.get("attack_success")), tool_calls)
    agent_fields = extract_agent_fields(result)
    return {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "agent_framework": agent_id,
        "agent_tier": tier,
        "invoke_path": result.get("invoke_path", ""),
        "sample_id": case.id,
        "sample_name": case.name,
        "attack_category": case.category,
        "attack_paradigm": case.paradigm,
        "attack_technique": case.technique,
        "impact_weight": case.impact_weight,
        "user_prompt": case.user_prompts[0],
        "sanitizer_threat_level": result.get("sanitizer_threat_level", ""),
        "sanitizer_would_block": result.get("sanitizer_would_block", False),
        "tool_invoked": bool(tool_calls),
        "attack_success": bool(result.get("attack_success")),
        "agent_refused": bool(result.get("refused")),
        "agent_ignored_poison": bool(result.get("ignored")),
        "agent_error": bool(result.get("agent_error")),
        "behavior_evidence": json.dumps(result.get("behavior_evidence") or {}, ensure_ascii=False),
        "latency_ms": result.get("latency_ms", ""),
        "error_message": result.get("error_message", ""),
        **agent_fields,
        **chain,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Native MCP poison evaluation")
    parser.add_argument("--agents", nargs="*", default=list(NATIVE_AGENTS))
    parser.add_argument("--samples", nargs="*", help="sample ids")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--mode", choices=["raw", "sanitized", "both"], default="raw")
    parser.add_argument("--no-batch-check", action="store_true")
    args = parser.parse_args()

    export_manifest()

    agents = [a for a in args.agents if a in NATIVE_AGENTS]
    if not agents:
        print("No native agents selected.", file=sys.stderr)
        sys.exit(1)

    cases = collect_all_samples()
    if args.samples:
        wanted = set(args.samples)
        cases = [c for c in cases if c.id in wanted]
    if args.limit > 0:
        cases = cases[: args.limit]

    modes = ["raw", "sanitized"] if args.mode == "both" else [args.mode]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    incr_dir = ROOT / "results" / "incremental"
    incr_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = incr_dir / f"mcp_eval_native_{run_id}.jsonl"
    csv_path = RESULT_ROOT / f"mcp_eval_native_full_{run_id}.csv"
    json_path = RESULT_ROOT / f"mcp_eval_native_full_{run_id}.json"

    rows: list[dict] = []
    flat_rows: list[dict] = []
    total = len(cases) * len(agents) * len(modes)
    idx = 0

    print(f"[NATIVE] run_id={run_id} cases={len(cases)} agents={agents} modes={modes} total={total}", flush=True)

    for mode in modes:
        sanitized = mode == "sanitized"
        for agent_id in agents:
            tier = "mcp" if agent_id in MCP_TIER_NATIVE else "fc"
            for case in cases:
                idx += 1
                payload = case.to_payload()
                print(f"[{idx}/{total}] {mode} {agent_id} {case.id}", flush=True)
                result = run_one(agent_id, payload, sanitized=sanitized)
                row = build_row(run_id=run_id, mode=mode, agent_id=agent_id, tier=tier, case=case, result=result)

                ok_row, msg_row = check_single_row(row, result)
                if not ok_row:
                    print(f"SANITY ROW FAIL: {msg_row}", flush=True)
                    sys.exit(2)

                flat_rows.append(row)
                rows.append({**row, "full_result": result})

                with jsonl_path.open("a", encoding="utf-8") as jf:
                    jf.write(json.dumps(row, ensure_ascii=False) + "\n")
                write_csv(csv_path, [row], append=True)

                sr = sum(1 for r in flat_rows if r["attack_success"]) / len(flat_rows)
                print(
                    f"  -> path={row.get('invoke_path')} success={row['attack_success']} "
                    f"tools={row['tool_call_names'] or '-'} ASR={sr:.0%}",
                    flush=True,
                )

                if not args.no_batch_check and len(flat_rows) >= BATCH_CHECK_SIZE and len(flat_rows) % BATCH_CHECK_SIZE == 0:
                    ok_batch, msg_batch = check_batch(flat_rows[-BATCH_CHECK_SIZE:])
                    print(f"BATCH CHECK: {msg_batch}", flush=True)
                    if not ok_batch:
                        print("STOP: batch sanity failed.", flush=True)
                        sys.exit(3)

    jsonl_to_csv(jsonl_path, csv_path)
    summary = build_summary(flat_rows)
    summary["run_id"] = run_id
    summary["experiment"] = "native_agent_sdk"
    write_json(json_path, rows, summary)

    summary_csv = RESULT_ROOT / f"mcp_eval_native_summary_{run_id}.csv"
    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        import csv

        fields = [
            ("agent_framework", "Agent framework (Agent框架)"),
            ("total_cases", "Total cases (总样本数)"),
            ("attack_success_count", "Success count (成功次数)"),
            ("ASR_agent", "ASR (攻击成功率)"),
            ("ASR_raw", "ASR raw (原始ASR)"),
            ("ASR_sanitized", "ASR sanitized (净化后ASR)"),
            ("DSR_independent", "DSR independent (独立防御成功率)"),
            ("refusal_rate", "Refusal rate (拒答率)"),
            ("error_rate", "Error rate (错误率)"),
        ]
        w = csv.DictWriter(f, fieldnames=[x[0] for x in fields])
        w.writerow({x[0]: x[1] for x in fields})
        for agent_id, s in summary["agents"].items():
            w.writerow({"agent_framework": agent_id, **s})

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")
    print(f"Summary: {summary_csv}")


if __name__ == "__main__":
    main()
