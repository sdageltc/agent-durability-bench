<div align="center">

# agent-durability-bench 🛡️

**The Open Crash-Resilience & Durability Benchmark for Autonomous AI Coding Agents**

[![CI](https://github.com/sdageltc/agent-durability-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/sdageltc/agent-durability-bench/actions/workflows/ci.yml)
[![Benchmark](https://img.shields.io/badge/Benchmark-DCP--2.0-blue.svg)](https://github.com/sdageltc/agent-durability-bench)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-Live%20on%20Pages-brightgreen.svg)](https://sdageltc.github.io/agent-durability-bench/)

**[Durability Benchmark](https://github.com/sdageltc/agent-durability-bench)** • **[PR Verification Action](https://github.com/sdageltc/letitloop-action)** • **[Engine Core (v0.3.0)](https://github.com/sdageltc/letitloop)**

</div>

---

## The Core Question

**What happens when an AI coding agent crashes at Step 8 of a 10-step macro task?**

Existing benchmarks like SWE-bench evaluate whether an LLM can resolve an issue in a single run. They ignore operational durability:
- Does the framework resume from the exact last step, or does it re-execute from scratch, burning duplicate tokens?
- Does a mid-task `SIGKILL`, spot instance eviction, or unhandled exception corrupt local AST files?
- Are child and grandchild processes cleaned up, or do they leak into the host OS?

`agent-durability-bench` introduces the **Durability Conformance Protocol 2.0 (DCP-2.0)** to measure crash survival, state integrity, and resumption fidelity across autonomous agent frameworks under physical OS `SIGKILL` fault injection.

---

## Benchmark Comparison: Durability Bench vs. Industry Benchmarks

| Evaluation Dimension | **Durability Bench (DCP-2.0)** | **SWE-bench** | **GAIA** | **AgentBench** |
|---|:---:|:---:|:---:|:---:|
| **Primary Metric** | **Crash Survival & Resumption Fidelity** | Single-Shot Issue Resolution | Multimodal Tool Execution | Multi-Turn LLM Reasoning |
| **Failure Injection** | **Deterministic `SIGKILL`, OOM, Spot Eviction** | None (Runs to completion or timeout) | None | None |
| **State Corruption Check** | **AST Invariants & File Integrity Proofs** | Pytest Exit Code Only | Regex String Match | Environment Reward Score |
| **Cost to Run (100 Tasks)** | **$0.00 (Zero-API Synthetic Harness)** | ~$450.00 (Cloud LLM Tokens) | ~$120.00 (LLM API) | Variable |
| **Runtime Duration** | **< 15 Seconds** | 4–12 Hours | 1–3 Hours | 2–6 Hours |
| **External Dependencies** | **Zero (Pure Python `psutil` + `pytest`)** | Docker Daemon + Seed Repos | Custom Tool APIs | Docker Sandbox |

---

## DCP-2.0 Deterministic Kill-Window Taxonomy

The benchmark evaluates four critical execution failure sentinels:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DCP-2.0 FAILURE SENTINELS                       │
├─────────────────────────┬────────────────────────┬─────────────────────┤
│ 1. Mid-Step Execution   │ 2. Pre-Commit Snapshot │ 3. Sibling Rollback │
├─────────────────────────┼────────────────────────┼─────────────────────┤
│ Non-maskable SIGKILL    │ Kill before state WAL  │ Kill during parallel│
│ during active subprocess│ fsync; tests journal   │ worktree merge      │
│ code execution.         │ transaction recovery.  │ conflict resolution.│
└─────────────────────────┴────────────────────────┴─────────────────────┘
```

1. **Token Inflation (`ERR_TOKEN_INFLATION`)**: The agent resumes without state memory and repeats previously completed tool calls.
2. **State Corruption (`ERR_STATE_CORRUPT`)**: A mid-mutation termination leaves syntax errors or unparseable JSON files on disk.
3. **Orphan Process Leakage (`ERR_ORPHAN_PROCESS`)**: Worker processes, test subprocesses, or browser daemons remain active after parent process termination.

---

## Quickstart

### 1. Local Synthetic Harness (Zero Tokens, <2 Seconds)

Run the deterministic synthetic test harness to verify local runner integrity:

```bash
# Clone repository
git clone https://github.com/sdageltc/agent-durability-bench.git
cd agent-durability-bench

# Install in editable mode
pip install -e .

# Run test suite and crash injector
pytest tests/ -v

# Run synthetic crash injection on LetItLoop adapter
python -m harness.runner --framework letitloop --signal SIGKILL
```

### 2. Multi-Framework Durability Matrix

Benchmark external framework adapters and export updated leaderboard markdown:

```bash
# Run benchmark across all registered adapters
python -m harness.runner --all --export-json results/latest.json --export-markdown docs/index.md
```

---

## Live Leaderboard

Live benchmark results are updated continuously via GitHub Actions and published to [GitHub Pages](https://sdageltc.github.io/agent-durability-bench/):

| Framework | DCP-1.0 Score | Resumption Success | Zero-State Corruption | Process Cleanup |
|---|:---:|:---:|:---:|:---:|
| **LetItLoop v0.2.0** | **100%** | ✅ Pass (WAL Resume) | ✅ Pass (AST Splicer) | ✅ Pass (Job Object) |
| *LangGraph (Community)* | *Pending* | - | - | - |
| *AutoGen (Community)* | *Pending* | - | - | - |
| *CrewAI (Community)* | *Pending* | - | - | - |

---

## Adding Your Framework

We welcome adapters for open-source and commercial agent frameworks. Adding an adapter requires implementing three methods:

```python
from harness.adapters.base import BaseAdapter

class MyFrameworkAdapter(BaseAdapter):
    def setup_environment(self, workspace_path, task_spec):
        """Prepare target workspace and dependencies."""
        pass

    def execute_step(self, step_index):
        """Execute a discrete agent step."""
        pass

    def resume_from_crash(self, crash_checkpoint_path):
        """Resume execution from persistent state."""
        pass
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete adapter tutorial and conformance testing suite.

---

## License

MIT License. Copyright (c) 2026 sdageltc.
