"""AutoGen AgentChat v0.4+ adapter for the in-memory durability baseline.

The benchmark loop is deterministic and API-free. It mirrors the loss of
conversation/task history when an AutoGen worker is killed, while optional
wrappers let users make individual async agents or sync tools durable.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Tuple

from adapters._durable_mixin import is_host_available, wrap_with_durable, wrap_with_durable_async
from adapters.base import FrameworkAdapter
from harness.injector import PhaseSentinelWatcher, ProcessLifecycleGuard
from harness.schema import DurabilityScore, SyntheticTaskSpec


class AutoGenV04Adapter(FrameworkAdapter):
    """Benchmark AutoGen AgentChat 0.4+ as an in-memory event-driven loop."""

    is_shim = not is_host_available("autogen_agentchat")

    def __init__(self, wal_dir: str = ".bench_wal"):
        self.wal_dir = wal_dir
        self.active_process: subprocess.Popen | None = None
        self._crash_injected = False

    @property
    def name(self) -> str:
        return "autogen_v04"

    @property
    def archetype_label(self) -> str:
        return "Microsoft AutoGen AgentChat v0.4+ (In-Memory Event Loop)"

    def wrap_tool(self, tool_fn):
        """Wrap a synchronous tool function with LetItLoop durability when installed."""
        if self.is_shim:
            return tool_fn
        return wrap_with_durable(tool_fn, wal_dir=self.wal_dir)

    def wrap_agent(self, agent_fn):
        """Wrap an async agent step with LetItLoop durability when installed."""
        if self.is_shim:
            return agent_fn
        return wrap_with_durable_async(agent_fn, wal_dir=self.wal_dir)

    def start_task(self, spec: SyntheticTaskSpec) -> Tuple[int, Any]:
        if spec.kill_at_step_index >= len(spec.steps):
            raise ValueError("kill_at_step_index must reference a task step or be -1")

        task_json = json.dumps(spec.model_dump_json())
        child_code = f'''
import asyncio
import pathlib
from harness.schema import SyntheticTaskSpec

spec = SyntheticTaskSpec.model_validate_json({task_json})

async def run_agentchat_loop():
    conversation_history = []
    print("[PHASE_READY]", flush=True)
    for index, step in enumerate(spec.steps):
        print("[PHASE:STEP_" + str(index) + "_" + step.step_id + "]", flush=True)
        if index == spec.kill_at_step_index:
            print("[KILL_POINT_REACHED:" + str(index) + ":" + step.step_id + "]", flush=True)
            await asyncio.sleep(30.0)

        if ".." in pathlib.PurePath(step.target_path).parts:
            raise ValueError("sandbox violation: target_path contains '..'")

        if step.action_type == "FILE_WRITE":
            target = pathlib.Path(step.target_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(step.expected_content, encoding="utf-8")
        elif step.action_type == "INVARIANT_CHECK":
            target = pathlib.Path(step.target_path)
            if not target.exists() or target.read_text(encoding="utf-8") != step.expected_content:
                raise AssertionError("Invariant check failed for step " + step.step_id)

        conversation_history.append(step.step_id)
        await asyncio.sleep(0.01)

    print("[PHASE_COMPLETE]", flush=True)

asyncio.run(run_agentchat_loop())
'''
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        root = str(Path(__file__).resolve().parents[1])
        env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        proc = subprocess.Popen(
            [sys.executable, "-c", child_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.active_process = proc
        self._crash_injected = False

        watcher = PhaseSentinelWatcher(proc.stdout)
        if not watcher.wait_for_phase(r"\[PHASE_READY\]", timeout_seconds=5.0):
            proc.kill()
            proc.wait(timeout=3.0)
            raise RuntimeError("AutoGen AgentChat simulation failed to signal readiness")

        should_inject_kill = 0 <= spec.kill_at_step_index < len(spec.steps)
        if should_inject_kill:
            reached_kill_point = watcher.wait_for_phase(r"\[KILL_POINT_REACHED", timeout_seconds=5.0)
            if not reached_kill_point:
                proc.kill()
                proc.wait(timeout=3.0)
                raise RuntimeError("AutoGen AgentChat simulation did not reach the configured kill point")

            killed = ProcessLifecycleGuard(proc.pid).inject_kill(spec.kill_signal)
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3.0)
            self._crash_injected = bool(killed and proc.returncode is not None and proc.returncode != 0)
        else:
            completed = watcher.wait_for_phase(r"\[PHASE_COMPLETE\]", timeout_seconds=float(spec.timeout_seconds))
            if not completed:
                proc.kill()
                proc.wait(timeout=3.0)
                raise RuntimeError("AutoGen AgentChat simulation timed out")
            proc.wait(timeout=3.0)

        return proc.pid, proc.stdout

    def resume_task(self, spec: SyntheticTaskSpec) -> DurabilityScore:
        if self._crash_injected:
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

        completed = self.active_process is not None and self.active_process.returncode == 0
        return DurabilityScore(
            task_id=spec.task_id,
            framework=self.name,
            resumed_successfully=completed,
            duplicate_token_waste_pct=0.0 if completed else 100.0,
            state_corruption_detected=not completed,
            impossibility_artifact_emitted=False,
            recovery_latency_seconds=0.0,
            final_verdict="PASS" if completed else "FAIL_DATA_LOSS",
        )
