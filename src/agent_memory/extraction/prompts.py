EXTRACT_FACTS_PROMPT = """
You extract durable long-term memories from conversations for an agent memory engine.

Only keep information that is likely to matter across future sessions.
Prioritize:
- stable preferences
- identity or role information
- long-running goals
- durable procedural knowledge
- causal explanations for important decisions

Ignore:
- chit-chat
- acknowledgements
- one-off small talk
- transient details unless they explain an important choice

Return JSON only.
"""

CONFLICT_JUDGE_PROMPT = """
You compare two candidate memories and decide whether they:
- contradict
- supersede
- support each other
- should both be kept
Return a short rationale and a resolution label.
"""

CONSOLIDATION_PROMPT = """
You merge semantically overlapping memories into one durable summary.

Produce one canonical memory that:
- preserves the most useful stable facts
- keeps causal rationale when important
- avoids duplicates
- uses concise wording

Return JSON only.
"""
