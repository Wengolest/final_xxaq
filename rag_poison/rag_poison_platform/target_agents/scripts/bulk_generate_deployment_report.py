"""Generate integrated deployment + experiment closure report."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import RESULTS_DIR, compute_summary, load_registry, save_registry

POOL_SUMMARY = RESULTS_DIR / "agent_sample_pool_summary.json"
POISON_SUMMARY = RESULTS_DIR / "poison_experiment_summary.json"
INSTALL_CSV = RESULTS_DIR / "bulk_agent_install_report.csv"
MATRIX_CSV = RESULTS_DIR / "poison_experiment_matrix.csv"
SHORTLIST_CSV = RESULTS_DIR / "external_agent_candidate_shortlist.csv"
PROBE_CSV = RESULTS_DIR / "external_agent_adapter_probe.csv"
EXT_SMOKE_CSV = RESULTS_DIR / "external_agent_poison_smoke.csv"


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _ in csv.reader(f)) - 1)


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _af_experiment_status() -> Dict[str, Any]:
    mock_csv = RESULTS_DIR / "mock_asr.csv"
    tool_csv = RESULTS_DIR / "tool_poison_mock.csv"
    return {
        "mock_asr": {
            "script": "runners/run_mock_asr.py",
            "output_csv": str(mock_csv),
            "exists": mock_csv.is_file(),
            "rows": _csv_rows(mock_csv),
            "summary": _load_json(RESULTS_DIR / "mock_asr.summary.json"),
        },
        "tool_poison_mock": {
            "script": "runners/run_tool_poison_mock.py",
            "output_csv": str(tool_csv),
            "exists": tool_csv.is_file(),
            "rows": _csv_rows(tool_csv),
            "summary": _load_json(RESULTS_DIR / "tool_poison_mock.summary.json"),
        },
        "note": "A-F 主实验输出固定为 mock_asr.csv / tool_poison_mock.csv，不覆盖历史文件",
    }


def _install_stats() -> Dict[str, Any]:
    if not INSTALL_CSV.is_file():
        return {}
    rows = _read_csv(INSTALL_CSV)
    return {
        "total": len(rows),
        "install_success": sum(1 for r in rows if str(r.get("install_success")).lower() == "true"),
        "install_skipped": sum(1 for r in rows if str(r.get("install_skipped")).lower() == "true"),
        "install_failed": sum(
            1
            for r in rows
            if str(r.get("install_attempted")).lower() == "true"
            and str(r.get("install_success")).lower() != "true"
        ),
    }


def _poison_matrix_section() -> Dict[str, Any]:
    data = _load_json(POISON_SUMMARY) or {}
    by_style = [s for s in data.get("summaries", []) if s.get("dimension") == "poison_trigger_style"]
    overall = next((s for s in data.get("summaries", []) if s.get("dimension_value") == "overall"), {})
    return {
        "matrix_rows": data.get("matrix_row_count", _csv_rows(MATRIX_CSV)),
        "case_validation": data.get("case_validation", {}),
        "overall_metrics": overall,
        "by_poison_trigger_style": by_style,
        "by_model_backend": [s for s in data.get("summaries", []) if s.get("dimension") == "model_backend"],
        "by_retrieval_profile": [s for s in data.get("summaries", []) if s.get("dimension") == "retrieval_profile"],
        "by_retrieval_top_k": [s for s in data.get("summaries", []) if s.get("dimension") == "retrieval_top_k"],
        "by_corpus_domain": [s for s in data.get("summaries", []) if s.get("dimension") == "corpus_domain"],
        "metric_note": "检索层命中 != 生成层污染；见 poison_experiment_report.md",
    }


def _experiment_scope_counts(agents: list, pool_summary: dict | None) -> Dict[str, Any]:
    pool = pool_summary or {}
    matrix_rows = _read_csv(MATRIX_CSV)
    local_matrix_ids: Set[str] = {
        r["agent_id"]
        for r in matrix_rows
        if r.get("sample_type") == "local_variant" and r.get("agent_id")
    }

    external_agents = [
        a for a in agents if a.get("sample_type") == "external_github_agent" or (
            not a.get("local_variant") and a.get("clone_success") and not a.get("id", "").startswith("local_")
        )
    ]
    deployed_external = sum(
        1 for a in external_agents if str(a.get("startup_success")).lower() == "true"
    )

    probe_rows = _read_csv(PROBE_CSV)
    rag_loop = sum(1 for r in probe_rows if str(r.get("rag_loop_supported")).lower() == "true")
    probe_started = sum(
        1 for r in probe_rows if str(r.get("started")).lower() == "true" or str(r.get("health_ok")).lower() == "true"
    )

    ext_smoke = _read_csv(EXT_SMOKE_CSV)
    poison_tested_external_ids: Set[str] = set()
    for r in ext_smoke:
        aid = r.get("agent_id", "")
        if not aid or aid == "_none_":
            continue
        if r.get("phase", "").startswith("query") and r.get("status") == "ok":
            poison_tested_external_ids.add(aid)

    effective = _load_json(RESULTS_DIR / "github_external_agent_effective_summary.json") or {}
    if not effective:
        effective = _load_json(RESULTS_DIR / "github_http_rag_poison_effective_summary.json") or {}
    for aid in effective.get("external_poison_loop_complete_agents", []):
        if aid != "minimal_http_rag_agent":
            poison_tested_external_ids.add(aid)

    github_matrix_rows = _csv_rows(RESULTS_DIR / "github_http_rag_poison_matrix.csv")
    file_matrix_rows = _csv_rows(RESULTS_DIR / "file_based_agent_poison_matrix.csv")
    sidecar_matrix_rows = _csv_rows(RESULTS_DIR / "compat_sidecar_agent_poison_matrix.csv")

    local_registered = _csv_rows(RESULTS_DIR / "local_rag_variants.csv") or (pool or {}).get("by_sample_type", {}).get("local_variant", 20)

    return {
        "sample_pool_count": pool.get("total_samples", _csv_rows(RESULTS_DIR / "agent_sample_pool.csv")),
        "local_variant_registered_count": local_registered,
        "local_variant_matrix_rows": _csv_rows(MATRIX_CSV),
        "deployed_external_agent_count": deployed_external,
        "poison_tested_local_variant_count": len(local_matrix_ids),
        "poison_tested_external_agent_count": effective.get("total_external_poison_tested_count", len(poison_tested_external_ids)),
        "native_http_poison_tested_count": effective.get("native_http_poison_tested_count", 0),
        "native_http_effective_rows": sum(
            1 for p in effective.get("per_agent", [])
            if p.get("adapter_category") == "A_native_http_rag" and p.get("success_rows", 0) > 0
        ),
        "file_based_poison_tested_count": effective.get("file_based_poison_tested_count", 0),
        "file_based_effective_rows": file_matrix_rows,
        "compat_sidecar_poison_tested_count": effective.get("compat_sidecar_poison_tested_count", 0),
        "compat_sidecar_effective_rows": sidecar_matrix_rows,
        "total_external_poison_tested_count": effective.get("total_external_poison_tested_count", len(poison_tested_external_ids)),
        "external_agent_candidate_count": _csv_rows(SHORTLIST_CSV),
        "external_agent_adapter_probe_count": len(probe_rows),
        "external_agent_rag_loop_supported_count": rag_loop,
        "external_agent_poison_tested_count": effective.get("total_external_poison_tested_count", len(poison_tested_external_ids)),
        "github_http_matrix_runner_covered_agents": effective.get("native_http_poison_tested_count", github_matrix_rows // 45 if github_matrix_rows else 0),
        "github_http_matrix_effective_rows": effective.get("effective_poison_rows", 0),
        "external_poison_loop_complete_agents": effective.get("external_poison_loop_complete_agents", []),
        "native_http_complete_agents": effective.get("native_http_effective_complete", []),
        "file_based_complete_agents": effective.get("file_based_effective_complete", []),
        "compat_sidecar_complete_agents": effective.get("compat_sidecar_effective_complete", []),
        "formal_matrix_sample_type": "local_variant_only",
        "local_matrix_agent_ids": sorted(local_matrix_ids),
    }


def _external_zero_reasons(scope: Dict[str, Any], probe_rows: List[Dict[str, str]]) -> List[str]:
    if scope["external_agent_poison_tested_count"] > 0:
        return []
    reasons = []
    if scope["deployed_external_agent_count"] == 0:
        reasons.append("无外部 Agent 在 registry 中标记 startup_success=true")
    if scope["external_agent_rag_loop_supported_count"] == 0:
        reasons.append("adapter 探测未找到 health+ingest+query 完整 RAG 闭环")
    err_types = {r.get("error_type", "") for r in probe_rows if r.get("error_type")}
    if "start_failed" in err_types or "health_failed" in err_types:
        reasons.append("启动失败或健康检查未通过（入口/依赖/端口不统一）")
    if "no_ingest" in err_types:
        reasons.append("多数外部项目无标准 documents/upload/ingest 接口")
    if "no_query" in err_types:
        reasons.append("query/chat/invoke 接口格式不统一，adapter 难以通用对接")
    reasons.append("部分项目依赖 Tavily/Azure/Mintlify 等外部服务，DeepSeek-only 环境无法完整运行")
    reasons.append("Windows/Linux 编译与 venv 路径差异导致 install_success 不等于可启动")
    reasons.append("不少仓库是框架/教程而非完整可投毒 RAG Agent")
    return reasons


def build_report_md(
    summary: dict,
    agents: list,
    pool_summary: dict | None,
    af_status: dict,
    install_stats: dict,
    poison_section: dict,
    scope: dict,
) -> str:
    pool = pool_summary or {}
    pool_complete = pool.get("pool_complete", False)
    by_type = pool.get("by_sample_type", {})
    probe_rows = _read_csv(PROBE_CSV)
    zero_reasons = _external_zero_reasons(scope, probe_rows)

    api_dep = [
        a
        for a in agents
        if a.get("sample_type") == "api_dependent_agent"
        or a.get("external_service_missing")
        or a.get("status") == "install_success_but_external_service_missing"
    ]
    overall_p = poison_section.get("overall_metrics", {})

    lines = [
        "# 多源异构 Agent 实验闭环报告",
        "",
        "> clone ≠ 部署成功；smoke ≠ 完整 ASR；检索命中 ≠ 回答污染。",
        "> API 策略：仅 `DEEPSEEK_API_KEY`（OpenAI-compat 外层映射）。",
        "> **正式投毒矩阵仅覆盖 local_variant，不包含 external_github_agent。**",
        "",
        "## 1. A–F 主实验状态",
        "",
        "| 实验 | 脚本 | 输出 CSV | 状态 | 行数 |",
        "|------|------|---------|------|------|",
    ]
    for key in ("mock_asr", "tool_poison_mock"):
        s = af_status[key]
        status = "已运行" if s["exists"] and s["rows"] > 0 else "未运行/缺失"
        lines.append(
            f"| {key} | `{s['script']}` | `{Path(s['output_csv']).name}` | {status} | {s['rows']} |"
        )
    lines += [
        "",
        "A–F 是基础主实验，保证原平台主线完整；本报告不修改其逻辑与历史 CSV。",
        "",
        "## 2. 样本池与实验口径（重要）",
        "",
        "| 指标 | 值 | 说明 |",
        "|------|-----|------|",
        f"| sample_pool_count | {scope['sample_pool_count']} | 样本池总条目（含 external / api_dependent / local_variant） |",
        f"| deployed_external_agent_count | {scope['deployed_external_agent_count']} | 真实启动成功的外部 GitHub Agent |",
        f"| local_variant_registered_count | {scope.get('local_variant_registered_count', 20)} | 样本池登记的 local RAG variant 总数 |",
        f"| poison_tested_local_variant_count | **{scope['poison_tested_local_variant_count']}** | 正式投毒矩阵实际运行的 variant 数 |",
        f"| poison_tested_external_agent_count | **{scope['poison_tested_external_agent_count']}** | 完成投毒闭环的外部 Agent 数（不含 duplicate） |",
        f"| native_http_poison_tested_count | {scope.get('native_http_poison_tested_count', 0)} | 外部 native HTTP RAG 测试数 |",
        f"| file_based_poison_tested_count | {scope.get('file_based_poison_tested_count', 0)} | 外部 file-based RAG 测试数 |",
        f"| compat_sidecar_poison_tested_count | {scope.get('compat_sidecar_poison_tested_count', 0)} | 外部 compat sidecar 测试数 |",
        f"| total_external_poison_tested_count | **{scope.get('total_external_poison_tested_count', 0)}** | 有效闭环 external 总数 |",
        f"| github_http_matrix_effective_rows | {scope.get('github_http_matrix_effective_rows', 'N/A')} | 有效投毒行数（有 answer 且无 error） |",
        "",
        f"- **native_http_complete**: {', '.join(scope.get('native_http_complete_agents', [])) or '无'}",
        f"- **file_based_complete**: {', '.join(scope.get('file_based_complete_agents', [])) or '无'}",
        f"- **compat_sidecar_complete**: {', '.join(scope.get('compat_sidecar_complete_agents', [])) or '无'}",
        f"- **external_poison_loop_complete (all)**: {', '.join(scope.get('external_poison_loop_complete_agents', [])) or '无'}",
        f"- **pool_complete** = {pool_complete}",
        f"- external_github_agent（池内）= {by_type.get('external_github_agent', 'N/A')}",
        f"- api_dependent_agent = {by_type.get('api_dependent_agent', 'N/A')}",
        f"- local_variant = {by_type.get('local_variant', 'N/A')}",
        f"- poison_test_supported（池定义）= {pool.get('poison_test_supported_count', 'N/A')}（均来自 local_variant）",
        "",
        "**口径说明**：`sample_pool_count` 不等于投毒测试 Agent 数。"
        f"样本池登记 **{scope.get('local_variant_registered_count', 20)} 个 local_variant**（poison_test_supported），"
        f"正式矩阵当前运行 **{scope['poison_tested_local_variant_count']} 个代表 variant**（4 模型×检索组合子集）。"
        "external_github_agent 当前仅用于候选筛选与可部署性分析，不计入正式投毒定量。",
        "",
        "## 3. 外部 Agent 筛选（部署可行性，非正式投毒）",
        "",
        f"| 指标 | 数量 |",
        f"|------|------|",
        f"| candidate_count | {summary['candidate_count']} |",
        f"| clone_success | {summary['clone_success_count']} |",
        f"| install_success | {summary['install_success_count']} |",
        f"| install_failed | {install_stats.get('install_failed', 'N/A')} |",
        f"| install_skipped | {install_stats.get('install_skipped', 'N/A')} |",
        f"| api_dependent (registry) | {summary.get('api_dependent_count', 0)} |",
        f"| external_service_missing | {len(api_dep)} |",
        "",
        "外部不足原因：其他 LLM Key、Mintlify/Pylon、Windows 编译失败、入口不统一、大型平台 too_heavy。",
        "",
        "## 4. 本地 RAG 变体（正式投毒主体）",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| local_variant 登记数 | {by_type.get('local_variant', _csv_rows(RESULTS_DIR / 'local_rag_variants.csv'))} |",
        f"| 正式矩阵覆盖 variant 数 | **{scope['poison_tested_local_variant_count']}** |",
        f"| poison smoke 记录 | {_csv_rows(RESULTS_DIR / 'bulk_agent_poison_smoke_test.csv')} |",
        "",
        "local_variant 基于 minimal_http_rag_agent；model_backend=mock/deepseek；**不伪装**为外部 GitHub Agent。",
        "",
        "## 5. 正式投毒矩阵（四类投毒，仅 local_variant）",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| matrix 总行数 | {poison_section.get('matrix_rows', 0)} |",
        f"| matrix sample_type | **{scope['formal_matrix_sample_type']}** |",
        f"| case 数 | {poison_section.get('case_validation', {}).get('total_cases', 'N/A')} |",
        f"| 四类齐全 | {poison_section.get('case_validation', {}).get('styles_complete', False)} |",
        "",
        "### Overall 指标（主结论，local_variant）",
        "",
        f"| 指标 | 值 | 层级 |",
        f"|------|-----|------|",
        f"| poison_retrieval_hit_rate | {overall_p.get('poison_retrieval_hit_rate', 'N/A')} | 检索 |",
        f"| poison_answer_keyword_hit_rate | {overall_p.get('poison_answer_keyword_hit_rate', 'N/A')} | 生成-关键词 |",
        f"| poison_strict_attack_success_rate | {overall_p.get('poison_strict_attack_success_rate', 'N/A')} | 生成-严格 |",
        f"| clean_query_poison_retrieval_rate | {overall_p.get('clean_query_poison_retrieval_rate', 'N/A')} | clean检索 |",
        f"| clean_query_answer_keyword_contamination_rate | {overall_p.get('clean_query_answer_keyword_contamination_rate', 'N/A')} | clean关键词 |",
        f"| clean_query_strict_contamination_rate | {overall_p.get('clean_query_strict_contamination_rate', 'N/A')} | clean严格 |",
        "",
        "关键词命中 = 污染措辞进入回答；严格攻击成功 = `attack_success=true` 最终判断被翻转。",
        "",
        f"| legacy 指标 | 值 | 说明 |",
        f"|-------------|-----|------|",
        f"| poison_answer_success_rate_legacy | {overall_p.get('poison_answer_success_rate_legacy', 'N/A')} | 旧混合口径，不作主结论 |",
        "",
        "### 按 poison_trigger_style",
        "",
        "| style | retrieval | keyword_hit | strict_attack | clean_kw | clean_strict |",
        "|-------|-----------|-------------|---------------|----------|--------------|",
    ]
    for r in poison_section.get("by_poison_trigger_style", []):
        lines.append(
            f"| {r.get('dimension_value')} | {r.get('poison_retrieval_hit_rate')} | "
            f"{r.get('poison_answer_keyword_hit_rate')} | {r.get('poison_strict_attack_success_rate')} | "
            f"{r.get('clean_query_answer_keyword_contamination_rate')} | "
            f"{r.get('clean_query_strict_contamination_rate')} |"
        )

    lines += [
        "",
        "## 6. 外部真实 Agent 实测状态",
        "",
        f"| 指标 | 值 |",
        f"|------|-----|",
        f"| external_agent_candidate_count | {scope['external_agent_candidate_count']} |",
        f"| external_agent_adapter_probe_count | {scope['external_agent_adapter_probe_count']} |",
        f"| external_agent_rag_loop_supported_count | {scope['external_agent_rag_loop_supported_count']} |",
        f"| external_agent_poison_tested_count | **{scope['external_agent_poison_tested_count']}** |",
        "",
        "shortlist 来源：`results/external_agent_candidate_shortlist.csv`",
        "adapter 探测：`results/external_agent_adapter_probe.csv`",
        "最小投毒 smoke：`results/external_agent_poison_smoke.csv`",
        "",
    ]
    if scope["external_agent_poison_tested_count"] == 0:
        lines.append("**当前外部 Agent 正式投毒测试数 = 0。** 原因包括：")
        for reason in zero_reasons:
            lines.append(f"- {reason}")
        lines.append("")

    if probe_rows:
        lines += ["### Adapter 探测明细", "", "| agent_id | health | ingest | query | rag_loop | error |", "|----------|--------|--------|-------|----------|-------|"]
        for r in probe_rows:
            lines.append(
                f"| {r.get('agent_id')} | {r.get('health_ok')} | {r.get('ingest_supported')} | "
                f"{r.get('query_supported')} | {r.get('rag_loop_supported')} | {r.get('error_type') or '-'} |"
            )
        lines.append("")

    lines += [
        "## 7. 关键实验结论",
        "",
        "1. **A–F** 是基础主实验，保证原平台主线完整。",
        f"2. **local_variant 正式矩阵**已完成（{scope['poison_tested_local_variant_count']} variants），可作为**主要定量结果**。",
        "3. **external_github_agent** 当前是部署可行性分析；只有通过 adapter 并完成 ingest/query/poison 闭环的才算真实投毒测试。",
        f"4. 当前 external 真实投毒测试数 = **{scope['external_agent_poison_tested_count']}**（与 local_variant 分开统计）。",
        "5. **API依赖型 Agent** 受 DeepSeek 单一 Key / 外部服务缺失影响，不纳入 poison_test_supported。",
        "6. **四类投毒**已进入正式矩阵（local_variant only），不再只是 smoke。",
        "7. **检索命中 ≠ 关键词命中 ≠ 严格攻击成功**；主结论看 `poison_strict_attack_success_rate`。",
        "",
        "## 8. 相关文件",
        "",
        "- `results/agent_sample_pool.csv`",
        "- `results/poison_experiment_matrix.csv`",
        "- `results/poison_experiment_report.md`",
        "- `results/external_agent_candidate_shortlist.csv`",
        "- `results/external_agent_adapter_probe.csv`",
        "- `results/external_agent_poison_smoke.csv`",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    reg = load_registry()
    summary = compute_summary(reg)
    pool_summary = _load_json(POOL_SUMMARY)
    af_status = _af_experiment_status()
    install_stats = _install_stats()
    poison_section = _poison_matrix_section()
    scope = _experiment_scope_counts(reg.get("agents", []), pool_summary)

    payload = {
        **summary,
        "experiment_scope": scope,
        "pool_summary": pool_summary,
        "af_experiments": af_status,
        "install_stats": install_stats,
        "poison_matrix": poison_section,
        "smoke_rows": _csv_rows(RESULTS_DIR / "bulk_agent_poison_smoke_test.csv"),
        "local_variant_rows": _csv_rows(RESULTS_DIR / "local_rag_variants.csv"),
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "bulk_agent_deployment_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RESULTS_DIR / "bulk_agent_deployment_report.md").write_text(
        build_report_md(
            summary, reg.get("agents", []), pool_summary, af_status, install_stats, poison_section, scope
        ),
        encoding="utf-8",
    )
    save_registry(reg)
    print("Wrote bulk_agent_deployment_summary.json and bulk_agent_deployment_report.md")
    print(
        f"scope: local_poison={scope['poison_tested_local_variant_count']} "
        f"external_poison={scope['poison_tested_external_agent_count']}"
    )


if __name__ == "__main__":
    main()
