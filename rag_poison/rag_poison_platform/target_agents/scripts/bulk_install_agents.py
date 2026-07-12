"""
Level 1c: Per-agent venv pip install (resumable, fault-tolerant).

Reads target_agents/bulk_registry.yaml; updates registry after each agent.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent.parent))
sys.path.insert(0, str(SCRIPT_DIR.parent))

from target_agents.bulk_common import (  # noqa: E402
    RESULTS_DIR,
    agent_root,
    apply_api_dependency_fields,
    load_registry,
    repo_path,
    run_cmd,
    save_registry,
    venv_path,
    write_csv,
    now_iso,
)
from utils.deepseek_env import write_agent_env_file  # noqa: E402

INSTALL_TIMEOUT_SEC = 600  # 10 minutes per agent pip phase (total budget)
VENV_TIMEOUT_SEC = 120

SKIP_HEAVY_IDS = frozenset({"dify", "open-webui", "langchain", "chroma"})

BUILD_FAIL_MARKERS = (
    "numpy",
    "chromadb",
    "hnswlib",
    "onnxruntime",
    "tokenizers",
    "meson",
    "subprocess-exited-with-error",
    "error: metadata-generation-failed",
    "failed to build",
    "microsoft visual c++",
    "gcc",
    "building wheel",
)

CSV_FIELDS = [
    "agent_id",
    "repo_url",
    "local_path",
    "clone_success",
    "install_attempted",
    "install_success",
    "install_skipped",
    "skip_reason",
    "venv_path",
    "install_log",
    "install_seconds",
    "error_type",
    "error_message",
]


def _py_exe(vp: Path) -> Path:
    return vp / "Scripts" / "python.exe"


def _find_manifest(repo: Path) -> Tuple[str, Optional[Path]]:
    """Return (manifest_type, path): requirements | pyproject | package_json | none."""
    root_req = repo / "requirements.txt"
    if root_req.is_file():
        return "requirements", root_req
    reqs = sorted(repo.rglob("requirements.txt"), key=lambda p: len(p.parts))
    if reqs:
        return "requirements", reqs[0]

    root_pp = repo / "pyproject.toml"
    if root_pp.is_file():
        return "pyproject", root_pp
    pps = sorted(repo.rglob("pyproject.toml"), key=lambda p: len(p.parts))
    if pps:
        return "pyproject", pps[0]

    if (repo / "package.json").is_file():
        return "package_json", repo / "package.json"

    return "none", None


def _classify_error(code: int, output: str) -> str:
    if code == 124:
        return "timeout"
    low = (output or "").lower()
    if any(m.lower() in low for m in BUILD_FAIL_MARKERS):
        return "dependency_build_failed"
    if code != 0:
        return "pip_failed"
    return ""


def _truncate(msg: str, limit: int = 800) -> str:
    msg = (msg or "").strip()
    return msg if len(msg) <= limit else msg[-limit:]


def _install_log_path(aid: str) -> Path:
    return agent_root(aid) / "install.log"


def _write_install_log(aid: str, text: str) -> Path:
    path = _install_log_path(aid)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="replace")
    return path


def _is_heavy_skip(agent_id: str) -> bool:
    return agent_id in SKIP_HEAVY_IDS


def _ensure_venv(aid: str, vp: Path, logs: List[str]) -> Tuple[bool, str, str]:
    if _py_exe(vp).is_file():
        logs.append("venv: already exists")
        return True, "", ""
    code, out = run_cmd([sys.executable, "-m", "venv", str(vp)], timeout=VENV_TIMEOUT_SEC)
    logs.append(f"venv create (code={code}):\n{out}")
    if code != 0:
        err_type = _classify_error(code, out)
        return False, err_type or "venv_failed", _truncate(out)
    return True, "", ""


def _run_pip_install(
    py: str,
    repo: Path,
    manifest_type: str,
    manifest_path: Optional[Path],
    logs: List[str],
) -> Tuple[bool, str, str, int]:
    """Run pip install with shared timeout budget; return success, error_type, message, seconds."""
    started = time.monotonic()
    remaining = INSTALL_TIMEOUT_SEC

    def _pip(args: List[str], label: str) -> Tuple[int, str]:
        nonlocal remaining
        budget = min(remaining, max(60, remaining))
        code, out = run_cmd(args, cwd=repo, timeout=budget)
        elapsed = int(time.monotonic() - started)
        remaining = INSTALL_TIMEOUT_SEC - elapsed
        logs.append(f"{label} (code={code}, elapsed={elapsed}s):\n{out}")
        return code, out

    code, out = _pip([py, "-m", "pip", "install", "-q", "--upgrade", "pip"], "pip upgrade")
    if code != 0:
        return False, _classify_error(code, out), _truncate(out), int(time.monotonic() - started)

    if manifest_type == "requirements" and manifest_path:
        code, out = _pip(
            [py, "-m", "pip", "install", "-r", str(manifest_path)],
            f"pip install -r {manifest_path.name}",
        )
    elif manifest_type == "pyproject" and manifest_path:
        install_root = manifest_path.parent
        code, out = _pip(
            [py, "-m", "pip", "install", "-e", str(install_root)],
            f"pip install -e {install_root}",
        )
    else:
        return False, "no_install_manifest", "no requirements.txt or pyproject.toml", int(
            time.monotonic() - started
        )

    elapsed = int(time.monotonic() - started)
    if code == 124 or elapsed >= INSTALL_TIMEOUT_SEC:
        return False, "timeout", _truncate(out), elapsed
    if code != 0:
        return False, _classify_error(code, out), _truncate(out), elapsed
    return True, "", "", elapsed


def _make_row(agent: Dict[str, Any], **overrides: Any) -> Dict[str, Any]:
    aid = agent["id"]
    vp = venv_path(aid)
    log_path = _install_log_path(aid)
    row = {
        "agent_id": aid,
        "repo_url": agent.get("repo_url", ""),
        "local_path": agent.get("local_path", str(repo_path(aid))),
        "clone_success": agent.get("clone_success", False),
        "install_attempted": False,
        "install_success": False,
        "install_skipped": False,
        "skip_reason": "",
        "venv_path": str(vp),
        "install_log": str(log_path),
        "install_seconds": 0,
        "error_type": "",
        "error_message": "",
    }
    row.update(overrides)
    return row


def _update_agent_registry(
    agent: Dict[str, Any],
    *,
    install_attempted: bool,
    install_success: bool,
    install_skipped: bool,
    skip_reason: str,
    error_type: str,
    error_message: str,
) -> None:
    if install_skipped:
        status = "install_skipped"
    elif install_success:
        status = "installed"
    elif install_attempted:
        status = "install_failed"
    else:
        status = agent.get("status", "cloned")

    agent.update(
        {
            "install_attempted": install_attempted,
            "install_success": install_success,
            "install_skipped": install_skipped,
            "skip_reason": skip_reason or "",
            "error_type": error_type or "",
            "error_stage": "" if install_success or install_skipped else ("install" if install_attempted else ""),
            "error_summary": _truncate(error_message) if error_message else "",
            "status": status,
            "venv_path": str(venv_path(agent["id"])),
            "tested_at": now_iso(),
        }
    )


def _process_agent(agent: Dict[str, Any], *, force: bool) -> Dict[str, Any]:
    aid = agent["id"]
    repo = repo_path(aid)
    vp = venv_path(aid)
    vp.parent.mkdir(parents=True, exist_ok=True)

    if not agent.get("clone_success"):
        _update_agent_registry(
            agent,
            install_attempted=False,
            install_success=False,
            install_skipped=True,
            skip_reason="no_clone",
            error_type="",
            error_message="",
        )
        return _make_row(
            agent,
            install_skipped=True,
            skip_reason="no_clone",
        )

    if not repo.is_dir() or not any(repo.iterdir()):
        agent["clone_success"] = False
        _update_agent_registry(
            agent,
            install_attempted=False,
            install_success=False,
            install_skipped=True,
            skip_reason="repo_missing",
            error_type="repo_missing",
            error_message=f"repo dir empty or missing: {repo}",
        )
        return _make_row(agent, install_skipped=True, skip_reason="repo_missing", error_type="repo_missing")

    if _is_heavy_skip(aid):
        _update_agent_registry(
            agent,
            install_attempted=False,
            install_success=False,
            install_skipped=True,
            skip_reason="too_heavy_or_framework_repo",
            error_type="",
            error_message="",
        )
        _write_install_log(aid, "SKIPPED: too_heavy_or_framework_repo\n")
        return _make_row(
            agent,
            install_skipped=True,
            skip_reason="too_heavy_or_framework_repo",
        )

    if agent.get("install_success") and not force:
        apply_api_dependency_fields(agent, repo)
        write_agent_env_file(vp.parent, use_deepseek=True)
        _update_agent_registry(
            agent,
            install_attempted=False,
            install_success=True,
            install_skipped=False,
            skip_reason="already_installed",
            error_type="",
            error_message="",
        )
        return _make_row(
            agent,
            install_skipped=True,
            skip_reason="already_installed",
            install_success=True,
        )

    logs: List[str] = [f"=== install start {now_iso()} force={force} ==="]
    started = time.monotonic()

    try:
        manifest_type, manifest_path = _find_manifest(repo)

        if manifest_type == "package_json":
            msg = "node project; npm install not supported in this pipeline"
            logs.append(msg)
            _write_install_log(aid, "\n".join(logs))
            _update_agent_registry(
                agent,
                install_attempted=False,
                install_success=False,
                install_skipped=True,
                skip_reason="node_project",
                error_type="",
                error_message=msg,
            )
            return _make_row(
                agent,
                install_attempted=False,
                install_skipped=True,
                skip_reason="node_project",
                install_seconds=int(time.monotonic() - started),
            )

        if manifest_type == "none":
            msg = "no requirements.txt or pyproject.toml"
            logs.append(msg)
            _write_install_log(aid, "\n".join(logs))
            _update_agent_registry(
                agent,
                install_attempted=False,
                install_success=False,
                install_skipped=True,
                skip_reason="no_install_manifest",
                error_type="no_install_manifest",
                error_message=msg,
            )
            return _make_row(
                agent,
                install_attempted=False,
                install_skipped=True,
                skip_reason="no_install_manifest",
                error_type="no_install_manifest",
                error_message=msg,
                install_seconds=int(time.monotonic() - started),
            )

        ok, err_type, err_msg = _ensure_venv(aid, vp, logs)
        if not ok:
            _write_install_log(aid, "\n".join(logs))
            _update_agent_registry(
                agent,
                install_attempted=True,
                install_success=False,
                install_skipped=False,
                skip_reason="",
                error_type=err_type,
                error_message=err_msg,
            )
            return _make_row(
                agent,
                install_attempted=True,
                install_success=False,
                error_type=err_type,
                error_message=err_msg,
                install_seconds=int(time.monotonic() - started),
            )

        py = str(_py_exe(vp))
        success, err_type, err_msg, elapsed = _run_pip_install(
            py, repo, manifest_type, manifest_path, logs
        )
        logs.append(f"=== finished success={success} elapsed={elapsed}s ===")
        _write_install_log(aid, "\n".join(logs))

        if success:
            apply_api_dependency_fields(agent, repo)
            write_agent_env_file(vp.parent, use_deepseek=True)
        _update_agent_registry(
            agent,
            install_attempted=True,
            install_success=success,
            install_skipped=False,
            skip_reason="",
            error_type=err_type,
            error_message=err_msg,
        )
        if success and agent.get("external_service_missing"):
            agent["status"] = agent.get("status") or "external_service_missing"
            agent["poison_test_supported"] = False
        return _make_row(
            agent,
            install_attempted=True,
            install_success=success,
            error_type=err_type,
            error_message=err_msg,
            install_seconds=elapsed,
        )

    except Exception as exc:
        tb = traceback.format_exc()
        logs.append(f"UNHANDLED: {tb}")
        _write_install_log(aid, "\n".join(logs))
        err_msg = _truncate(f"{type(exc).__name__}: {exc}")
        _update_agent_registry(
            agent,
            install_attempted=True,
            install_success=False,
            install_skipped=False,
            skip_reason="",
            error_type="unhandled_exception",
            error_message=err_msg,
        )
        return _make_row(
            agent,
            install_attempted=True,
            install_success=False,
            error_type="unhandled_exception",
            error_message=err_msg,
            install_seconds=int(time.monotonic() - started),
        )


def _select_agents(
    agents: List[Dict[str, Any]],
    *,
    only: Optional[str],
    max_agents: Optional[int],
) -> List[Dict[str, Any]]:
    if only:
        selected = [a for a in agents if a.get("id") == only]
        if not selected:
            raise SystemExit(f"agent_id not found in registry: {only}")
        return selected

    cloned = [a for a in agents if a.get("clone_success")]
    if max_agents is not None:
        return cloned[: max(0, max_agents)]
    return cloned


def _build_all_rows(reg: Dict[str, Any], processed: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for agent in reg.get("agents", []):
        aid = agent["id"]
        if aid in processed:
            rows.append(processed[aid])
        else:
            rows.append(
                _make_row(
                    agent,
                    install_skipped=not agent.get("clone_success"),
                    skip_reason="not_processed_this_run" if agent.get("clone_success") else "no_clone",
                    install_success=agent.get("install_success", False),
                    install_attempted=agent.get("install_attempted", False),
                )
            )
    return rows


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bulk install agents into isolated venvs")
    p.add_argument("--force", action="store_true", help="Reinstall even if install_success=true")
    p.add_argument("--only", type=str, default=None, help="Install a single agent_id")
    p.add_argument("--max-agents", type=int, default=None, help="Limit cloned agents processed this run")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    reg = load_registry()
    all_agents = reg.get("agents", [])
    total_cloned = sum(1 for a in all_agents if a.get("clone_success"))

    targets = _select_agents(all_agents, only=args.only, max_agents=args.max_agents)
    processed_rows: Dict[str, Dict[str, Any]] = {}

    stats = {
        "attempted": 0,
        "success": 0,
        "skipped": 0,
        "failed": 0,
        "timeout_count": 0,
    }

    print(f"[install] total_cloned={total_cloned} this_run={len(targets)} force={args.force}")

    for agent in targets:
        aid = agent["id"]
        try:
            row = _process_agent(agent, force=args.force)
            processed_rows[aid] = row
            save_registry(reg)

            if row.get("install_skipped"):
                stats["skipped"] += 1
            elif row.get("install_success"):
                stats["attempted"] += 1
                stats["success"] += 1
            elif row.get("install_attempted"):
                stats["attempted"] += 1
                stats["failed"] += 1
                if row.get("error_type") == "timeout":
                    stats["timeout_count"] += 1

            print(
                f"[install] {aid} "
                f"attempted={row.get('install_attempted')} "
                f"success={row.get('install_success')} "
                f"skipped={row.get('install_skipped')} "
                f"reason={row.get('skip_reason') or row.get('error_type')}"
            )
        except Exception as exc:
            err_row = _make_row(
                agent,
                install_attempted=True,
                install_success=False,
                error_type="outer_exception",
                error_message=_truncate(str(exc)),
            )
            processed_rows[aid] = err_row
            _update_agent_registry(
                agent,
                install_attempted=True,
                install_success=False,
                install_skipped=False,
                skip_reason="",
                error_type="outer_exception",
                error_message=str(exc),
            )
            save_registry(reg)
            stats["attempted"] += 1
            stats["failed"] += 1
            print(f"[install] {aid} OUTER_ERROR {exc}")

    all_rows = _build_all_rows(reg, processed_rows)
    out_csv = RESULTS_DIR / "bulk_agent_install_report.csv"
    write_csv(out_csv, all_rows, fieldnames=CSV_FIELDS)
    save_registry(reg)

    print("--- install summary ---")
    print(f"total_cloned: {total_cloned}")
    print(f"attempted: {stats['attempted']}")
    print(f"success: {stats['success']}")
    print(f"skipped: {stats['skipped']}")
    print(f"failed: {stats['failed']}")
    print(f"timeout_count: {stats['timeout_count']}")
    print(f"CSV -> {out_csv}")


if __name__ == "__main__":
    main()
