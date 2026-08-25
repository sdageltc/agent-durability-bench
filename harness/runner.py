import os
import sys
import time
import json
import pathlib
import argparse
from typing import List, Dict, Any, Optional

from harness.schema import SyntheticTaskSpec, SyntheticStep, DurabilityScore
from adapters.base import FrameworkAdapter
from adapters.letitloop_adapter import LetItLoopAdapter
from adapters.langgraph_adapter import LangGraphAdapter
from adapters.autogen_adapter import AutoGenAdapter
from adapters.crewai_adapter import CrewAIAdapter
from adapters.raw_python_adapter import RawPythonAdapter

ADAPTERS: Dict[str, type] = {
    "letitloop": LetItLoopAdapter,
    "langgraph": LangGraphAdapter,
    "autogen": AutoGenAdapter,
    "crewai": CrewAIAdapter,
    "raw_python": RawPythonAdapter
}

class DurabilityBenchmarkRunner:
    def __init__(self, output_dir: str = "results", wal_dir: str = ".bench_wal"):
        self.output_dir = pathlib.Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.wal_dir = wal_dir

    def run_durability_trial(
        self,
        framework_name: str,
        task_spec: SyntheticTaskSpec
    ) -> DurabilityScore:
        adapter_cls = ADAPTERS.get(framework_name.lower())
        if not adapter_cls:
            raise ValueError(f"Unknown framework adapter: {framework_name}. Available: {list(ADAPTERS.keys())}")

        adapter: FrameworkAdapter = adapter_cls(wal_dir=self.wal_dir)
        adapter.start_task(task_spec)
        return adapter.resume_task(task_spec)

    def run_matrix_sweep(self, tasks: Optional[List[SyntheticTaskSpec]] = None) -> List[DurabilityScore]:
        if not tasks:
            tasks = [
                SyntheticTaskSpec(
                    task_id="dcp-micro-3step",
                    steps=[
                        SyntheticStep(step_id="step_1", action_type="FILE_WRITE", target_path="build/f1.txt", expected_content="c1", simulated_token_cost=100),
                        SyntheticStep(step_id="step_2", action_type="FILE_WRITE", target_path="build/f2.txt", expected_content="c2", simulated_token_cost=150),
                        SyntheticStep(step_id="step_3", action_type="FILE_WRITE", target_path="build/f3.txt", expected_content="c3", simulated_token_cost=200),
                    ],
                    kill_at_step_index=1,
                    kill_signal="SIGKILL"
                ),
                SyntheticTaskSpec(
                    task_id="dcp-pipeline-5step",
                    steps=[
                        SyntheticStep(step_id="s1", action_type="FILE_WRITE", target_path="build/p1.txt", expected_content="d1", simulated_token_cost=120),
                        SyntheticStep(step_id="s2", action_type="FILE_WRITE", target_path="build/p2.txt", expected_content="d2", simulated_token_cost=180),
                        SyntheticStep(step_id="s3", action_type="FILE_WRITE", target_path="build/p3.txt", expected_content="d3", simulated_token_cost=250),
                        SyntheticStep(step_id="s4", action_type="FILE_WRITE", target_path="build/p4.txt", expected_content="d4", simulated_token_cost=300),
                        SyntheticStep(step_id="s5", action_type="FILE_WRITE", target_path="build/p5.txt", expected_content="d5", simulated_token_cost=350),
                    ],
                    kill_at_step_index=2,
                    kill_signal="SIGKILL"
                )
            ]

        results = []
        for fw in ADAPTERS.keys():
            for task in tasks:
                score = self.run_durability_trial(fw, task)
                results.append(score)
        return results

    def compile_leaderboard(self, results: List[DurabilityScore]) -> Dict[str, Any]:
        # Group by framework
        summary: Dict[str, Dict[str, Any]] = {}
        for r in results:
            if r.framework not in summary:
                summary[r.framework] = {
                    "framework": r.framework,
                    "total_trials": 0,
                    "passed_trials": 0,
                    "avg_token_waste_pct": 0.0,
                    "avg_recovery_latency_ms": 0.0,
                    "state_corruptions": 0
                }
            s = summary[r.framework]
            s["total_trials"] += 1
            if r.resumed_successfully:
                s["passed_trials"] += 1
            s["avg_token_waste_pct"] += r.duplicate_token_waste_pct
            s["avg_recovery_latency_ms"] += (r.recovery_latency_seconds * 1000.0)
            if r.state_corruption_detected:
                s["state_corruptions"] += 1

        leaderboard = []
        for fw, s in summary.items():
            n = s["total_trials"] or 1
            recovery_rate = (s["passed_trials"] / n) * 100.0
            avg_waste = s["avg_token_waste_pct"] / n
            avg_latency = s["avg_recovery_latency_ms"] / n
            leaderboard.append({
                "framework": fw,
                "recovery_rate_pct": round(recovery_rate, 1),
                "avg_duplicate_token_waste_pct": round(avg_waste, 1),
                "avg_recovery_latency_ms": round(avg_latency, 2),
                "state_corruptions": s["state_corruptions"],
                "dcp_status": "CONFORMANT" if recovery_rate == 100.0 and avg_waste < 5.0 else "NON_CONFORMANT"
            })

        # Sort: Highest recovery rate, lowest token waste
        leaderboard.sort(key=lambda x: (-x["recovery_rate_pct"], x["avg_duplicate_token_waste_pct"]))
        return {
            "protocol_version": "DCP-1.0",
            "timestamp": time.time(),
            "leaderboard": leaderboard
        }

    def export_markdown_leaderboard(self, leaderboard_data: Dict[str, Any], target_path: str):
        p = pathlib.Path(target_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            "# Durability Conformance Protocol (DCP-1.0) Leaderboard 🏆",
            "",
            "Independent empirical crash-resilience matrix for AI coding agents under abrupt `SIGKILL` fault injection.",
            "",
            "| Rank | Framework / Engine | Crash Recovery ($R_{crash}$) | Duplicate Token Waste ($W_{token}$) | Resumption Latency | DCP-1.0 Status |",
            "|:---:|---|:---:|:---:|:---:|:---:|"
        ]
        
        for idx, row in enumerate(leaderboard_data["leaderboard"], 1):
            badge = "🟢 CONFORMANT" if row["dcp_status"] == "CONFORMANT" else "🔴 NON-CONFORMANT"
            status_icon = "🥇" if idx == 1 else ("🥈" if idx == 2 else f"**{idx}**")
            lines.append(
                f"| {status_icon} | **`{row['framework']}`** | `{row['recovery_rate_pct']}%` | `{row['avg_duplicate_token_waste_pct']}%` | `{row['avg_recovery_latency_ms']} ms` | {badge} |"
            )
            
        lines.extend([
            "",
            "---",
            "### Methodology & Protocol Invariants",
            "1. **Ungraceful Crash Injection**: Processes are halted midway through atomic steps using non-maskable `SIGKILL`.",
            "2. **Zero-API Simulation**: Deterministic synthetic task engine with zero cloud latency or flakiness.",
            "3. **Token Accounting**: Duplicated tool executions on resumed tasks are tracked as waste tokens.",
            "",
            "*Generated by `agent-durability-bench`.*"
        ])
        
        p.write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Agent Durability Benchmark Runner (DCP-1.0)")
    parser.add_argument("--matrix", action="store_true", help="Run full cross-framework matrix sweep")
    parser.add_argument("--framework", default="letitloop", help="Target framework adapter")
    parser.add_argument("--export-json", default="results/leaderboard.json", help="Path to export results JSON")
    parser.add_argument("--export-markdown", default="docs/index.md", help="Path to export markdown leaderboard")
    args = parser.parse_args()

    runner = DurabilityBenchmarkRunner()
    
    if args.matrix:
        print("=" * 60)
        print("RUNNING DCP-1.0 FULL FRAMEWORK MATRIX SWEEP")
        print("=" * 60)
        results = runner.run_matrix_sweep()
        leaderboard_data = runner.compile_leaderboard(results)
        
        # Export
        json_path = pathlib.Path(args.export_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(leaderboard_data, indent=2), encoding="utf-8")
        
        runner.export_markdown_leaderboard(leaderboard_data, args.export_markdown)
        
        print("\n" + json.dumps(leaderboard_data, indent=2))
        print(f"\nLeaderboard exported to {args.export_json} and {args.export_markdown}")
    else:
        spec = SyntheticTaskSpec(
            task_id="bench-standard-001",
            steps=[
                SyntheticStep(step_id="step_1", action_type="FILE_WRITE", target_path="build/f1.txt", expected_content="stage_1", simulated_token_cost=100),
                SyntheticStep(step_id="step_2", action_type="FILE_WRITE", target_path="build/f2.txt", expected_content="stage_2", simulated_token_cost=150),
                SyntheticStep(step_id="step_3", action_type="FILE_WRITE", target_path="build/f3.txt", expected_content="stage_3", simulated_token_cost=200),
            ],
            kill_at_step_index=1,
            kill_signal="SIGKILL"
        )
        score = runner.run_durability_trial(args.framework, spec)
        print("\n[BENCHMARK TRIAL COMPLETED]")
        print(json.dumps(score.model_dump(), indent=2))

if __name__ == "__main__":
    main()
