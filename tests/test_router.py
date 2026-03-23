from agent_memory.controller.router import IntentRouter, reciprocal_rank_fusion
from agent_memory.models import QueryIntent


def test_router_classifies_causal_queries() -> None:
    router = IntentRouter()
    assert router.classify("为什么部署会失败？") is QueryIntent.CAUSAL


def test_router_classifies_temporal_queries() -> None:
    router = IntentRouter()
    assert router.classify("上周我们讨论了什么数据库方案？") is QueryIntent.TEMPORAL


def test_router_classifies_procedural_queries() -> None:
    router = IntentRouter()
    assert router.classify("如何配置 agent memory？") is QueryIntent.PROCEDURAL


def test_rrf_prefers_consensus_items() -> None:
    fused = reciprocal_rank_fusion(
        {
            "semantic": ["a", "b", "c"],
            "entity": ["b", "a", "d"],
            "full_text": ["b", "e", "a"],
        }
    )
    assert list(fused.keys())[0] == "b"

