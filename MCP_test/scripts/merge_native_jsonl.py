"""合并多段 native 实验 JSONL，重建 300 行 CSV / summary / JSON。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.reporting import build_summary, jsonl_to_csv, write_json

RESULT_ROOT = ROOT.parent / "MCP_result"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="输出批次 ID，如 20260608_171706")
    parser.add_argument("jsonl", nargs="+", help="按顺序合并的 jsonl 路径")
    args = parser.parse_args()

    rows: list[dict] = []
    for p in args.jsonl:
        path = Path(p)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row["run_id"] = args.run_id
                rows.append(row)

    incr = ROOT / "results" / "incremental"
    incr.mkdir(parents=True, exist_ok=True)
    merged_jl = incr / f"mcp_eval_native_{args.run_id}_merged.jsonl"
    with merged_jl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_path = RESULT_ROOT / f"mcp_eval_native_full_{args.run_id}.csv"
    json_path = RESULT_ROOT / f"mcp_eval_native_full_{args.run_id}.json"
    summary_csv = RESULT_ROOT / f"mcp_eval_native_summary_{args.run_id}.csv"

    jsonl_to_csv(merged_jl, csv_path)
    summary = build_summary(rows)
    summary["run_id"] = args.run_id
    summary["experiment"] = "native_agent_sdk"
    write_json(json_path, [{**r} for r in rows], summary)

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
    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=[x[0] for x in fields])
        w.writerow({x[0]: x[1] for x in fields})
        for agent_id, s in summary["agents"].items():
            w.writerow({"agent_framework": agent_id, **s})

    print(f"merged_rows={len(rows)}")
    print(f"CSV: {csv_path}")
    print(f"Summary: {summary_csv}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
