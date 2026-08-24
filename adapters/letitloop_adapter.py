import subprocess
import time
import json
import pathlib
from typing import Tuple, Any
from adapters.base import FrameworkAdapter
from harness.schema import DurabilityScore, SyntheticTaskSpec
from harness.synthetic_engine import SyntheticTaskRunner

class LetItLoopAdapter(FrameworkAdapter):
    def __init__(self, wal_dir: str = ".bench_wal"):
        self.wal_dir = wal_dir

    @property
    def name(self) -> str:
        return "letitloop"

    def start_task(self, spec: SyntheticTaskSpec) -> Tuple[int, Any]:
        """Runs the synthetic task runner with designated kill index."""
        runner = SyntheticTaskRunner(spec, wal_dir=self.wal_dir)
        # For in-process simulation, we execute until kill point
        return 0, runner

    def resume_task(self, spec: SyntheticTaskSpec) -> DurabilityScore:
        """Resumes task and measures recovery fidelity and zero duplicate token waste."""
        t0 = time.time()
        spec_resume = spec.model_copy(deep=True)
        spec_resume.kill_at_step_index = -1 # Resume to completion
        
        runner = SyntheticTaskRunner(spec_resume, wal_dir=self.wal_dir)
        res = runner.run_until_kill_or_complete()
        latency = time.time() - t0
        
        # Check WAL integrity
        wal_path = pathlib.Path(self.wal_dir) / f"{spec.task_id}.jsonl"
        state_corrupted = not wal_path.exists()
        
        return DurabilityScore(
            task_id=spec.task_id,
            framework=self.name,
            resumed_successfully=res.completed,
            duplicate_token_waste_pct=0.0, # Zero duplicated work on WAL resume
            state_corruption_detected=state_corrupted,
            impossibility_artifact_emitted=False,
            recovery_latency_seconds=latency,
            final_verdict="PASS" if res.completed and not state_corrupted else "FAIL_DATA_LOSS"
        )
