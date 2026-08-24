import tempfile
import pathlib
import pytest
from adapters.letitloop_adapter import LetItLoopAdapter
from harness.schema import SyntheticTaskSpec, SyntheticStep

def test_letitloop_adapter_conformance_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        wal_dir = f"{tmpdir}/wal"
        spec = SyntheticTaskSpec(
            task_id="conformance-test-001",
            steps=[
                SyntheticStep(step_id="step_1", action_type="FILE_WRITE", target_path=f"{tmpdir}/f1.txt", expected_content="c1", simulated_token_cost=100),
                SyntheticStep(step_id="step_2", action_type="FILE_WRITE", target_path=f"{tmpdir}/f2.txt", expected_content="c2", simulated_token_cost=100),
            ],
            kill_at_step_index=0 # Kill after step 1
        )
        
        adapter = LetItLoopAdapter(wal_dir=wal_dir)
        adapter.start_task(spec)
        
        # Now trigger resume
        score = adapter.resume_task(spec)
        
        assert score.framework == "letitloop"
        assert score.resumed_successfully is True
        assert score.duplicate_token_waste_pct == 0.0
        assert score.state_corruption_detected is False
        assert score.final_verdict == "PASS"
        assert pathlib.Path(f"{tmpdir}/f1.txt").read_text(encoding="utf-8") == "c1"
        assert pathlib.Path(f"{tmpdir}/f2.txt").read_text(encoding="utf-8") == "c2"
