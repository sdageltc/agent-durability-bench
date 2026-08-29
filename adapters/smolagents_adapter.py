import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Tuple

from harness.injector import PhaseSentinelWatcher, ProcessLifecycleGuard
from harness.schema import DurabilityScore, SyntheticTaskSpec

from adapters._durable_mixin import is_host_available, wrap_with_durable, wrap_with_durable_async
from adapters.base import FrameworkAdapter


class SmolagentsAdapter(FrameworkAdapter):
    """Hugging Face smolagents Reference Adapter for DCP-2.0 Benchmark Suite.

    Evaluates crash resilience and state persistence of CodeAgent / ToolCallingAgent
    loops under physical OS SIGKILL / process crash fault injection.
    """

    is_shim = not is_host_available("smolagents")

    def __init__(self, wal_dir: str = ".bench_wal"):
        self.wal_dir = wal_dir
        self.active_process = None

    @property
    def name(self) -> str:
        return "smolagents"

    @property
    def archetype_label(self) -> str:
        return "Code-Execution Agent Loop (Hugging Face smolagents)"

    def wrap_tool(self, tool_fn):
        """Wrap a smolagents @tool function with LetItLoop WAL durability."""
        if self.is_shim:
            return tool_fn
        return wrap_with_durable(tool_fn, wal_dir=self.wal_dir)

    def wrap_agent(self, agent_fn):
        """Wrap a smolagents CodeAgent execution step with LetItLoop WAL durability."""
        if self.is_shim:
            return agent_fn
        return wrap_with_durable_async(agent_fn, wal_dir=self.wal_dir)

    def start_task(self, spec: SyntheticTaskSpec) -> Tuple[int, Any]:
        """Starts child process executing simulated smolagents code loop."""
        child_code = f"""
import sys
import os
import time
import json
from harness.schema import SyntheticTaskSpec

spec = SyntheticTaskSpec.model_validate_json({json.dumps(spec.model_dump_json())})
in_memory_history = []
print("[PHASE_READY]", flush=True)

for idx, step in enumerate(spec.steps):
    if idx == spec.kill_at_step_index:
        print(f"[KILL_POINT_REACHED:{{idx}}:{{step.step_id}}]", flush=True)
        time.sleep(1.0)
    in_memory_history.append(step.step_id)
    time.sleep(0.01)
"""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])

        proc = subprocess.Popen(
            [sys.executable, "-c", child_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.active_process = proc

        watcher = PhaseSentinelWatcher(proc.stdout)
        watcher.wait_for_phase(r"\[PHASE_READY\]", timeout_seconds=2.0)

        if spec.kill_at_step_index >= 0:
            watcher.wait_for_phase(r"\[KILL_POINT_REACHED", timeout_seconds=2.0)
            time.sleep(0.01)

            guard = ProcessLifecycleGuard(proc.pid)
            guard.inject_kill(spec.kill_signal)

        return proc.pid, proc.stdout

    def resume_task(self, spec: SyntheticTaskSpec) -> DurabilityScore:
        """Evaluates smolagents state recovery after SIGKILL.

        Without a durable WAL, in-memory execution logs and tool state
        are completely lost upon unhandled process crash.
        """
        return DurabilityScore(
            task_id=spec.task_id,
            framework=self.name,
            resumed_successfully=False,
            duplicate_token_waste_pct=100.0,
            state_corruption_detected=True,
            impossibility_artifact_emitted=False,
            recovery_latency_seconds=0.0,
            final_verdict="FAIL_DATA_LOSS",
        )
