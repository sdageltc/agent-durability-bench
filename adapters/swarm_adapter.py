from adapters.in_memory_adapter import InMemoryAdapter


class SwarmAdapter(InMemoryAdapter):
    """OpenAI Swarm-style handoff adapter with in-memory state semantics."""

    @property
    def name(self) -> str:
        return "swarm"

    @property
    def archetype_label(self) -> str:
        return "OpenAI Swarm Handoff Pattern (In-Memory)"
