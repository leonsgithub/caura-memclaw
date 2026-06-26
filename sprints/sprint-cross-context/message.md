Summary

Sprint: 2-Phase Cross-Context Recall for MemClaw

Problem: memclaw_recall's single-phase search blends own (scope_agent) and shared
(scope_team/scope_org) memories in one query. Low-scoring shared knowledge gets
crowded out by higher-scoring own memories even when no own memory directly answers
the question.

Solution: Port Brain MCP's 2-phase cross-context retrieval pattern as an opt-in
cross_context=True flag on memclaw_recall. Phase 1 = current behaviour (unchanged).
Phase 2 = re-run same query embedding without caller_agent_id (storage returns shared
scope only), apply lower threshold, discount scores, cap blend at cc_ratio.

Task	What shipped	Commit
CC-01	source_type: str | None = None on MemoryOut; _memory_to_out passes it through	743a1eb
CC-02	CrossContextEnrich pipeline step; wired into search pipeline after PostFilterResults	743a1eb
CC-03	search_memories + _search_memories_pipeline + memclaw_recall tool — 5 new params	743a1eb
CC-04	Deployed to 192.168.1.53 — core-api container healthy	live

Default values match Brain MCP's routing_weights.yaml:
  cc_top_m=3, cc_threshold=0.15, cc_ratio=0.3, cc_discount=0.85

All params default to off — zero behaviour change for existing callers unless
cross_context=True is explicitly passed.

Key design decision: Phase 2 uses the SAME query embedding (not per-hit embeddings
like Brain does). This avoids new storage endpoints while still surfacing shared
knowledge below Phase 1's threshold. Less precise than Brain's approach but minimal
and correct for MemClaw's use case.

Files changed:
  core-api/src/core_api/pipeline/steps/search/cross_context_enrich.py  (new)
  core-api/src/core_api/pipeline/steps/search/__init__.py
  core-api/src/core_api/pipeline/compositions/search.py
  core-api/src/core_api/services/memory_service.py
  core-api/src/core_api/mcp_server.py
  core-api/src/core_api/schemas.py
  sprints/sprint-cross-context/capability_tasks.json  (new)
