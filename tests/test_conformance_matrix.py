import tempfile
import pathlib
import json
import pytest
from harness.runner import DurabilityBenchmarkRunner, ADAPTERS
from harness.schema import SyntheticTaskSpec, SyntheticStep

def test_all_adapters_registered():
    assert "letitloop" in ADAPTERS
    assert "langgraph" in ADAPTERS
    assert "autogen" in ADAPTERS
    assert "crewai" in ADAPTERS
    assert "raw_python" in ADAPTERS

def test_durability_matrix_sweep_math():
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = DurabilityBenchmarkRunner(output_dir=tmpdir, wal_dir=f"{tmpdir}/wal")
        
        task = SyntheticTaskSpec(
            task_id="test-matrix-task",
            steps=[
                SyntheticStep(step_id="s1", action_type="FILE_WRITE", target_path=f"{tmpdir}/t1.txt", expected_content="a", simulated_token_cost=100),
                SyntheticStep(step_id="s2", action_type="FILE_WRITE", target_path=f"{tmpdir}/t2.txt", expected_content="b", simulated_token_cost=100),
            ],
            kill_at_step_index=0
        )
        
        results = runner.run_matrix_sweep(tasks=[task])
        assert len(results) == len(ADAPTERS)
        
        leaderboard_data = runner.compile_leaderboard(results)
        assert leaderboard_data["protocol_version"] == "DCP-1.0"
        
        # letitloop must be rank 1 with 100% recovery and 0% waste
        rank1 = leaderboard_data["leaderboard"][0]
        assert rank1["framework"] == "letitloop"
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
        assert "Durability Conformance Protocol (DCP-1.0) Leaderboard" in content
        assert "letitloop" in content
        assert "🟢 CONFORMANT" in content
        assert "🔴 NON-CONFORMANT" in content
