import pathlib
import tempfile

from adapters.autogen_v04_adapter import AutoGenV04Adapter
from adapters.letitloop_adapter import LetItLoopAdapter
from harness.runner import ADAPTERS
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


def test_autogen_v04_adapter_is_registered_and_loses_state_after_sigkill(tmp_path):
    spec = SyntheticTaskSpec(
        task_id="autogen-v04-crash-001",
        steps=[
            SyntheticStep(
                step_id="step_1",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "step1.txt"),
                expected_content="first",
                simulated_token_cost=100,
            ),
            SyntheticStep(
                step_id="step_2",
                action_type="FILE_WRITE",
                target_path=str(tmp_path / "step2.txt"),
                expected_content="second",
                simulated_token_cost=150,
            ),
        ],
        kill_at_step_index=1,
        kill_signal="SIGKILL",
    )

    assert ADAPTERS["autogen_v04"] is AutoGenV04Adapter

    adapter = AutoGenV04Adapter(wal_dir=str(tmp_path / "wal"))
    pid, _ = adapter.start_task(spec)

    assert adapter.active_process is not None
    assert pid == adapter.active_process.pid
    assert adapter.active_process.poll() is not None
    assert (tmp_path / "step1.txt").read_text(encoding="utf-8") == "first"
    assert not (tmp_path / "step2.txt").exists()
    assert not (tmp_path / "wal" / f"{spec.task_id}.jsonl").exists()

    score = adapter.resume_task(spec)

    assert score.framework == "autogen_v04"
    assert score.resumed_successfully is False
    assert score.duplicate_token_waste_pct == 100.0
    assert score.state_corruption_detected is True
    assert score.final_verdict == "FAIL_DATA_LOSS"
