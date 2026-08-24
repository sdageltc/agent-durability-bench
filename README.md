# agent-durability-bench 🛡️

**The open crash-resilience and durability benchmark for autonomous AI agent frameworks.**

What happens when an agent worker crashes mid-execution (`kill -9`, spot VM eviction, unhandled exception, OOM kill)?
- Does the framework resume from the exact last step, or does it re-execute from scratch (wasting tokens)?
- Does state get silently corrupted?
- Are contracts and acceptance gates preserved across process crashes?

Based on the *arXiv 2608.03836 Resume Contract* specification, `agent-durability-bench` injects deterministic process kills across synthetic multi-step task lifecycles and scores recovery fidelity.

*100% deterministic, zero LLM API key dependencies, and open to all framework adapters.*

---

## Benchmark Invariants (DCP-1.0)

1. **Zero State Corruption**: No partially written files, corrupted ASTs, or broken JSON contracts.
2. **Exactly-Once Step Resumption**: Resuming a crashed workflow MUST NOT duplicate completed work.
3. **Deterministic Impossibility Proof**: Tasks exhausting retries prior to crash must terminate with a signed receipt.

---

## Quick Start

```bash
# Clone and install dependencies
git clone https://github.com/sdageltc/agent-durability-bench.git
cd agent-durability-bench
pip install -e .

# Run the test harness on LetItLoop
python -m harness.runner --framework letitloop --phase WORKING --signal SIGKILL

# Run full multi-framework matrix
python -m harness.runner --all --export-markdown docs/index.md
```

## Adding Your Framework

See [CONTRIBUTING.md](CONTRIBUTING.md) to implement a `FrameworkAdapter` for LangGraph, CrewAI, AutoGen, or your custom agent framework.
