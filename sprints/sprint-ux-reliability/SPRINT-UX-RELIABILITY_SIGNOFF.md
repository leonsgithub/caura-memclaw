# Sprint UX-Reliability Signoff

**Sprint Goal:** Reduce adoption friction and prevent memory bleed: default writes to `scope_agent`, cache recall in Redis, add `memclaw_session_start` warm-context tool, add local embedder fallback, and add `memclaw-init` CLI.

**Branch:** `sprint/ux-reliability`

## Execution Summary

| Metric | Value |
|--------|-------|
| Total WorkItems Planned | 6 |
| Completed | 6 |
| Failed / Cancelled | 0 |
| Success Rate | 6 / 6 |
| Total Attempts | 1 per item |
| Retry Rate | 0% |
| Sessions | 2 (context compaction mid-sprint) |

## WorkItem Status

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| UX-01 | `memclaw_write` default visibility → `scope_agent` | ✅ completed | Single-line change in `mcp_server.py`; standalone-only path |
| UX-02 | Redis recall cache in `memclaw_recall` | ✅ completed | 4 cache tests added; cache bypassed on `cross_context=True` or `filter_agent_id` |
| UX-03 | `memclaw_session_start` tool (tool #20) | ✅ completed | Returns top-5 memories, keystones, procedures ≥ 0.6 reliability; 5 tests; all baselines regenerated |
| UX-04 | Ollama-compatible local embedder fallback | ✅ completed | `EMBEDDING_PROVIDER=ollama` + `OLLAMA_EMBEDDING_URL` / `OLLAMA_EMBEDDING_MODEL` env vars; reuses `OpenAIEmbeddingProvider`; 5 tests |
| UX-05 | `memclaw-init` CLI | ✅ completed | `cli/memclaw_init.py`; argparse + httpx; health ping + MCP config block + optional agent verify |
| UX-Z01 | Sprint signoff | ✅ completed | This document |

## Artifacts Produced

| File | Change |
|------|--------|
| `core-api/src/core_api/mcp_server.py` | UX-01 visibility default; UX-02 cache logic; UX-03 `memclaw_session_start` handler |
| `core-api/src/core_api/tools/memclaw_session_start.py` | UX-03 ToolSpec (new file) |
| `common/provider_names.py` | Added `OLLAMA = "ollama"` |
| `common/embedding/_registry.py` | UX-04 ollama case in `get_embedding_provider` |
| `common/embedding/providers/openai.py` | Added `self._base_url` attribute for introspection |
| `cli/memclaw_init.py` | UX-05 setup CLI (new file) |
| `tests/test_tools_registry.py` | Added `memclaw_session_start` to `EXPECTED_PLUGIN_EXPOSED` |
| `tests/test_tool_descriptions_regression.py` | `EXPECTED_TOOL_COUNT = 20` |
| `tests/test_mcp_recall.py` | 4 cache hit/miss/bypass tests |
| `tests/test_mcp_session.py` | 5 session-start tests (new file) |
| `tests/test_embedding_local.py` | 5 Ollama provider tests (new file) |
| `tests/fixtures/tool_descriptions_baseline_v1.json` | Regenerated (20 tools) |
| `tests/fixtures/tool_descriptions_enriched_baseline_v1.json` | Regenerated (20 tools) |
| `tests/fixtures/tools_list_baseline_v1.json` | Regenerated (20 tools) |
| `plugin/tools.json` | Regenerated (20 tools) |

## Test Results

57 tests across 8 test files — 0 failures.

```
tests/test_tools_registry.py          (registry invariants)
tests/test_tool_descriptions_regression.py  (baseline drift)
tests/test_mcp_recall.py              (UX-02 cache + existing)
tests/test_mcp_session.py             (UX-03 session_start)
tests/test_mcp_env.py
tests/test_mcp_export.py
tests/test_mcp_review.py
tests/test_embedding_local.py         (UX-04 Ollama)
```

## Design Decisions

**UX-04 — Ollama via existing OpenAI-compatible provider, not a new class.** Ollama exposes `/v1/embeddings` (OpenAI wire format). Reusing `OpenAIEmbeddingProvider` with `api_key="ollama"`, `base_url=OLLAMA_EMBEDDING_URL`, `send_dimensions=False` required zero new code for the embedding logic itself. The only addition is an `ollama` branch in the registry (~5 lines) and `OLLAMA = "ollama"` in `ProviderName`.

**UX-05 — No `/agents/register` endpoint exists.** Agent registration happens implicitly on first write. `--agent-id` instead calls `GET /agents/{agent_id}` to verify existence; if the agent isn't found, prints that it will auto-create on first write. This is more useful than a non-existent endpoint.

**UX-02 cache key** is SHA-256 of `{query}{capped_top_k}` (first 12 hex chars), scoped by `agent_id`. Cross-context queries and targeted `filter_agent_id` queries bypass the cache — both are expected to produce different result sets than the baseline agent recall.

## Lessons Learned

- Baseline fixture regeneration after adding a new tool requires 4 separate steps (3 JSON fixtures + `plugin/tools.json`). This is the second sprint where this has been a friction point — consider a `make fixtures` target.
- The memclaw test DB runs on port 5544 (`memclaw-test-db` container), not the default 5432. This has tripped up test runs twice.

## Deliberate Omissions

- No `OLLAMA_EMBEDDING_API_KEY` env var — Ollama accepts any value for the API key, and `"ollama"` is the community convention. Override is not needed.
- `cli/memclaw_init.py` has no `__init__.py` — it's a script, not a package. Runnable as `python -m cli.memclaw_init`.

---

**Signed off:** Claude (claude-sonnet-4-6)

**Date:** 2026-06-26

**Next Sprint:** Consider `memclaw-verify` (smoke-test a deployment end-to-end) or `memclaw_agent_profile` (richer per-agent config surface).
