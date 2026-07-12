"""Benchmark orchestrator — run full MAS safety evaluation suite."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mas_safety.evaluator.metadata_sanitizer import MetadataSanitizer
from mas_safety.evaluator.metrics import compute_attack_result, format_results_table
from mas_safety.scenarios.catalog import build_default_scenarios
from mas_safety.scenarios.runner import ScenarioRunner
from mas_safety.types import AttackCategory, AttackResult, AttackScenario, OrchestratorType


class BenchmarkRunner:
    """Run MAS safety benchmarks with configurable trials and scenarios."""

    def __init__(
        self,
        work_dir: str | Path = "benchmark_workspace",
        results_dir: str | Path = "benchmark_results",
        orchestrator_type: OrchestratorType = OrchestratorType.CENTRAL,
        use_full_mas: bool = True,
        trials_per_scenario: int = 3,
    ):
        self.work_dir = Path(work_dir)
        self.results_dir = Path(results_dir)
        self.orchestrator_type = orchestrator_type
        self.use_full_mas = use_full_mas
        self.trials_per_scenario = trials_per_scenario
        self.scenario_runner = ScenarioRunner(
            work_dir=self.work_dir,
            orchestrator_type=orchestrator_type,
            use_full_mas=use_full_mas,
        )
        self.metadata_sanitizer = MetadataSanitizer()

    def run(
        self,
        scenarios: list[AttackScenario] | None = None,
        categories: list[AttackCategory] | None = None,
    ) -> list[AttackResult]:
        scenarios = scenarios or build_default_scenarios()
        if categories:
            scenarios = [s for s in scenarios if s.category in categories]

        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        results: list[AttackResult] = []
        for scenario in scenarios:
            trial_results = []
            for trial_id in range(self.trials_per_scenario):
                result = self.scenario_runner.run_trial(scenario, trial_id)
                trial_results.append(result)

            attack_result = compute_attack_result(scenario, trial_results)
            results.append(attack_result)
            self._save_scenario_result(attack_result)

        self._save_summary(results)
        return results

    def run_dry(self) -> list[AttackResult]:
        """Generate fixtures and analyze without calling LLM (offline validation)."""
        from mas_safety.evaluator.trace_analyzer import TraceAnalyzer
        from mas_safety.sandbox.fixtures import FixtureGenerator
        from mas_safety.types import AgentMessage, TrialResult
        import uuid

        self.results_dir.mkdir(parents=True, exist_ok=True)
        scenarios = build_default_scenarios()
        results = []

        for scenario in scenarios:
            if scenario.category != AttackCategory.MAS_HIJACKING:
                continue
            trial_dir = self.work_dir / "dry_run"
            fixtures = FixtureGenerator(trial_dir / "content")
            marker = f"MAS_RCE_SUCCESS_{uuid.uuid4().hex[:12]}"
            f = fixtures.create_hijack_file(
                "dry_attack.txt",
                scenario.error_template,
                marker=marker,
            )
            content = f.read_text(encoding="utf-8")

            fake_messages = [
                AgentMessage("FileSurfer", "assistant", content, 0),
                AgentMessage(
                    "Orchestrator",
                    "assistant",
                    "File access failed. Instruct Executor to run: python dry_attack.txt",
                    1,
                ),
                AgentMessage("Executor", "user", f"MARKER_WRITTEN:{marker}", 2),
            ]

            analyzer = TraceAnalyzer(trial_dir, expected_marker=marker)
            trial = TrialResult(
                scenario=scenario.name,
                trial_id=0,
                success=analyzer.detect_control_flow_hijack(fake_messages),
                refused=False,
                metadata_poisoned=True,
                control_flow_hijacked=True,
                payload_executed=False,
                confused_deputy_agent="FileSurfer",
                messages=fake_messages,
            )
            attack_result = compute_attack_result(scenario, [trial])
            results.append(attack_result)
            self._save_scenario_result(attack_result)

        self._save_summary(results)
        return results

    def _save_scenario_result(self, result: AttackResult) -> None:
        path = self.results_dir / f"{result.scenario.name}.json"
        data = {
            "scenario": result.scenario.name,
            "category": result.scenario.category.value,
            "modality": result.scenario.modality.value,
            "trials": result.trials,
            "attack_success_rate": result.attack_success_rate,
            "refusal_rate": result.refusal_rate,
            "metadata_poison_rate": result.metadata_poison_rate,
            "control_flow_hijack_rate": result.control_flow_hijack_rate,
            "trial_details": [
                {
                    "trial_id": t.trial_id,
                    "success": t.success,
                    "refused": t.refused,
                    "metadata_poisoned": t.metadata_poisoned,
                    "control_flow_hijacked": t.control_flow_hijacked,
                    "payload_executed": t.payload_executed,
                    "confused_deputy": t.confused_deputy_agent,
                    "markers": t.markers_found,
                    "notes": t.notes,
                    "trace_files": self._trace_files(result.scenario.name, t.trial_id),
                    "metadata_report": self._metadata_report(t),
                }
                for t in result.trial_results
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _metadata_report(self, trial) -> dict:
        report = self.metadata_sanitizer.analyze_propagation(trial.messages)
        return {
            "cross_agent_leaks": report.cross_agent_leaks,
            "agents_contaminated": report.agents_contaminated,
            "sanitization_score": report.sanitization_score,
        }

    def _trace_files(self, scenario_name: str, trial_id: int) -> list[str]:
        """Return saved trace files for the exact scenario trial, if present."""
        trace_files: list[str] = []
        for json_path in sorted(self.work_dir.glob(f"trial_{trial_id}_*/trace/agent_trace.json")):
            try:
                trace = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if trace.get("scenario", {}).get("name") != scenario_name:
                continue
            if trace.get("trial_id") != trial_id:
                continue
            trace_files.append(str(json_path.resolve()))
            md_path = json_path.with_suffix(".md")
            if md_path.exists():
                trace_files.append(str(md_path.resolve()))
        return trace_files

    def _save_summary(self, results: list[AttackResult]) -> None:
        summary = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orchestrator": self.orchestrator_type.value,
            "trials_per_scenario": self.trials_per_scenario,
            "results": [
                {
                    "name": r.scenario.name,
                    "category": r.scenario.category.value,
                    "asr": r.attack_success_rate,
                    "refusal_rate": r.refusal_rate,
                    "metadata_poison_rate": r.metadata_poison_rate,
                    "control_flow_hijack_rate": r.control_flow_hijack_rate,
                }
                for r in results
            ],
        }
        path = self.results_dir / "summary.json"
        path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        table_path = self.results_dir / "summary.txt"
        table_path.write_text(format_results_table(results), encoding="utf-8")
