"""Hugging Face smolagents Reference Specification for DCP-2.0 Benchmark Suite.

This fixture defines the expected test contract for community contributors
implementing `adapters/smolagents_adapter.py` (Issue #3).
"""

from harness.schema import DurabilityScore, SyntheticStep, SyntheticTaskSpec


def create_smolagents_synthetic_task(task_id: str = "smolagents-spec-001") -> SyntheticTaskSpec:
    """Creates a standard 3-step synthetic task simulating smolagents tool calling."""
    return SyntheticTaskSpec(
        task_id=task_id,
        steps=[
            SyntheticStep(
                step_id="step_1",
                action_type="FILE_WRITE",
                target_path="build/f1.txt",
                expected_content="c1",
                simulated_token_cost=100,
            ),
            SyntheticStep(
                step_id="step_2",
                action_type="FILE_WRITE",
                target_path="build/f2.txt",
                expected_content="c2",
                simulated_token_cost=150,
            ),
            SyntheticStep(
                step_id="step_3",
                action_type="FILE_WRITE",
                target_path="build/f3.txt",
                expected_content="c3",
                simulated_token_cost=200,
            ),
        ],
        kill_at_step_index=1,
        kill_signal="SIGKILL",
    )


def assert_smolagents_unmanaged_data_loss(score: DurabilityScore) -> None:
    """Verifies that unmanaged in-memory execution loses state under SIGKILL."""
    assert score.framework == "smolagents"
    assert score.resumed_successfully is False
    assert score.duplicate_token_waste_pct == 100.0
    assert score.state_corruption_detected is True
    assert score.final_verdict == "FAIL_DATA_LOSS"
