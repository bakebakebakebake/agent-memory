from agent_memory.controller.forgetting import ForgettingPolicy
from agent_memory.models import MemoryItem, MemoryLayer, MemoryType


def build_memory(access_count: int = 0, layer: MemoryLayer = MemoryLayer.SHORT_TERM) -> MemoryItem:
    return MemoryItem(
        id="memory-1",
        content="important preference",
        memory_type=MemoryType.SEMANTIC,
        embedding=[0.1, 0.2, 0.3],
        access_count=access_count,
        importance=0.9,
        trust_score=0.9,
        decay_rate=0.05,
        layer=layer,
    )


def test_effective_strength_increases_with_access() -> None:
    policy = ForgettingPolicy()
    weak = policy.effective_strength(build_memory(access_count=0), age_days=1)
    strong = policy.effective_strength(build_memory(access_count=10), age_days=1)
    assert strong > weak


def test_next_layer_promotes_high_strength_memories() -> None:
    policy = ForgettingPolicy()
    memory = build_memory(access_count=12)
    assert policy.next_layer(memory, age_days=0.1) is MemoryLayer.LONG_TERM


def test_next_layer_demotes_low_strength_memories() -> None:
    policy = ForgettingPolicy()
    memory = build_memory(access_count=0, layer=MemoryLayer.LONG_TERM)
    memory.importance = 0.2
    memory.trust_score = 0.2
    assert policy.next_layer(memory, age_days=60) is MemoryLayer.SHORT_TERM

