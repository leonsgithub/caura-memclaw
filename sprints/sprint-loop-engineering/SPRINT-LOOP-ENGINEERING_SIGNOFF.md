# Sprint Loop-Engineering Signoff

**Sprint Goal:** Make MemClaw a faithful *Memory* organ inside a Loop Engineering loop — not the whole loop. Close the one genuinely in-lane gap (the paper's "Nodding Loop": an agent grading its own homework) and explicitly *not* build the harness organs the original draft over-reached into.

**Sprint Duration:** 2026-06-26 (single session)

**Branch:** `sprint/brain-parity-plan`

---

## Scope Correction (the most important artifact of this sprint)

This sprint was planned with **6 work items across 3 upgrades** and deliberately cut to **2 items (1 feature + signoff)** before any code was written. The cut is the headline result, so it is recorded first.

After re-reading the source — `/home/leon/dev/research/learningsystem/Loop-Engineering-IEEE.pdf` — the load-bearing thesis is explicit (Table V, §VII.E, §XII):

> **"Loop engineering is a set of capabilities, not a product."**

A loop has **six organs**, and the paper places each in the **harness**, not in any single tool:

| Organ | Move | Where it lives | MemClaw? |
|---|---|---|---|
| Automations | Scheduling | Claude Code `/loop`, Cloud Routines, GH Actions | ❌ harness |
| Worktrees | Handoff | git `--worktree` | ❌ harness |
| Skills | Discovery | `SKILL.md` | ❌ harness (Forge mints skill docs, but discovery/invocation is harness-side) |
| Connectors | Persistence/Discovery | MCP | ❌ protocol (MemClaw is *reached* over MCP) |
| Sub-agents | Verification | `.claude/agents/reviewer.md` + `/goal` | ❌ harness (MemClaw only *records* the verdict) |
| **Memory** | **Persistence** | **on-disk state** | ✅ **this is MemClaw's lane** |

MemClaw is **one** organ: Memory. The original draft had the memory store grow three organs the harness already owns. All three were dropped:

| Dropped item | Why |
|---|---|
| `memclaw_verify_run` (subprocess-sandbox evaluator) | The evaluator is a separate **agent** (Fig. 3), a harness organ — not a function in the memory store. Putting a subprocess executor inside MemClaw is the wrong layer (and was the sprint's only high-risk item). |
| `memclaw_cost_audit` + Turn-Distance Cost Factor `base_cost × 2^(turn_distance/10)` | The formula was **invented**. The paper's "cost scales with turns survived" (§II.C) is *motivational intuition for why verification matters*, not a mechanism it proposes building. Instrumenting a fabricated metric is speculative gold-plating. |
| `memclaw_schedule_loop` + propulsion-ticket cron | Scheduling is the harness's organ (`/loop` + Cloud Routines). The draft worker even punted payload execution back to the harness — pure duplication. |

The in-lane survivor became **LE-01**.

Superseded design doc: [`docs/loop-engineering-upgrades.md`](../../docs/loop-engineering-upgrades.md) (carries a SUPERSEDED banner pointing here).

---

## Execution Summary

| Metric | Value |
|--------|-------|
| Total WorkItems Planned | 2 |
| Completed | 2 |
| Failed / Cancelled | 0 |
| Success Rate | 2 / 2 |
| Total Attempts | 2 |
| Retry Rate | 0 |
| Estimated Duration | 1 day |

## WorkItem Status

| ID | Title | Status | Attempts | Notes |
|----|-------|--------|----------|-------|
| LE-01 | Verified-vs-claimed procedure reliability | **completed** | 1 | Migration 029 + model + handler + 3 tests. Commit `8810bb6`. |
| LE-Z01 | Sprint signoff | **completed** | 1 | This document. |

---

## LE-01 — What Was Built

**Problem (the Nodding Loop, §VI.A):** `memclaw_procedure_record` drove `reliability_score` purely from the agent's self-reported `outcome_type`. The `validation_passed` parameter the tool already declared ([`mcp_server.py`](../../core-api/src/core_api/mcp_server.py) `memclaw_procedure_record`) was **silently dropped** — an agent's self-graded "success" was indistinguishable from one an independent evaluator confirmed.

**Change set (6 files, +182/-3):**

| File | Change |
|---|---|
| `core-storage-api/.../migrations/versions/029_procedure_verified_counters.py` | New migration: `verified_success_count` / `verified_failure_count` on `procedure_stats` (Integer, NOT NULL DEFAULT 0, reversible) |
| `common/models/procedure.py` | The two mapped columns on `ProcedureStats` |
| `core-storage-api/.../schemas.py` | `PROCEDURE_STATS_FIELDS` serializes the new counters back |
| `core-api/.../mcp_server.py` | `validation_passed=True` additionally moves the verified counters; response gains `verified_reliability` (null until a verified outcome exists). Self-reported path unchanged when `None`/`False`. Quarantine still keys off combined counts. |
| `core-api/.../tools/memclaw_procedure_record.py` | Tool description documents *when* to set `validation_passed` (independent verifier only) |
| `tests/test_mcp_procedures.py` | 3 new tests |

**Design boundary held:** MemClaw does **not** run tests, spawn the evaluator, or schedule anything. The harness's independent evaluator agent runs the verification and reports the verdict via `validation_passed=True`; MemClaw only *remembers it honestly*. `verified_reliability` is `null` (not `0.5`) at zero verified outcomes, so callers distinguish "never independently verified" from "verified and mediocre" — the paper's verification-debt signal (§VIII).

---

## Verification Evidence

**Unit tests** — `tests/test_mcp_procedures.py` (FakeStorage stub, real handlers + ranker):

```
$ TEST_DATABASE_URL=postgresql+asyncpg://memclaw:changeme@127.0.0.1:5544/memclaw \
    .venv/bin/python -m pytest tests/test_mcp_procedures.py -q
.................                                                         [100%]
17 passed in 0.64s
```

The 3 new cases prove the LE-01 acceptance criteria:
- `test_record_self_reported_leaves_verified_null` — `validation_passed` unset → `success_count=1`, `verified_success_count=0`, `verified_reliability=None` (self-reported path byte-for-byte unchanged).
- `test_record_verified_success_moves_verified_counters` — self-reported then verified success → `success_count=2`, `verified_success_count=1`, `verified_reliability > 0.5`.
- `test_record_verified_failure_drops_verified_reliability` — verified failure → `verified_failure_count=1`, `verified_reliability < 0.5`.

**Migration chain** — full chain on a fresh throwaway DB:

```
027 -> 028 -> 029   (alembic upgrade head: clean)
2nd upgrade head:   0 migrations run (idempotent)
\d procedure_stats: verified_success_count | integer | not null | 0
                    verified_failure_count | integer | not null | 0
downgrade -1:       029 -> 028 clean; both columns removed
```

**Regression:** `tests/test_procedure_service.py` + `tests/test_mcp_procedures.py` = 26 passed. Two failures in `tests/test_forge_procedure_bridge.py` (`run_forge_distill` positional-arg signature mismatch) are **pre-existing** — confirmed present on the clean tree at `ff2277a` via `git stash`, unrelated to LE-01.

---

## Loop Engineering Organ Map (post-sprint)

| Organ | Owner | MemClaw's role |
|---|---|---|
| Memory / Persistence | **MemClaw** | `memclaw_write` / `recall` / `evolve` / lifecycle automation + **(this sprint)** verified-vs-claimed outcome reliability on procedures |
| Automations / Scheduling | Harness | none — use `/loop`, Cloud Routines |
| Worktrees / Handoff | Harness | none — git `--worktree` |
| Skills / Discovery | Harness | Forge mints skill docs; discovery/invocation is harness-side |
| Connectors | Protocol | MemClaw is reached over MCP |
| Sub-agents / Verification | Harness | the evaluator agent runs tests; **MemClaw records the verdict** (LE-01) |

**100% loop coverage is explicitly NOT a MemClaw goal.** The correct ambition: *MemClaw is the best possible Memory organ in someone else's loop.*

---

## Lessons Learned

**What went well**
1. **Killing scope before coding.** Re-reading the primary source turned a 6-item, 4-day, high-risk sprint into a 1-item, 1-day, low-risk one. The biggest win was a `-274`-line plan diff, not a feature.
2. **The gap was already half-wired.** `validation_passed` existed in the tool signature but was dead. The fix gave an existing-but-ignored parameter meaning rather than adding new surface.
3. **The FakeStorage harness** in `tests/test_mcp_procedures.py` made the three record-path tests cheap and DB-light.

**What to improve**
1. **Pre-existing forge-bridge test rot.** `test_forge_procedure_bridge.py` is red on `main`-line (`run_forge_distill` signature drift). Not in scope here, but it means `tests/` is not green end-to-end — flagged for a follow-up.
2. **Test DB discovery.** The suite needs `TEST_DATABASE_URL` pointed at the `memclaw-test-db` container (port 5544); this isn't documented in the sprint tooling. Worth a one-line note in the test README.

## Deferred to Next Sprint

- **Verified-failure quarantine weighting.** Let a verified failure dock a procedure faster than a self-reported one (verified outcomes carry more signal). Deferred until the verified counters have real production data to tune the threshold against.

---

**Signed off:** Claude Code (sprint-run)
**Date:** 2026-06-26
**Result:** 2/2 work items completed. One in-lane capability shipped; five-sixths of the original draft deliberately not built, on principle.
