# Adding Your Agent Framework to the Durability Benchmark 🛡️

We believe every autonomous coding agent and agentic workflow framework should be crash-safe. Rather than making speculative claims about third-party frameworks, `agent-durability-bench` provides an open, transparent, and reproducible conformance harness.

## Why Durability Matters

When an autonomous agent runs a multi-step task and encounters a crash (`kill -9`, spot VM termination, unhandled exception, network partition):
1. **Zero Duplicate Work**: Completed steps should not be re-executed, avoiding token and cost blowouts.
2. **Zero State Corruption**: Partially completed state must not leave corrupted files on disk.
3. **Exact Recovery**: The agent must resume from its last verified checkpoint.

---

## How to Add Your Framework

1. **Fork the repository** and install dependencies:
   ```bash
   git clone https://github.com/sdageltc/agent-durability-bench.git
   cd agent-durability-bench
   pip install -e .
   ```

2. **Create your adapter** in `adapters/<your_framework>_adapter.py`:
   ```python
   from adapters.base import FrameworkAdapter
   from harness.schema import DurabilityScore, SyntheticTaskSpec

   class MyFrameworkAdapter(FrameworkAdapter):
       @property
       def name(self) -> str:
           return "my-framework"

       def start_task(self, spec: SyntheticTaskSpec):
           # Launch your framework task
           ...

       def resume_task(self, spec: SyntheticTaskSpec) -> DurabilityScore:
           # Resume from crash and evaluate state
           ...
   ```

3. **Add unit tests** in `tests/test_my_framework_adapter.py`.

4. **Submit a Pull Request**. Once merged, your framework will be evaluated daily in our automated GitHub Actions nightly CI sweep and featured on the public leaderboard!
