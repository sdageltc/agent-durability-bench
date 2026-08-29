import pathlib
import tempfile

from adapters.letitloop_adapter import LetItLoopAdapter
from harness.schema import SyntheticStep, SyntheticTaskSpec


def test_letitloop_adapter_conformance_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        wal_dir = f"{tmpdir}/wal"
        spec = SyntheticTaskSpec(
            task_id="conformance-test-001",
            steps=[
                SyntheticStep(
                    step_id="step_1",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/f1.txt",
                    expected_content="c1",
                    simulated_token_cost=100,
                ),
                SyntheticStep(
                    step_id="step_2",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/f2.txt",
                    expected_content="c2",
                    simulated_token_cost=100,
                ),
            ],
            kill_at_step_index=0,  # Kill after step 1
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


def test_smolagents_adapter_conformance_data_loss():
    from adapters.smolagents_adapter import SmolagentsAdapter

    with tempfile.TemporaryDirectory() as tmpdir:
        wal_dir = f"{tmpdir}/wal"
        spec = SyntheticTaskSpec(
            task_id="smolagents-conformance-001",
            steps=[
                SyntheticStep(
                    step_id="step_1",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/f1.txt",
                    expected_content="c1",
                    simulated_token_cost=100,
                ),
                SyntheticStep(
                    step_id="step_2",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/f2.txt",
                    expected_content="c2",
                    simulated_token_cost=100,
                ),
            ],
            kill_at_step_index=0,
        )

        adapter = SmolagentsAdapter(wal_dir=wal_dir)
        pid, watcher = adapter.start_task(spec)
        assert pid > 0

        score = adapter.resume_task(spec)
        assert score.framework == "smolagents"
        assert score.resumed_successfully is False
        assert score.duplicate_token_waste_pct == 100.0
        assert score.state_corruption_detected is True
        assert score.final_verdict == "FAIL_DATA_LOSS"


def test_smolagents_adapter_wrap_tool_durable():
    from adapters.smolagents_adapter import SmolagentsAdapter

    adapter = SmolagentsAdapter()
    dummy_tool = lambda x: x * 2  # noqa: E731
    wrapped = adapter.wrap_tool(dummy_tool)
    assert callable(wrapped)
    assert wrapped(5) == 10
