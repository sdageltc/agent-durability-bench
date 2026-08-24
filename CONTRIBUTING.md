# Contributing to agent-durability-bench

Thank you for helping build the open benchmark for AI agent crash resilience. This guide walks you through implementing a `FrameworkAdapter` to benchmark your framework against the **Durability Conformance Protocol (DCP-1.0)**.

---

## The Adapter Contract (DCP-1.0)

Every framework adapter subclasses `BaseAdapter` in `harness/adapters/base.py`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

class BaseAdapter(ABC):
    """Base interface for agent framework durability adapters."""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abstractmethod
    def setup_environment(self, workspace_path: Path, task_spec: Dict[str, Any]) -> None:
        """Initialize target agent workspace and mock tools."""
        pass

    @abstractmethod
    def execute_step(self, step_index: int) -> Dict[str, Any]:
        """Execute a single agent step and return state receipt."""
        pass

    @abstractmethod
    def resume_from_crash(self, crash_checkpoint_path: Path) -> Dict[str, Any]:
        """Resume execution following an ungraceful SIGKILL."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Terminate all background child/grandchild worker processes."""
        pass
```

---

## Step-by-Step: Adding a New Framework Adapter

### Step 1: Create the Adapter File
Create `adapters/<framework_name>_adapter.py`:

```python
from pathlib import Path
from typing import Dict, Any
from harness.adapters.base import BaseAdapter

class LangGraphAdapter(BaseAdapter):
    def __init__(self):
        super().__init__(name="langgraph", version="0.2.0")
        self.active_graph = None

    def setup_environment(self, workspace_path: Path, task_spec: Dict[str, Any]) -> None:
        self.workspace = workspace_path
        # Initialize graph state and memory saver checkpointer

    def execute_step(self, step_index: int) -> Dict[str, Any]:
        # Run node transition
        return {"step": step_index, "status": "COMPLETED"}

    def resume_from_crash(self, crash_checkpoint_path: Path) -> Dict[str, Any]:
        # Reload state from checkpoint
        return {"resumed_step": 2, "status": "RESUMED"}

    def cleanup(self) -> None:
        # Close database connections and worker pools
        pass
```

### Step 2: Register in Harness
Import and register your adapter in `harness/adapters/__init__.py`:

```python
from harness.adapters.letitloop_adapter import LetItLoopAdapter
from adapters.langgraph_adapter import LangGraphAdapter

ADAPTER_REGISTRY = {
    "letitloop": LetItLoopAdapter,
    "langgraph": LangGraphAdapter,
}
```

### Step 3: Run Conformance Verification
Verify your adapter passes all DCP-1.0 test suites locally:

```bash
# Run unit tests
pytest tests/test_conformance.py -v

# Run crash injection test
python -m harness.runner --framework <your-framework> --signal SIGKILL
```

---

## Submitting Your Pull Request

1. Fork the repository and create a branch: `git checkout -b adapter/add-<framework-name>`.
2. Ensure your adapter passes `pytest tests/` with zero failures.
3. Run the anti-slop linter on all documentation:
   ```bash
   python .agents/scripts/slop_checker.py README.md
   ```
4. Open a Pull Request using the standard [New Adapter Issue Form](https://github.com/sdageltc/agent-durability-bench/issues/new?template=new_adapter.yml).
