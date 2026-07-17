"""完整攻击流水线 — Tool1 → Tool2 → Dispatcher → 结果回传。

一键运行:
    python run_full_pipeline.py --descriptor agent_descriptors/autogen_magentic_one.json --trials 10

分步运行:
    python run_full_pipeline.py --skip-tool12 --bundle path/to/execution_bundle.json
    python run_full_pipeline.py --skip-execute --bundle path/to/execution_bundle.json

输出:
    runs/<analysis_id>/
    ├── execution_bundle.json     ← Tool1+Tool2 产出
    ├── run_result.json           ← 回传后的 AgentEVAL 结果
    ├── feedback_summary.json     ← 反馈闭环结果
    └── dispatcher_results/
        ├── results.json          ← 分发器原始结果
        └── summary.json          ← ASR 汇总表
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 确保 AgentEVAL 在 Python 路径上
_AGENTEVAL_ROOT = Path("E:/wangan/AgentEVAL-Risk-Tools/src")
if str(_AGENTEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENTEVAL_ROOT))

# 确保本平台在路径上（dispatcher 需要）
_PLATFORM_ROOT = Path(__file__).resolve().parent
if str(_PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLATFORM_ROOT))

# Load .env for API key (DEEPSEEK_API_KEY / OPENAI_API_KEY)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass


def run_tool1_tool2(
    descriptor_path: str | Path,
    out_dir: str | Path,
    *,
    count: int = 1,
    profile: str = "compact",
    llm: str = "off",
    dynamic_probe: bool = True,
    use_siraj_prompts: bool = True,
) -> dict[str, Any]:
    """运行 AgentEVAL Tool1 + Tool2，生成 execution_bundle.json。

    Returns:
        {"evaluation_id": ..., "bundle_path": ..., "case_count": ...}
    """
    from agenteval.pipeline import AgentEval, PipelineOptions

    print("=" * 70)
    print("STEP 1: Tool1 (Analyzer) + Tool2 (Generator)")
    print("=" * 70)

    options = PipelineOptions(
        count=count,
        profile=profile,
        dynamic_probe=dynamic_probe,
        llm=llm,
        use_siraj_prompts=use_siraj_prompts,
    )

    agenteval = AgentEval(run_root=str(Path(out_dir).parent))
    evaluation = agenteval.prepare(
        target=str(descriptor_path),
        out_dir=str(out_dir),
        options=options,
    )

    bundle_path = Path(out_dir) / "execution_bundle.json"
    print(f"  Agent:      {evaluation.snapshot.agent_ref}")
    print(f"  Evidence:   {len(evaluation.snapshot.evidence_index)} items")
    print(f"  RiskSeeds:  {len(evaluation.seeds)}")
    print(f"  Cases:      {len(evaluation.cases)}")
    print(f"  Bundle:     {bundle_path.resolve()}")
    print(f"  Status:     {evaluation.status}")

    return {
        "evaluation_id": evaluation.evaluation_id,
        "bundle_path": str(bundle_path),
        "case_count": len(evaluation.cases),
        "seed_count": len(evaluation.seeds),
        "evaluation": evaluation,
    }


def run_dispatcher(
    bundle_path: str | Path,
    *,
    work_dir: str | Path = "dispatcher_workspace",
    results_dir: str | Path = "dispatcher_results",
    trials: int = 10,
    models: list[str] | None = None,
    frameworks: list[str] | None = None,
    error_templates: list[str] | None = None,
    user_query_variant: int = 0,
) -> dict[str, Any]:
    """运行分发器，执行攻击测试。

    Returns:
        {"results": [...], "summary": {...}}
    """
    from dispatcher import AttackDispatcher

    print()
    print("=" * 70)
    print("STEP 2: Attack Dispatcher")
    print("=" * 70)

    dispatcher = AttackDispatcher(
        bundle_path=str(bundle_path),
        work_dir=str(work_dir),
        results_dir=str(results_dir),
        trials=trials,
        models=models or ["deepseek-chat"],
        frameworks=frameworks or ["autogen", "crewai", "metagpt"],
        error_templates=error_templates or ["access_denied", "python_traceback", "wordpress_403"],
        user_query_variant=user_query_variant,
    )

    return dispatcher.run()


def submit_to_agenteval(
    evaluation: Any,
    results_path: str | Path,
    *,
    apply_feedback: bool = True,
) -> dict[str, Any]:
    """将攻击结果回传给 AgentEVAL，触发反馈闭环。

    Args:
        evaluation: PreparedEvaluation 对象或 analysis_dir 路径
        results_path: dispatcher 输出的 results.json 路径
        apply_feedback: 是否应用反馈更新 RiskSeed 置信度
    """
    from agenteval.pipeline import AgentEval

    print()
    print("=" * 70)
    print("STEP 3: Submit Results to AgentEVAL (Feedback Loop)")
    print("=" * 70)

    # 加载结果并去除 evaluation_id（submit_results 会校验，但不强制要求）
    raw = json.loads(Path(results_path).read_text(encoding="utf-8"))

    # 确保每个 result 有 seed_id 和 run_id
    results_list = raw.get("results", [])
    for r in results_list:
        if "run_id" not in r:
            r["run_id"] = f"run_ext_{r.get('case_id', 'unknown')}_{uuid.uuid4().hex[:8]}"
        if "seed_id" not in r:
            r["seed_id"] = r.get("case_id", "unknown")

    agenteval = AgentEval()
    submission = agenteval.submit_results(
        evaluation=evaluation,
        results=raw,
        apply_feedback=apply_feedback,
    )

    print(f"  Accepted:    {submission.get('accepted', 0)} results")
    print(f"  Status:      {submission.get('status', 'unknown')}")
    if "feedback" in submission:
        fb = submission["feedback"]
        print(f"  Feedback:    {fb.get('updated_count', '?')} seeds updated")

    return submission


def run_full_pipeline(
    descriptor_path: str | Path | None = None,
    bundle_path: str | Path | None = None,
    *,
    out_dir: str | Path | None = None,
    skip_tool12: bool = False,
    skip_execute: bool = False,
    skip_submit: bool = False,
    trials: int = 10,
    models: list[str] | None = None,
    frameworks: list[str] | None = None,
    error_templates: list[str] | None = None,
    count: int = 1,
    profile: str = "compact",
    llm: str = "off",
) -> dict[str, Any]:
    """端到端运行完整流水线。

    Pipeline:
        Agent Descriptor → Tool1 (Analyzer) → Tool2 (Generator)
        → execution_bundle.json → Dispatcher → results.json
        → AgentEVAL submit_results (feedback loop)

    Args:
        descriptor_path: Agent 描述文件路径（Tool1 输入）
        bundle_path: 已有的 execution_bundle.json（可跳过 Tool1+Tool2）
        out_dir: 输出目录（默认 runs/<timestamp>）
        skip_tool12: 跳过 Tool1+Tool2（需要提供 bundle_path）
        skip_execute: 跳过攻击执行（只跑 Tool1+Tool2）
        skip_submit: 跳过结果回传
        trials: 每组组合的试验次数
        models: 模型列表
        frameworks: 框架列表
        error_templates: 错误模板列表
        count: Tool2 每个 seed 生成的 case 数
        profile: Tool2 生成策略 (compact/expanded)
        llm: Tool1/Tool2 的 LLM 模式 (on/off/auto)
    """
    started_at = datetime.now(timezone.utc)

    # 确定输出目录
    if out_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_dir = Path("runs") / f"pipeline_{ts}"
    else:
        out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Pipeline output directory: {out_dir.resolve()}")
    print(f"Start time: {started_at.isoformat()}")
    print()

    pipeline_state: dict[str, Any] = {
        "started_at": started_at.isoformat(),
        "output_dir": str(out_dir),
        "steps_completed": [],
    }

    # ---- Step 1: Tool1 + Tool2 ----
    evaluation = None
    if skip_tool12:
        if not bundle_path:
            raise ValueError("--skip-tool12 requires --bundle")
        print("SKIPPING Tool1+Tool2 (using existing bundle)")
        bundle_path = Path(bundle_path)
        if not bundle_path.exists():
            raise FileNotFoundError(f"Bundle not found: {bundle_path}")
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        pipeline_state["bundle_path"] = str(bundle_path)
        pipeline_state["evaluation_id"] = bundle.get("evaluation_id", "")
        pipeline_state["case_count"] = len(bundle.get("cases", []))
    else:
        if not descriptor_path:
            raise ValueError("Either --descriptor or --bundle (with --skip-tool12) is required")
        tool12_result = run_tool1_tool2(
            descriptor_path=descriptor_path,
            out_dir=str(out_dir),
            count=count,
            profile=profile,
            llm=llm,
        )
        bundle_path = Path(tool12_result["bundle_path"])
        evaluation = tool12_result.get("evaluation")
        pipeline_state.update({
            "evaluation_id": tool12_result["evaluation_id"],
            "bundle_path": str(bundle_path),
            "case_count": tool12_result["case_count"],
            "seed_count": tool12_result["seed_count"],
        })
        pipeline_state["steps_completed"].append("tool1_tool2")

    # ---- Step 2: Dispatcher (attack execution) ----
    if skip_execute:
        print("\nSKIPPING attack execution")
    else:
        dispatcher_out = out_dir / "dispatcher_results"
        dispatcher_work = out_dir / "dispatcher_workspace"
        dispatcher_result = run_dispatcher(
            bundle_path=bundle_path,
            work_dir=dispatcher_work,
            results_dir=dispatcher_out,
            trials=trials,
            models=models,
            frameworks=frameworks,
            error_templates=error_templates,
        )
        pipeline_state["dispatcher_summary"] = dispatcher_result.get("summary", {})
        pipeline_state["steps_completed"].append("dispatcher")

    # ---- Step 3: Submit to AgentEVAL ----
    if skip_submit:
        print("\nSKIPPING result submission")
    else:
        dispatcher_results = out_dir / "dispatcher_results" / "results.json"
        if dispatcher_results.exists():
            # 如果有 PreparedEvaluation 对象直接用，否则从 analysis_dir 加载
            if evaluation is not None:
                submit_to_agenteval(evaluation, dispatcher_results, apply_feedback=True)
            else:
                # 尝试从 out_dir 加载
                try:
                    from agenteval.pipeline import AgentEval
                    ae = AgentEval()
                    loaded = ae.load(str(out_dir))
                    submit_to_agenteval(loaded, dispatcher_results, apply_feedback=True)
                except Exception as exc:
                    print(f"  WARNING: Could not submit results: {exc}")
                    print(f"  Results are at: {dispatcher_results.resolve()}")
            pipeline_state["steps_completed"].append("submit_results")
        else:
            print(f"\nWARNING: No dispatcher results found at {dispatcher_results}")

    # ---- Final Summary ----
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    pipeline_state["elapsed_seconds"] = round(elapsed, 1)
    pipeline_state["completed_at"] = datetime.now(timezone.utc).isoformat()

    print()
    print("=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Output:      {out_dir.resolve()}")
    print(f"  Steps:       {pipeline_state['steps_completed']}")
    print(f"  Elapsed:     {elapsed:.1f}s")

    # 打印 ASR 汇总
    disp_summary = pipeline_state.get("dispatcher_summary", {})
    if disp_summary:
        overall_asr = disp_summary.get("overall_asr", 0)
        total = disp_summary.get("total_trials", 0)
        successes = disp_summary.get("total_successes", 0)
        print(f"  ASR:         {overall_asr:.1%} ({successes}/{total})")
        for fw, stats in disp_summary.get("by_framework", {}).items():
            print(f"    {fw}:      {stats.get('asr', 0):.1%} ({stats.get('successes', 0)}/{stats.get('total', 0)})")

    # 保存流水线状态
    state_path = out_dir / "pipeline_state.json"
    state_path.write_text(
        json.dumps(pipeline_state, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return pipeline_state


def main():
    parser = argparse.ArgumentParser(
        description="MAS Attack Full Pipeline: Tool1 → Tool2 → Dispatcher → Submit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 完整流水线：Tool1+Tool2 → 攻击 → 回传
  python run_full_pipeline.py --descriptor agent_descriptors/autogen_magentic_one.json --trials 10

  # 只用 AutoGen + deepseek-chat，减少试验次数
  python run_full_pipeline.py --descriptor agent_descriptors/autogen_magentic_one.json \\
      --frameworks autogen --models deepseek-chat --trials 3

  # 从已有 bundle 开始（跳过 Tool1+Tool2）
  python run_full_pipeline.py --skip-tool12 --bundle runs/xxx/execution_bundle.json --trials 5

  # 只运行 Tool1+Tool2 生成情况（不执行攻击）
  python run_full_pipeline.py --descriptor agent_descriptors/autogen_magentic_one.json --skip-execute

  # 运行攻击但跳过回传
  python run_full_pipeline.py --skip-tool12 --bundle bundle.json --skip-submit
        """,
    )
    parser.add_argument(
        "--descriptor", default=None,
        help="Path to Agent descriptor JSON for Tool1 input",
    )
    parser.add_argument(
        "--bundle", default=None,
        help="Path to existing execution_bundle.json (skip Tool1+Tool2)",
    )
    parser.add_argument(
        "--out-dir", default=None,
        help="Output directory (default: runs/pipeline_<timestamp>)",
    )
    parser.add_argument(
        "--skip-tool12", action="store_true",
        help="Skip Tool1+Tool2 (use existing bundle)",
    )
    parser.add_argument(
        "--skip-execute", action="store_true",
        help="Skip attack execution (just generate cases)",
    )
    parser.add_argument(
        "--skip-submit", action="store_true",
        help="Skip result submission back to AgentEVAL",
    )
    parser.add_argument(
        "--trials", type=int, default=10,
        help="Trials per combination (default: 10)",
    )
    parser.add_argument(
        "--frameworks", default="autogen,crewai,metagpt",
        help="Comma-separated frameworks",
    )
    parser.add_argument(
        "--models", default="deepseek-chat",
        help="Comma-separated model names",
    )
    parser.add_argument(
        "--error-templates", default="access_denied,python_traceback,wordpress_403",
        help="Comma-separated error templates",
    )
    parser.add_argument(
        "--count", type=int, default=1,
        help="Cases per seed from Tool2 (default: 1)",
    )
    parser.add_argument(
        "--profile", default="compact",
        choices=["compact", "expanded"],
        help="Tool2 generation profile (default: compact)",
    )
    parser.add_argument(
        "--llm", default="off",
        choices=["on", "off", "auto"],
        help="LLM mode for Tool1/Tool2 (default: off)",
    )

    args = parser.parse_args()

    frameworks = [fw.strip() for fw in args.frameworks.split(",")]
    models = [m.strip() for m in args.models.split(",")]
    error_templates = [t.strip() for t in args.error_templates.split(",")]

    run_full_pipeline(
        descriptor_path=args.descriptor,
        bundle_path=args.bundle,
        out_dir=args.out_dir,
        skip_tool12=args.skip_tool12,
        skip_execute=args.skip_execute,
        skip_submit=args.skip_submit,
        trials=args.trials,
        models=models,
        frameworks=frameworks,
        error_templates=error_templates,
        count=args.count,
        profile=args.profile,
        llm=args.llm,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
