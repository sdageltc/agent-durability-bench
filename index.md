# 🏆 Agent Durability Benchmark Leaderboard

*Conforming to the [arXiv:2608.03836 Resume Contract](https://arxiv.org/abs/2608.03836) Specification*

Testing autonomous agent crash-resilience across `SIGKILL`, OOM, and process failure scenarios.

| Framework     | Benchmark Scenario   | Recovery Success   | Token Waste %   | State Corruption   | Conformance Verdict   |
|---------------|----------------------|--------------------|-----------------|--------------------|-----------------------|
| **letitloop** | bench-standard-001   | ✅ YES             | 0.0%            | 🛡️ 0 Corruption    | **PASS**              |

---

## Benchmark Invariants

- **0% Token Waste**: Agents must resume from their exact last committed checkpoint without re-executing completed work.
- **Zero State Corruption**: No partial writes or invalid JSON contracts remaining on disk.
- **Open Conformance**: All framework maintainers are invited to [submit an adapter](https://github.com/sdageltc/agent-durability-bench/blob/main/CONTRIBUTING.md).

*Updated automatically via GitHub Actions Nightly CI Matrix.*
