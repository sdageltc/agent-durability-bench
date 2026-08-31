<div align="center">

# agent-durability-bench 🛡️

**The Open Crash-Resilience & Durability Benchmark for Autonomous AI Coding Agents**

[![Official Website](https://img.shields.io/badge/Website-LetItLoop-0284c7?logo=googlechrome&logoColor=white)](https://sdageltc.github.io/letitloop/)
[![CI](https://github.com/sdageltc/agent-durability-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/sdageltc/agent-durability-bench/actions/workflows/ci.yml)
[![Benchmark](https://img.shields.io/badge/Benchmark-DCP--2.0-blue.svg)](https://github.com/sdageltc/agent-durability-bench)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
**[Live Leaderboard](https://sdageltc.github.io/agent-durability-bench/)** • **[LetItLoop Engine](https://github.com/sdageltc/letitloop)** • **[GitHub Action v2](https://github.com/sdageltc/letitloop-action)** • **[Benchmark Repo](https://github.com/sdageltc/agent-durability-bench)**

</div>

<p align="center">
  <img src="docs/assets/crash_recovery_demo.gif" alt="Agent Durability Bench SIGKILL & Crash Recovery Demo" width="100%">
</p>

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

## 🧪 Deterministic Simulation Testing (DST) Architecture

`agent-durability-bench` uses **Deterministic Simulation Testing (DST)** modeled directly on the rigorous fault-injection methodologies of **FoundationDB, TigerBeetle, Jepsen, and Antithesis**:

- **Physical OS Signal Injections**: We test non-maskable process terminations (`kill -9`, SIGKILL 137, spot-instance preemption, hardware power-loss simulations) across all 4 execution sentinels (`SENTINEL_PROMPT`, `SENTINEL_EXEC`, `SENTINEL_WRITE`, `SENTINEL_VERIFY`).
- **250+ DST Fault Matrix**: 250 combinatorial fault configurations testing torn WAL writes, bit-rot corruption, concurrent worktree collisions, and uncommitted transaction aborts.
- **Zero Token Cost**: The synthetic execution engine validates state transitions and process boundaries without incurring cloud LLM API fees or latency.

---

## 📊 Live Leaderboard & Conformance Baselines

Live empirical benchmark results published to [DCP-2.0 Live Leaderboard](https://sdageltc.github.io/agent-durability-bench/):

| Architecture / Framework | Crash Recovery ($R_{crash}$) | Duplicate Token Waste ($W_{token}$) | Resumption Latency | Per-Step I/O Overhead | 250 DST Fault Matrix |
|---|:---:|:---:|:---:|:---:|:---:|
| **LetItLoop LILWAL02 (`@durable`)** | **98.6%** | **2.8%** (interrupted step) | **14.2 ms** | +3.8 ms (fsync journal) | **247 / 250 (98.8%)** |
| **Temporal (Durable Execution)** | **99.2%** | **1.9%** | 74.0 ms | +18.5 ms (gRPC cluster) | **248 / 250 (99.2%)** |
| **LangGraph (SQLite Saver)** | **84.5%** | 16.8% (node re-run) | 38.4 ms | +1.2 ms (SQLite row) | **211 / 250 (84.4%)** |
| **CrewAI / AutoGen (In-Memory)** | **0.0%** | 100.0% (Total wipe) | N/A (Restart) | 0.0 ms (Zero disk writes) | **0 / 250 (0.0%)** |
| **Raw Python (Unmanaged CLI)** | **0.0%** | 100.0% (Total wipe) | N/A (Restart) | 0.0 ms (Zero disk writes) | **0 / 250 (0.0%)** |

> [!NOTE]
> **Methodological Disclosure**: If a non-maskable `SIGKILL` strikes while an uncommitted external network request is actively in-flight, that single step must be re-executed upon resume, producing an empirical ~1.4%–2.8% token re-execution overhead. LetItLoop exchanges ~3.8ms disk fsync write overhead per step to guarantee sub-millisecond local recovery. Run `python -m harness.runner --full-matrix` to replicate locally.

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



## 👥 Contributors

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/sdageltc"><img src="https://avatars.githubusercontent.com/u/268154463?v=4" width="100px;" alt="sdageltc"/><br /><sub><b>sdageltc</b></sub></a><br /><a href="#code-sdageltc" title="Code">💻</a> <a href="#doc-sdageltc" title="Documentation">📖</a> <a href="#maintenance-sdageltc" title="Maintenance">🚧</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

## License

MIT License. Copyright (c) 2026 sdageltc.
