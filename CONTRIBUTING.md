# Contributing to agent-durability-bench 🛡️

Thank you for contributing to the open standard for AI agent durability and crash resilience! This benchmark evaluates runtime crash resilience, process tree isolation, and token waste under ungraceful termination (**Durability Conformance Protocol 1.0 / DCP-1.0**).

---

## Architectural Archetypes & Reference Patterns

DCP-1.0 categorizes agent runtime architectures into four primary archetypes:

1. **Atomic Write-Ahead Log (WAL) Engine**: Append-only log with synchronous disk fsync (e.g., LetItLoop, Temporal).
2. **Periodic Snapshot Graph**: Checkpointing at superstep/node boundaries (e.g., LangGraph with SqliteSaver).
3. **In-Memory Event Loop**: Conversational loops with state stored in memory (e.g., AutoGen, CrewAI).
4. **Unmanaged Script**: Direct Python execution without process supervision.

---

## How to Add Your Framework Adapter

We welcome official native adapters from framework maintainers!

### Step 1: Subclass `FrameworkAdapter`
In `adapters/<your_framework>_adapter.py`:

```python
from typing import Tuple, Any
from adapters.base import FrameworkAdapter
from harness.schema import DurabilityScore, SyntheticTaskSpec

class MyFrameworkAdapter(FrameworkAdapter):
    def __init__(self, wal_dir: str = ".bench_wal"):
        self.wal_dir = wal_dir

    @property
    def name(self) -> str:
        return "my_framework"

    def start_task(self, spec: SyntheticTaskSpec) -> Tuple[int, Any]:
        """Spawns your framework in a child subprocess. Returns (PID, stdout)."""
        ...

    def resume_task(self, spec: SyntheticTaskSpec) -> DurabilityScore:
        """Resumes execution after SIGKILL and reports recovered steps and token waste."""
        ...
```

### Step 2: Register in `harness/runner.py`
Add your adapter to `ADAPTERS` in `harness/runner.py`.

### Step 3: Run the Test Suite
```bash
pytest tests/ -v
python -m harness.runner --matrix
```

Submit a Pull Request on GitHub to have your framework benchmarked on the official leaderboard!
