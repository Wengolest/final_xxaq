"""
Build per-agent failure diagnosis and recovery plan from matrix CSV + registry + inspect/install reports.
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
PLATFORM_ROOT = SCRIPT_DIR.parent.parent
RESULTS = PLATFORM_ROOT / "results"
MATRIX_CSV = RESULTS / "github_http_rag_poison_matrix.csv"
SUMMARY_JSON = RESULTS / "github_http_rag_poison_matrix.summary.json"
INSPECT_CSV = RESULTS / "bulk_agent_inspect_report.csv"
INSTALL_CSV = RESULTS / "bulk_agent_install_report.csv"
PROBE_CSV = RESULTS / "bulk_agent_poison_probe.csv"
BULK_REGISTRY = SCRIPT_DIR.parent / "bulk_registry.yaml"
REGISTRY = SCRIPT_DIR.parent / "registry.yaml"
MANIFEST = SCRIPT_DIR.parent / "bulk_agent_poison_manifest.yaml"

OUT_CSV = RESULTS / "github_agent_failure_diagnosis.csv"
OUT_MD = RESULTS / "github_agent_recovery_plan.md"

KB_DIRS = ("data", "docs", "documents", "kb", "knowledge", "source_documents", "uploads", "knowledge_base")
INDEX_SCRIPTS = ("ingest.py", "build_index.py", "create_index.py", "load_docs.py", "index.py")

CSV_FIELDS = [
    "agent_id",
    "total_rows",
    "success_rows",
    "failed_rows",
    "main_error_type",
    "service_started",
    "health_ok",
    "has_query_endpoint",
    "has_ingest_endpoint",
    "has_file_corpus_dir",
    "has_index_build_script",
    "requires_docker",
    "requires_redis",
    "requires_postgres",
    "requires_external_api",
    "adapter_category",
    "recovery_action",
    "fix_priority",
    "notes",
]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _resolve_repo(agent_id: str, bulk: Dict, reg: Dict) -> Path:
    for entry in bulk.get("agents", []):
        if entry.get("id") == agent_id:
            lp = entry.get("local_path", "")
            if lp and Path(lp).is_dir():
                return Path(lp)
            alt = Path(r"D:\AI\target_agents_bulk") / agent_id / "repo"
            if alt.is_dir():
                return alt
    for entry in reg.get("agents", []):
        if entry.get("id") == agent_id:
            lp = entry.get("local_path", "")
            if lp and Path(lp).is_dir():
                return Path(lp)
    return Path("")


def _scan_repo(repo: Path) -> Dict[str, Any]:
    if not repo.is_dir():
        return {"has_file_corpus_dir": False, "has_index_build_script": False, "corpus_dirs": []}
    corpus_dirs = [d for d in KB_DIRS if (repo / d).is_dir()]
    for sub in repo.rglob("*"):
        if sub.is_dir() and sub.name in KB_DIRS and str(sub.relative_to(repo)).count("\\") < 4:
            if sub.name not in corpus_dirs:
                corpus_dirs.append(str(sub.relative_to(repo)).replace("\\", "/"))
    scripts = [s for s in INDEX_SCRIPTS if (repo / s).is_file()]
    lc = ""
    for p in list(repo.rglob("*.py"))[:200] + list(repo.rglob("README*"))[:5]:
        try:
            if p.stat().st_size < 100_000:
                lc += p.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            pass
    return {
        "has_file_corpus_dir": bool(corpus_dirs),
        "corpus_dirs": corpus_dirs[:5],
        "has_index_build_script": bool(scripts),
        "index_scripts": scripts,
        "requires_redis": "redis" in lc,
        "requires_postgres": any(x in lc for x in ("postgres", "pgvector", "sqlalchemy")),
        "requires_docker": bool(list(repo.rglob("docker-compose*"))) or "docker-compose" in lc,
    }


def _normalize_error(err: str) -> str:
    if not err or err == "OK":
        return ""
    e = err.strip()
    if e.startswith("service_unreachable"):
        return "port_not_listening"
    if e.startswith("probe_failed"):
        return "adapter_probe_config_error"
    if "no_ingest_path" in e:
        return "adapter_ingest_path_missing"
    if e.startswith("ingest_failed"):
        return "adapter_ingest_http_failed"
    if "missing" in e and ("question" in e or "message" in e or "report" in e or "body" in e):
        return "adapter_query_field_mismatch"
    if e.startswith("query_failed"):
        if "Error loading" in e or "500" in e:
            return "adapter_query_runtime_error"
        return "adapter_query_field_mismatch"
    return "other_failure"


def _infer_service_state(
    agent_id: str,
    rows: List[Dict[str, str]],
    probe: Dict[str, str],
    bulk_entry: Dict[str, Any],
) -> Tuple[bool, bool]:
    errs = [r.get("error", "") for r in rows]
    has_success = any(not r.get("error") and r.get("answer") for r in rows)
    if has_success:
        return True, True
    if any(e.startswith("query_failed") or e.startswith("ingest_failed") for e in errs if e):
        return True, True
    if probe.get("health_ok", "").lower() == "true":
        return True, True
    if bulk_entry.get("startup_success"):
        return True, True
    if probe.get("query_ok", "").lower() == "true":
        return True, probe.get("health_ok", "").lower() == "true"
    return False, False


def _classify_adapter(
    agent_id: str,
    manifest: Dict[str, Any],
    inspect: Dict[str, str],
    repo_scan: Dict[str, Any],
    service_started: bool,
    has_query: bool,
    has_ingest: bool,
    main_error: str,
    success_rows: int,
) -> Tuple[str, str, int]:
    mf = manifest.get(agent_id, {})
    tier = mf.get("tier", "")
    notes = mf.get("notes", "")

    if success_rows >= 15:
        return "A_native_http_rag", "native_http: rerun full matrix or scale up", 1

    native_ingest = has_ingest or bool(mf.get("ingest_endpoint")) or bool(inspect.get("ingest_endpoint"))
    native_query = has_query or bool(mf.get("chat_endpoint")) or bool(inspect.get("query_endpoint"))

    if tier == "skip" or agent_id in ("llama_index", "chat-langchain", "openhands"):
        return "D_not_suitable", "not_suitable: deployability analysis only", 99

    if agent_id == "rag-fastapi-chatbot":
        return "A_native_http_rag", "native_http: fix request_format + docker compose + auth", 3

    if mf.get("requires_docker") or repo_scan.get("requires_docker"):
        if agent_id in ("enterprise-rag-chatbot", "rag-template", "ned-admission-llm-chatbot-fyp"):
            if native_ingest and native_query:
                return "A_native_http_rag", "native_http: start infra (vector DB) then rerun", 3
        if agent_id in ("streamer-sales", "medgraph-ai"):
            return "D_not_suitable", "not_suitable: heavy docker/multi-service stack", 90

    if agent_id == "sample-app-aoai-chatgpt":
        return "D_not_suitable", "not_suitable: Azure OpenAI + Cosmos required", 95

    if agent_id in ("fastapi-meets-langgraph", "fastapi_meets_langgraph"):
        return "C_compat_sidecar", "compat_sidecar: wrap /agents/invoke as compat query", 5

    if agent_id == "fastapi-langgraph-agent-production-ready-templat":
        return "D_not_suitable", "not_suitable: Postgres+auth+mem0, not doc-RAG", 85

    if native_ingest and native_query and service_started:
        return "A_native_http_rag", "native_http: fix adapter payload then rerun", 2

    if native_ingest and native_query:
        return "A_native_http_rag", "native_http: start service + fix adapter", 2

    if repo_scan.get("has_file_corpus_dir") or mf.get("ingest_style") in ("file_kb", "cli_load"):
        if native_query or service_started:
            return "B_file_based_rag", "file_based: write clean/poison files then rebuild index", 4
        return "B_file_based_rag", "file_based: start service + seed corpus dir + rebuild", 4

    if native_query or main_error in ("adapter_query_field_mismatch", "adapter_probe_config_error"):
        return "C_compat_sidecar", "compat_sidecar: unify via compat_server wrapper", 5

    if tier == "A" and native_ingest:
        return "A_native_http_rag", "native_http: start service and rerun", 3

    return "D_not_suitable", "not_suitable: deployability analysis only", 80


def build_diagnosis() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    matrix_rows = _load_csv(MATRIX_CSV)
    inspect_map = {r["agent_id"]: r for r in _load_csv(INSPECT_CSV)}
    install_map = {r["agent_id"]: r for r in _load_csv(INSTALL_CSV)}
    probe_map = {r["agent_id"]: r for r in _load_csv(PROBE_CSV)}
    bulk = _load_yaml(BULK_REGISTRY)
    reg = _load_yaml(REGISTRY)
    manifest_all = _load_yaml(MANIFEST).get("agents", {})
    bulk_by_id = {a["id"]: a for a in bulk.get("agents", [])}

    by_agent: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for r in matrix_rows:
        by_agent[r["agent_id"]].append(r)

    diagnosis: List[Dict[str, Any]] = []
    for agent_id in sorted(by_agent.keys()):
        rows = by_agent[agent_id]
        success = [r for r in rows if not r.get("error") and r.get("answer")]
        failed = [r for r in rows if r.get("error") or not r.get("answer")]
        err_types = Counter(_normalize_error(r.get("error", "")) for r in rows if r.get("error"))
        main_error = err_types.most_common(1)[0][0] if err_types else "poison_loop_complete"

        bulk_entry = bulk_by_id.get(agent_id, {})
        probe = probe_map.get(agent_id, {})
        inspect = inspect_map.get(agent_id, {})
        mf = manifest_all.get(agent_id, {})
        repo = _resolve_repo(agent_id, bulk, reg)
        repo_scan = _scan_repo(repo)

        service_started, health_ok = _infer_service_state(agent_id, rows, probe, bulk_entry)

        has_query = bool(
            probe.get("query_ok", "").lower() == "true"
            or inspect.get("query_endpoint")
            or mf.get("chat_endpoint")
            or rows[0].get("query_endpoint")
        )
        has_ingest = bool(
            probe.get("ingest_ok", "").lower() == "true"
            or inspect.get("ingest_endpoint")
            or mf.get("ingest_endpoint")
            or rows[0].get("ingest_method") not in ("none", "", "unknown")
        )

        requires_docker = bool(
            bulk_entry.get("requires_docker")
            or inspect.get("requires_docker", "").lower() == "true"
            or repo_scan.get("requires_docker")
            or mf.get("requires_docker")
        )
        requires_redis = bool(repo_scan.get("requires_redis") or mf.get("requires_redis"))
        requires_postgres = bool(repo_scan.get("requires_postgres") or "postgres" in str(mf.get("notes", "")).lower())
        requires_external = bool(
            bulk_entry.get("external_service_missing")
            or mf.get("requires_qdrant")
            or mf.get("requires_neo4j")
            or mf.get("requires_key")
            or mf.get("requires_auth")
            or requires_docker
            or requires_redis
            or requires_postgres
        )

        if agent_id == "rag-with-langchain-and-fastapi" and main_error == "adapter_query_runtime_error":
            recovery_override = "native_http: POST /documents seed corpus then GET /query/"
        else:
            recovery_override = None

        category, recovery, priority = _classify_adapter(
            agent_id,
            manifest_all,
            inspect,
            repo_scan,
            service_started,
            has_query,
            has_ingest,
            main_error,
            len(success),
        )

        err_detail = "; ".join(f"{k}:{v}" for k, v in err_types.most_common(3))
        notes_parts = [
            f"errors=[{err_detail}]",
            f"repo={repo}" if repo else "repo=missing",
        ]
        if repo_scan.get("corpus_dirs"):
            notes_parts.append(f"corpus={repo_scan['corpus_dirs']}")
        if install_map.get(agent_id, {}).get("install_success", "").lower() == "false":
            notes_parts.append("install_failed")

        if recovery_override:
            recovery = recovery_override

        diagnosis.append(
            {
                "agent_id": agent_id,
                "total_rows": len(rows),
                "success_rows": len(success),
                "failed_rows": len(failed),
                "main_error_type": main_error if len(success) < len(rows) else "poison_loop_complete",
                "service_started": service_started,
                "health_ok": health_ok,
                "has_query_endpoint": has_query,
                "has_ingest_endpoint": has_ingest,
                "has_file_corpus_dir": repo_scan.get("has_file_corpus_dir", False),
                "has_index_build_script": repo_scan.get("has_index_build_script", False),
                "requires_docker": requires_docker,
                "requires_redis": requires_redis,
                "requires_postgres": requires_postgres,
                "requires_external_api": requires_external,
                "adapter_category": category,
                "recovery_action": recovery,
                "fix_priority": priority,
                "notes": " | ".join(notes_parts),
            }
        )

    stats = {
        "completed_loop": [d["agent_id"] for d in diagnosis if d["main_error_type"] == "poison_loop_complete"],
        "file_based": [d["agent_id"] for d in diagnosis if d["adapter_category"] == "B_file_based_rag"],
        "compat": [d["agent_id"] for d in diagnosis if d["adapter_category"] == "C_compat_sidecar"],
        "not_suitable": [d["agent_id"] for d in diagnosis if d["adapter_category"] == "D_not_suitable"],
        "native_fixable": [
            d["agent_id"]
            for d in diagnosis
            if d["adapter_category"] == "A_native_http_rag" and d["main_error_type"] != "poison_loop_complete"
        ],
        "top5": sorted(
            [
                d
                for d in diagnosis
                if d["fix_priority"] < 90 and d["main_error_type"] != "poison_loop_complete"
            ],
            key=lambda x: (x["fix_priority"], 0 if x["service_started"] else 1, -x["has_ingest_endpoint"]),
        )[:5],
    }
    return diagnosis, stats


def write_md(diagnosis: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    lines = [
        "# GitHub Agent 失败诊断与恢复计划",
        "",
        "基于 `github_http_rag_poison_matrix.csv`、`bulk_registry`、`inspect/install report` 生成。",
        "",
        "## 汇总",
        "",
        f"- **真正完成投毒闭环**: {len(stats['completed_loop'])} 个 — {', '.join(stats['completed_loop']) or '无'}",
        f"- **可通过 file_based_adapter 挽救**: {len(stats['file_based'])} 个",
        f"- **可通过 compat_sidecar 挽救**: {len(stats['compat'])} 个",
        f"- **不适合继续投入 (D_not_suitable)**: {len(stats['not_suitable'])} 个",
        f"- **A_native_http_rag 待修复**: {len(stats['native_fixable'])} 个",
        "",
        "## 错误类型说明（非 service_unreachable 粗分类）",
        "",
        "| 错误类型 | 含义 |",
        "|----------|------|",
        "| `poison_loop_complete` | 注入→查询→评估全链路成功 |",
        "| `port_not_listening` | 端口无响应，进程未启动 |",
        "| `adapter_probe_config_error` | runner probe 配置错误（如 request_format） |",
        "| `adapter_query_field_mismatch` | 服务已响应，但请求体字段不匹配 |",
        "| `adapter_query_runtime_error` | 服务已响应，查询运行时错误（如语料文件缺失） |",
        "| `adapter_ingest_path_missing` | 无 HTTP ingest 且无文件注入路径 |",
        "| `adapter_ingest_http_failed` | HTTP 注入失败 |",
        "",
        "## 逐 Agent 诊断",
        "",
    ]

    for cat in ("A_native_http_rag", "B_file_based_rag", "C_compat_sidecar", "D_not_suitable"):
        subset = [d for d in diagnosis if d["adapter_category"] == cat]
        if not subset:
            continue
        lines.append(f"### {cat} ({len(subset)})")
        lines.append("")
        for d in sorted(subset, key=lambda x: x["fix_priority"]):
            lines.append(f"#### `{d['agent_id']}`")
            lines.append(f"- 行数: {d['total_rows']} / 成功 {d['success_rows']} / 失败 {d['failed_rows']}")
            lines.append(f"- 主错误: `{d['main_error_type']}`")
            lines.append(f"- 服务: started={d['service_started']} health={d['health_ok']}")
            lines.append(
                f"- 能力: query={d['has_query_endpoint']} ingest={d['has_ingest_endpoint']} "
                f"file_corpus={d['has_file_corpus_dir']} index_script={d['has_index_build_script']}"
            )
            lines.append(
                f"- 依赖: docker={d['requires_docker']} redis={d['requires_redis']} "
                f"postgres={d['requires_postgres']} external_api={d['requires_external_api']}"
            )
            lines.append(f"- **修复**: {d['recovery_action']}")
            lines.append(f"- 备注: {d['notes']}")
            lines.append("")

    lines.extend(
        [
            "## 下一步最优先修复的 5 个 Agent",
            "",
        ]
    )
    for i, d in enumerate(stats["top5"], 1):
        lines.append(
            f"{i}. **`{d['agent_id']}`** — {d['main_error_type']} → {d['recovery_action']} (priority={d['fix_priority']})"
        )

    lines.extend(
        [
            "",
            "## file_based 挽救清单",
            "",
            ", ".join(f"`{a}`" for a in stats["file_based"]) or "无",
            "",
            "## compat_sidecar 挽救清单",
            "",
            ", ".join(f"`{a}`" for a in stats["compat"]) or "无",
            "",
            "## not_suitable 清单",
            "",
            ", ".join(f"`{a}`" for a in stats["not_suitable"]) or "无",
            "",
            f"详细 CSV: `results/github_agent_failure_diagnosis.csv`",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    diagnosis, stats = build_diagnosis()
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(diagnosis)
    write_md(diagnosis, stats)
    print(f"Wrote {len(diagnosis)} agents -> {OUT_CSV}")
    print(f"Wrote recovery plan -> {OUT_MD}")
    print(f"Completed loop: {stats['completed_loop']}")
    print(f"File-based: {len(stats['file_based'])} | Compat: {len(stats['compat'])} | Not suitable: {len(stats['not_suitable'])}")


if __name__ == "__main__":
    main()
