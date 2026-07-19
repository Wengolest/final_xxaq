"""
合并 outputs/agent_chain_poison/ 下所有 agent_chain_poison_*.csv 结果。

用法:
  python -m runners.merge_agent_chain_poison_results
"""

from __future__ import annotations

import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from agent_chain_poison.evaluator import aggregate_summary
from runners.run_agent_chain_poison import CSV_FIELDS

DEFAULT_OUTPUT_DIR = PLATFORM_ROOT / "outputs" / "agent_chain_poison"
MERGED_CSV_NAME = "agent_chain_poison_merged_results.csv"
MERGED_MD_NAME = "agent_chain_poison_merged_summary.md"

RUN_ID_RE = re.compile(
    r"^agent_chain_poison_(\d{8}_\d{6})_[0-9a-f]{8}$",
    re.IGNORECASE,
)

# 新格式 case_id 前缀 -> poison_type
NEW_CASE_PREFIX = {
    "logical_rule": "logical_rule_injection",
    "priority_shift": "priority_shift_injection",
    "step_order": "step_order_hijack",
    "evidence_suppression": "evidence_suppression",
    "autonomous_action": "autonomous_action_drift",
}

# 旧格式 acp_ 前缀 -> poison_type，全局序号偏移
LEGACY_PREFIX_OFFSET = {
    "logi": ("logical_rule_injection", 0),
    "prio": ("priority_shift_injection", 20),
    "step": ("step_order_hijack", 40),
    "evid": ("evidence_suppression", 60),
    "auto": ("autonomous_action_drift", 80),
}


def _is_new_format_case_id(case_id: str) -> bool:
    return any(case_id.startswith(f"{prefix}_") for prefix in NEW_CASE_PREFIX)


def _canonical_slot(row: Dict[str, Any]) -> Optional[tuple[str, int]]:
    """将新旧 case_id 映射为 (poison_type, slot_1..20)。"""
    case_id = (row.get("case_id") or "").strip()
    poison_type = (row.get("poison_type") or "").strip()
    if not case_id or not poison_type:
        return None

    for prefix, pt in NEW_CASE_PREFIX.items():
        if case_id.startswith(f"{prefix}_"):
            try:
                slot = int(case_id.rsplit("_", 1)[-1])
            except ValueError:
                return None
            if pt == poison_type and 1 <= slot <= 20:
                return pt, slot
            return None

    if case_id.startswith("acp_"):
        parts = case_id.split("_")
        if len(parts) < 4:
            return None
        legacy_key = parts[1]
        mapping = LEGACY_PREFIX_OFFSET.get(legacy_key)
        if not mapping:
            return None
        pt, offset = mapping
        if pt != poison_type:
            return None
        try:
            global_num = int(parts[-1])
        except ValueError:
            return None
        slot = global_num - offset
        if 1 <= slot <= 20:
            return pt, slot

    return None


def _row_sort_key(row: Dict[str, Any]) -> tuple:
    """去重优先级：最新 run_id > 新格式 case_id > 旧格式。"""
    run_ts = _run_id_sort_key(str(row.get("run_id", "")))
    new_fmt = 1 if _is_new_format_case_id(str(row.get("case_id", ""))) else 0
    return (run_ts, new_fmt)


def _run_id_sort_key(run_id: str) -> datetime:
    match = RUN_ID_RE.match(run_id or "")
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
        except ValueError:
            pass
    return datetime.min


def _discover_csv_files(output_dir: Path) -> List[Path]:
    files = sorted(output_dir.glob("agent_chain_poison_*.csv"))
    merged = output_dir / MERGED_CSV_NAME
    return [p for p in files if p.resolve() != merged.resolve()]


def _read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _dedupe_by_latest_run_id(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按 (poison_type, slot) 去重，兼容新旧 case_id；同 slot 保留最新且优先新格式。"""
    best: Dict[tuple[str, int], Dict[str, Any]] = {}
    fallback: Dict[str, Dict[str, Any]] = {}

    for row in rows:
        case_id = (row.get("case_id") or "").strip()
        if not case_id:
            continue
        slot_key = _canonical_slot(row)
        if slot_key is not None:
            current = best.get(slot_key)
            if current is None or _row_sort_key(row) >= _row_sort_key(current):
                best[slot_key] = row
            continue

        current = fallback.get(case_id)
        if current is None or _row_sort_key(row) >= _row_sort_key(current):
            fallback[case_id] = row

    merged = list(best.values()) + [
        row for cid, row in fallback.items()
        if not any((row.get("case_id") or "").strip() == (b.get("case_id") or "").strip() for b in best.values())
    ]
    return sorted(merged, key=lambda r: (r.get("poison_type", ""), r.get("case_id", "")))


def _render_merged_summary_md(
    summary: Dict[str, Any],
    *,
    source_files: List[Path],
    deduped_count: int,
    raw_count: int,
) -> str:
    lines = [
        "# Agent Chain Poison 合并实验报告",
        "",
        "## 1. 合并概览",
        "",
        f"- 源 CSV 文件数: **{len(source_files)}**",
        f"- 原始记录数: **{raw_count}**",
        f"- 去重后样本数: **{deduped_count}**",
        f"- 有效样本数: **{summary['valid_cases']}**",
        f"- 失败样本数: **{summary['error_cases']}**",
        f"- 总 strict_success_rate: **{summary['strict_success_rate']:.2%}**",
        f"- reasoning_shift_rate: **{summary['reasoning_shift_rate']:.2%}**",
        f"- decision_shift_rate: **{summary['decision_shift_rate']:.2%}**",
        f"- risk_downgrade_rate: **{summary['risk_downgrade_rate']:.2%}**",
        f"- autonomous_action_rate: **{summary['autonomous_action_rate']:.2%}**",
        "",
        "## 2. 源文件列表",
        "",
    ]
    for path in source_files:
        lines.append(f"- `{path.name}`")
    lines.extend([
        "",
        "## 3. 按 poison_type 分组统计",
        "",
        "| poison_type | total | reasoning_shift | decision_shift | risk_downgrade | autonomous_action | strict_success |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for pt, stats in summary.get("by_poison_type", {}).items():
        lines.append(
            f"| {pt} | {stats['total']} "
            f"| {stats['reasoning_shift_rate']:.2%} "
            f"| {stats['decision_shift_rate']:.2%} "
            f"| {stats['risk_downgrade_rate']:.2%} "
            f"| {stats['autonomous_action_rate']:.2%} "
            f"| {stats['strict_success_rate']:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)


def merge_results(
    *,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    out_dir = output_dir or DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    source_files = _discover_csv_files(out_dir)
    if not source_files:
        raise RuntimeError(f"No source CSV files found in {out_dir}")

    all_rows: List[Dict[str, Any]] = []
    for path in source_files:
        all_rows.extend(_read_csv_rows(path))

    raw_count = len(all_rows)
    merged_rows = _dedupe_by_latest_run_id(all_rows)
    summary = aggregate_summary(merged_rows)

    merged_csv = out_dir / MERGED_CSV_NAME
    merged_md = out_dir / MERGED_MD_NAME

    with merged_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged_rows)

    merged_md.write_text(
        _render_merged_summary_md(
            summary,
            source_files=source_files,
            deduped_count=len(merged_rows),
            raw_count=raw_count,
        ),
        encoding="utf-8",
    )

    print(f"Source CSV files: {len(source_files)}")
    print(f"Raw rows: {raw_count}")
    print(f"Merged unique cases: {len(merged_rows)}")
    print(f"Total strict_success_rate: {summary['strict_success_rate']:.2%}")
    print()
    print("By poison_type:")
    for pt, stats in summary.get("by_poison_type", {}).items():
        print(
            f"  {pt}: total={stats['total']} "
            f"reasoning_shift={stats['reasoning_shift_rate']:.2%} "
            f"decision_shift={stats['decision_shift_rate']:.2%} "
            f"risk_downgrade={stats['risk_downgrade_rate']:.2%} "
            f"autonomous_action={stats['autonomous_action_rate']:.2%} "
            f"strict_success={stats['strict_success_rate']:.2%}"
        )
    print()
    print(f"Wrote merged CSV -> {merged_csv}")
    print(f"Wrote merged summary -> {merged_md}")

    return {
        "merged_csv": merged_csv,
        "merged_md": merged_md,
        "summary": summary,
        "merged_rows": merged_rows,
    }


def main() -> None:
    merge_results()


if __name__ == "__main__":
    main()
