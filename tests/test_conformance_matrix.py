import pathlib
import tempfile

from harness.runner import ADAPTERS, PRIMARY_ARCHETYPES, DurabilityBenchmarkRunner
from harness.schema import SyntheticStep, SyntheticTaskSpec


def test_all_archetypes_registered():
    for arch in PRIMARY_ARCHETYPES:
        assert arch in ADAPTERS
    assert "atomic_wal" in ADAPTERS
    assert "snapshot_graph" in ADAPTERS
    assert "in_memory_loop" in ADAPTERS
    assert "unmanaged_script" in ADAPTERS


def test_durability_matrix_sweep_math():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = DurabilityBenchmarkRunner(output_dir=tmpdir, wal_dir=f"{tmpdir}/wal")

        task = SyntheticTaskSpec(
            task_id="test-matrix-task",
            steps=[
                SyntheticStep(
                    step_id="s1",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/t1.txt",
                    expected_content="a",
                    simulated_token_cost=100,
                ),
                SyntheticStep(
                    step_id="s2",
                    action_type="FILE_WRITE",
                    target_path=f"{tmpdir}/t2.txt",
                    expected_content="b",
                    simulated_token_cost=100,
                ),
            ],
            kill_at_step_index=0,
        )

        results = runner.run_matrix_sweep(tasks=[task])
        assert len(results) == len(PRIMARY_ARCHETYPES)

        leaderboard_data = runner.compile_leaderboard(results)
        assert leaderboard_data["protocol_version"] == "DCP-2.0"
        assert "methodology" in leaderboard_data

        # atomic_wal must be rank 1 with 100% recovery and 0% waste
        rank1 = leaderboard_data["leaderboard"][0]
        assert rank1["framework"] == "atomic_wal"
        assert rank1["recovery_rate_pct"] == 100.0
        assert rank1["avg_duplicate_token_waste_pct"] == 0.0
        assert rank1["dcp_status"] == "CONFORMANT"


def test_export_markdown_leaderboard():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = DurabilityBenchmarkRunner(output_dir=tmpdir, wal_dir=f"{tmpdir}/wal")
        results = runner.run_matrix_sweep()
        leaderboard_data = runner.compile_leaderboard(results)

        md_path = f"{tmpdir}/docs/index.md"
        runner.export_markdown_leaderboard(leaderboard_data, md_path)

        content = pathlib.Path(md_path).read_text(encoding="utf-8")
        assert "Durability Conformance Protocol (DCP-2.0) Leaderboard" in content
        assert "Atomic WAL Engine" in content
        assert "Methodological Scope Disclosure" in content
        assert "🟢 CONFORMANT" in content
        assert "🔴 NON-CONFORMANT" in content
