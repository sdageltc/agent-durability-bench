# Agent Execution Guidelines for agent-durability-bench

## ⚡ Fast Test & Conformance Protocol

### 1. Targeted Adapter Test (< 0.5s)
When modifying framework adapters or crash injectors, test only the affected file:
```bash
pytest tests/test_benchmarks.py -v
```

### 2. Durability Benchmark Execution
```bash
# Run DCP-1.0 benchmark with SIGKILL fault injection:
agent-durability-bench --framework letitloop --fault sigkill
```

### 🔒 Invariants
- **Real Subprocess Execution**: All benchmarks must execute real child processes (`ProcessLifecycleGuard`) rather than static mock returns.
- **Fair Methodology**: Focus strictly on runtime crash durability ($R_{crash}$) and token waste ($W_{token}$), without IQ/reasoning bias.
- **Attribution**: Author must remain `sdageltc <sdageltc@users.noreply.github.com>`.
