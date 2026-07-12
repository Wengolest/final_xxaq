#!/usr/bin/env python3
"""Create venv per agent under agents/ and pip install (ASCII-safe alternative to ps1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "agents"

SPECS: dict[str, list[str]] = {
    "swarm": ["openai>=1.0", "mcp>=1.0", "git+https://github.com/openai/swarm.git"],
    "pydantic-ai": ["pydantic-ai"],  # PyPI；本地 clone 在中文路径下 editable 易失败
    "crewai": ["crewai", "crewai-tools", "mcp>=1.0", "mcpadapt"],
    "langroid": ["langroid"],
    "strands-agents": ["-e", str(AGENTS / "strands-agents" / "strands-py")],
    "autogen": ["autogen-agentchat", "autogen-ext[mcp,openai]", "mcp>=1.0"],
}


def run(cmd: list[str], cwd: Path | None = None) -> int:
    print("$", " ".join(cmd))
    return subprocess.call(cmd, cwd=cwd)


def main() -> None:
    main_venv = ROOT / "venv"
    if not main_venv.is_dir():
        run([sys.executable, "-m", "venv", str(main_venv)])
    pip_main = main_venv / "Scripts" / "pip.exe"
    run([str(pip_main), "install", "-r", str(ROOT / "requirements.txt")])

    for name, packages in SPECS.items():
        repo = AGENTS / name
        if not repo.is_dir():
            print(f"[SKIP] {name}")
            continue
        venv = repo / "venv"
        if not venv.is_dir():
            run([sys.executable, "-m", "venv", str(venv)])
        pip = venv / "Scripts" / "pip.exe"
        run([str(pip), "install", "--upgrade", "pip"])
        i = 0
        while i < len(packages):
            pkg = packages[i]
            if pkg == "-e" and i + 1 < len(packages):
                cmd = [str(pip), "install", "-e", packages[i + 1]]
                i += 2
            else:
                cmd = [str(pip), "install", pkg]
                i += 1
            if run(cmd) != 0:
                print(f"[WARN] {name}: failed: {' '.join(cmd[2:])}")
        (repo / "ENV_README.txt").write_text(
            f"Agent: {name}\nActivate: .\\venv\\Scripts\\Activate.ps1\n",
            encoding="utf-8",
        )
    print("\nDone.")


if __name__ == "__main__":
    main()
