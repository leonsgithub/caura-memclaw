# Sprint Recall-Context Signoff

**Sprint Goal:** Fix cross-project bleed in `memclaw_recall` phase 2. Phase 2 (`CrossContextEnrich`) re-ran the query without `caller_agent_id`, so storage returned all `scope_team`/`scope_org` rows ranked by pure embedding similarity — a `.53 login` from an unrelated project could outrank the correct one. Fix: `preferred_agent_ids` soft score boost (×1.2) in `memory_scored_search`; `CrossContextEnrich` auto-populates it from `caller_agent_id`.

**Duration:** 2026-06-26 (single session, resumed after context compaction)

## Execution Summary

| Metric | Value |
|--------|-------|
| Total WorkItems | 6 |
| Completed | 6 |
| Failed / Cancelled | 0 |
| Success Rate | 6/6 |
| Total Attempts | 6 |
| Retry Rate | 0% |
| Deploy | 192.168.1.53 — both containers healthy |

## WorkItem Status

| ID | Status | Notes |
|----|--------|-------|
| RC-01 | completed | `memory_scored_search` gains `preferred_agent_ids` / `preferred_agent_boost` params + CASE boost |
| RC-02 | completed | `/memories/scored-search` router threads params from request body |
| RC-03 | completed | `CrossContextEnrich` auto-populates `preferred_agent_ids` from `caller_agent_id` |
| RC-04 | completed | 4 unit tests; local `_patch_storage_client` override avoids pgvector dep |
| RC-05 | completed | Built + deployed on `dns` (192.168.1.53); both containers healthy |
| RC-Z01 | completed | This file |

## File Changes

| File | Change |
|------|--------|
| `core-storage-api/src/core_storage_api/services/postgres_service.py` | `memory_scored_search` — added `preferred_agent_ids: list[str] \| None = None` and `preferred_agent_boost: float = 1.2`; CASE expression multiplies score for matching `agent_id` rows |
| `core-storage-api/src/core_storage_api/routers/memories.py` | `/scored-search` endpoint passes `preferred_agent_ids` and `preferred_agent_boost` from body |
| `core-api/src/core_api/pipeline/steps/search/cross_context_enrich.py` | Phase 2 `search_p2` dict includes `preferred_agent_ids=[caller_agent_id]` when set; absent when anonymous |
| `tests/test_recall_context.py` | 4 unit tests: boost logic + pipeline wiring; `_patch_storage_client` override to skip pgvector |
| `sprints/sprint-recall-context/capability_tasks.json` | All RC-01..RC-04 states updated to `completed` |

## Test Run Output

```
$ python -m pytest tests/test_recall_context.py -v
Pytest: 4 passed
```

Tests:
- `test_preferred_agent_boost_ranks_same_agent_higher` — same-agent score × 1.2 > cross-agent score
- `test_no_boost_when_preferred_agent_ids_is_none` — None / empty list → no change
- `test_cross_context_enrich_passes_preferred_agent_ids` — CrossContextEnrich sends `preferred_agent_ids=["project-a"]` to storage
- `test_cross_context_enrich_no_preferred_when_anonymous` — `caller_agent_id=None` → key absent from payload

## Deployment

Branch `sprint/brain-parity-plan` deployed to `dns` (192.168.1.53):

```
docker compose build core-api core-storage-api  → Built
docker compose up -d core-api core-storage-api  → Both containers Started + Healthy
```

## Backlog / Known Items

- `preferred_agent_boost = 1.2` is an arbitrary default; tune after observing real ranking behaviour in Hermes multi-agent scenarios.
- The `sprint/brain-parity-plan` branch is not merged to `main` — coordinate with upstream (`caura-ai/caura-memclaw`) before merging.
- Three Hermes instances sharing the same `X-Agent-ID: hermes-orchestrator` are still indistinguishable to MemClaw; separate agent IDs per instance would make the boost more precise. Tracked as a separate concern (see `sprints/sprint-feedback/hermesfeedbackdevops.md`).

---

**Signed off:** claude-code

**Date:** 2026-06-26
