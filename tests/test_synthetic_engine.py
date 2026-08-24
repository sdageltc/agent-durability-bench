import tempfile
import pathlib
import pytest
from harness.synthetic_engine import SyntheticTaskRunner
from harness.schema import SyntheticTaskSpec, SyntheticStep

def test_synthetic_task_runs_and_writes_state():
    with tempfile.TemporaryDirectory() as tmpdir:
        spec = SyntheticTaskSpec(
            task_id="test-001",
            steps=[
                SyntheticStep(step_id="s1", action_type="FILE_WRITE", target_path=f"{tmpdir}/f1.txt", expected_content="hello", simulated_token_cost=50),
                SyntheticStep(step_id="s2", action_type="FILE_WRITE", target_path=f"{tmpdir}/f2.txt", expected_content="world", simulated_token_cost=50),
            ],
            kill_at_step_index=-1,
            kill_signal="SIGKILL"
        )
        runner = SyntheticTaskRunner(spec, wal_dir=f"{tmpdir}/wal")
        res = runner.run_until_kill_or_complete()
        assert res.completed is True
        assert res.total_tokens == 100
        assert pathlib.Path(f"{tmpdir}/f1.txt").read_text(encoding="utf-8") == "hello"
        assert pathlib.Path(f"{tmpdir}/f2.txt").read_text(encoding="utf-8") == "world"

def test_synthetic_task_resumes_from_wal_without_duplicate_work():
    with tempfile.TemporaryDirectory() as tmpdir:
        wal_dir = f"{tmpdir}/wal"
        # Pre-populate step 1 in WAL
        spec = SyntheticTaskSpec(
            task_id="test-resume-002",
            steps=[
                SyntheticStep(step_id="s1", action_type="FILE_WRITE", target_path=f"{tmpdir}/f1.txt", expected_content="first", simulated_token_cost=50),
                SyntheticStep(step_id="s2", action_type="FILE_WRITE", target_path=f"{tmpdir}/f2.txt", expected_content="second", simulated_token_cost=50),
            ],
            kill_at_step_index=-1
        )
        
        # Run step 1 only
        spec_partial = SyntheticTaskSpec(
            task_id="test-resume-002",
            steps=[spec.steps[0]],
            kill_at_step_index=-1
        )
        runner1 = SyntheticTaskRunner(spec_partial, wal_dir=wal_dir)
        runner1.run_until_kill_or_complete()
        
        # Now run full spec with runner 2
        runner2 = SyntheticTaskRunner(spec, wal_dir=wal_dir)
        res = runner2.run_until_kill_or_complete()
        
        assert res.completed is True
        # s1 should have been skipped, only s2 tokens counted in second run
        assert res.total_tokens == 50
        assert pathlib.Path(f"{tmpdir}/f1.txt").read_text(encoding="utf-8") == "first"
        assert pathlib.Path(f"{tmpdir}/f2.txt").read_text(encoding="utf-8") == "second"
