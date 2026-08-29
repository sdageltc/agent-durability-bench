import json
import os
import subprocess
import sys
import time
from pathlib import Path

from adapters.letitloop_adapter import LetItLoopAdapter
from harness.injector import PhaseSentinelWatcher, ProcessLifecycleGuard
from harness.schema import DurabilityScore, SyntheticStep, SyntheticTaskSpec


def test_real_subprocess_crash_and_wal_recovery(tmp_path):
    wal_dir = tmp_path / "wal_test"
    wal_dir.mkdir(parents=True, exist_ok=True)

    spec = SyntheticTaskSpec(
        task_id="bench-crash-test-001",
        steps=[
            SyntheticStep(
                step_id="step_1",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "f1.txt"),
                expected_content="stage_1",
                simulated_token_cost=100,
            ),
            SyntheticStep(
                step_id="step_2",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "f2.txt"),
                expected_content="stage_2",
                simulated_token_cost=150,
            ),
            SyntheticStep(
                step_id="step_3",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "f3.txt"),
                expected_content="stage_3",
                simulated_token_cost=200,
            ),
            SyntheticStep(
                step_id="step_4",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "f4.txt"),
                expected_content="stage_4",
                simulated_token_cost=250,
            ),
        ],
        kill_at_step_index=2,  # Kill at step 2
        kill_signal="SIGKILL",
    )

    # Subprocess script to execute steps and output phase sentinels
    child_script = tmp_path / "child_runner.py"
    child_script.write_text(
        f'''
import sys
import time
from harness.schema import SyntheticTaskSpec
from harness.synthetic_engine import SyntheticTaskRunner

spec = SyntheticTaskSpec.model_validate_json({json.dumps(spec.model_dump_json())})
runner = SyntheticTaskRunner(spec, wal_dir=r"{wal_dir}")
print("[PHASE_READY]", flush=True)

# Run until target kill step
runner.run_until_kill_or_complete()
print("[PHASE_DONE]", flush=True)
''',
        encoding="utf-8",
    )

    # 1. Spawn live subprocess with unbuffered output
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)

    proc = subprocess.Popen(
        [sys.executable, str(child_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
    )

    watcher = PhaseSentinelWatcher(proc.stdout, r"\[PHASE_READY\]")
    ready = watcher.wait_for_phase(timeout_seconds=5.0)
    assert ready, "Subprocess failed to signal ready state."

    # Give subprocess 100ms to hit kill point and write WAL
    time.sleep(0.2)

    # 2. Inject Process Tree Kill
    guard = ProcessLifecycleGuard(proc.pid)
    killed = guard.inject_kill("SIGKILL")
    assert killed or proc.poll() is not None, "Process was not successfully terminated."

    # 3. Verify WAL state was committed up to step 2
    wal_file = wal_dir / f"{spec.task_id}.jsonl"
    assert wal_file.exists(), f"WAL file {wal_file} was not written."

    wal_lines = [json.loads(line) for line in wal_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(wal_lines) == 2, f"Expected 2 completed WAL steps, got {len(wal_lines)}"

    # 4. Resume task using LetItLoopAdapter
    adapter = LetItLoopAdapter(wal_dir=str(wal_dir))
    score: DurabilityScore = adapter.resume_task(spec)

    assert score.resumed_successfully is True
    assert score.duplicate_token_waste_pct == 0.0
    assert score.state_corruption_detected is False
    assert score.final_verdict == "PASS"

    # Assert remaining files created
    assert (tmp_path / "f1.txt").exists()
    assert (tmp_path / "f2.txt").exists()
    assert (tmp_path / "f3.txt").exists()
    assert (tmp_path / "f4.txt").exists()
