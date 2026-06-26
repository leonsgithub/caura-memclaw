# Sprint: sprint-brain-parity Signoff

**Sprint Goal:** Close the genuine, non-redundant feature-parity gaps between
`procedural_memory_mcp` (Brain) and MemClaw at the "pragmatic parity" scope.

**Date:** 2026-06-26

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Tasks Planned | 6 (BP-01 … BP-05, BP-Z01) |
| Completed | 6 |
| Failed / Cancelled | 0 |
| Success Rate | 100% |
| Total Commits | 5 implementation + 1 plan |
| MCP tool surface before | 12 v1 + 4 procedural = 16 tools |
| MCP tool surface after | 19 tools |

---

## Task Outcomes

| ID | Objective | Status | Commits | Verify |
|----|-----------|--------|---------|--------|
| BP-01 | Procedure lifecycle storage (DELETE, invalidate, quarantine client methods) | Completed | f0ffa81 | `pytest tests/test_mcp_procedures.py` → pass |
| BP-02 | `memclaw_procedure_manage` MCP tool (quarantine/unquarantine/invalidate/delete/stats) | Completed | ff41baa | `pytest tests/test_mcp_procedures.py` → pass |
| BP-03 | `memclaw_env` — Env Truths store (upsert/get/list/verify) | Completed | 63eb6e6 | `pytest tests/test_mcp_env.py` → 3 pass |
| BP-04 | `memclaw_export` — visibility-scoped bulk export (JSON/JSONL, cursor-paginated) | Completed | fad8a56 | `pytest tests/test_mcp_export.py` → 5 pass |
| BP-05 | `memclaw_review` — low-weight curation surface | Completed | 2b8500b | `pytest tests/test_mcp_review.py` → 5 pass |
| BP-Z01 | Sprint signoff + deliberate-divergence ledger | Completed | this file | Written |

**Meta-test suite (all sprints):** 21 tests pass across registry, description regression, and export-in-sync suites after each task.

---

## Files Changed

```
core-api/src/core_api/mcp_server.py                            (+~350 lines)
core-api/src/core_api/tools/memclaw_env.py                     (new)
core-api/src/core_api/tools/memclaw_export.py                  (new)
core-api/src/core_api/tools/memclaw_review.py                  (new)
core-api/src/core_api/tools/memclaw_procedure_manage.py        (new — BP-02)
core-storage-api/ (DELETE endpoint + status patch)             (BP-01)
tests/test_mcp_env.py                                          (new — 3 tests)
tests/test_mcp_export.py                                       (new — 5 tests)
tests/test_mcp_review.py                                       (new — 5 tests)
tests/test_mcp_procedures.py                                   (+6 tests BP-02)
tests/test_tools_registry.py                                   (surface expanded)
tests/test_tool_descriptions_regression.py                     (count → 19)
tests/fixtures/tool_descriptions_baseline_v1.json             (regenerated)
tests/fixtures/tool_descriptions_enriched_baseline_v1.json    (regenerated)
tests/fixtures/tools_list_baseline_v1.json                    (regenerated)
plugin/tools.json                                              (regenerated)
```

---

## Deliberate-Divergence Ledger

The following Brain tools were reviewed and **intentionally NOT ported**. Each absence is a documented decision, not an oversight.

| Brain Tool | Reason Not Ported |
|------------|-------------------|
| `record_correction` | MemClaw already handles this automatically. The contradiction detector (search pipeline) creates a supersession link whenever a new memory conflicts with an existing one; no manual correction call is needed. |
| `link_thought` | Covered by the entity cross-linking pipeline (`subject_entity_id` / `predicate` / `object_value` on Memory). Agents write structured memories; the pipeline builds the knowledge graph automatically. No manual link surface is needed. |
| `get_stale_thoughts` | Covered by `memclaw_list(weight_max=0.4, sort=weight)` and the new `memclaw_review`. MemClaw's crystallizer also promotes and culls memories via lifecycle transitions. No separate stale-review endpoint is warranted. |
| `record_failure_context` | Feeds Brain's training/curriculum subsystem. The prior procedural-memory sprint deliberately omitted that subsystem; Forge replaces it in the MemClaw ecosystem. |
| `record_escalation` | Same reasoning as `record_failure_context` — curriculum path, not in scope. |
| `call_procedure` | `memclaw_procedure_suggest` already returns `steps` + `reasoning_guide`; `memclaw_procedure_record` logs usage. A separate "call and record" wrapper adds no new semantics — the caller does both today. |
| `brain_batch` | The MCP protocol client already parallelizes independent tool calls. A batch envelope that wraps multiple calls is YAGNI: it adds latency overhead (single round-trip vs. parallel dispatch) with no benefit in a native MCP context. |
| `delete_thought` / `update_thought` | Covered by `memclaw_manage(op=delete)` and `memclaw_manage(op=update)`. The naming differs; the semantics are identical. |
| `record_outcome` | MemClaw's `memclaw_evolve` adjusts `memory.weight` based on recall outcomes automatically. A separate outcome record surface would duplicate state that evolve already manages. |
| `rate_retrieval` | Brain's rating feeds its internal usefulness tracker. MemClaw tracks usage via `recall_count` + `last_recalled_at` on the Memory row and `memclaw_evolve` weight adjustments. No separate rating call is needed. |

---

## Lessons Learned

1. **Re-use storage primitives.** BP-03 (Env Truths) required zero migration — the existing `_env_truths` collection in the doc store was sufficient. This pattern (reserved collection names over new tables) should be the default for small, key-value domains.

2. **`memclaw_export` vs `memclaw_list`.** Export is essentially `memclaw_list` with trust≥1 + format options. The separation is justified by intent (bulk egress vs. interactive paging), not by implementation complexity.

3. **Frozen surface tests pay off.** Regenerating 3 baseline files + `plugin/tools.json` after each task kept the contract clear. The cost is a few seconds; the benefit is immediate detection if the tool count drifts.

4. **Ponytail discipline.** All 5 new tools were implemented with no speculative parameters. The review tool is ~60 lines including the docstring; export is ~80. Neither required a new abstraction layer.

---

**Signed off:** Claude (sprint-run agent)

**Branch:** `sprint/brain-parity-plan`

**Next:** Merge to main; update deployed MemClaw instance.
