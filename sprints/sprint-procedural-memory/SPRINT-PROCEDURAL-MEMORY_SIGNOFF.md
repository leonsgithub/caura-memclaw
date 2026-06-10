# Sprint procedural-memory — Signoff

**Date:** 2026-06-10
**Branch:** `feat/sprint-procedural-memory`
**Fork / deploy target:** `leonsgithub/caura-memclaw` (fork of `caura-ai/caura-memclaw`); `origin` remains upstream, `fork` remote is the push target. PR will be fork → upstream `main` if/when shared.
**Objective:** Bring Brain's runtime *suggest → rank-by-reliability → record-outcome* procedural loop into MemClaw as a dedicated `procedures` domain, wired INTO the existing Skill Factory / Forge rather than duplicating its trajectory mining.

---

## Task Status

| Task | Title | Status | Commit | Notes |
|------|-------|--------|--------|-------|
| PM-01 | Procedures storage domain (migration 023 + model + router) | DONE | e61caf7 | 2 tables, model, router, service; alembic up/down roundtrip clean |
| PM-02 | core-api ranker + storage-client methods | DONE | f021fa6 | semantic + Jaccard context + reliability blend; no Brain import |
| PM-03 | MCP tools suggest / record / write | DONE | 2a74610 | full runtime loop incl. quarantine; 3 tools register in REGISTRY |
| PM-04 | Forge bridge — mined skills emit suggestable procedures | DONE | 76721e7 | additive + failure-isolated; reliability seeded from trace outcomes |
| PM-05 | Close loop into Skill Factory telemetry | DONE | 2431356 | record bumps linked skill `telemetry`; implements deferred Phase-4 |
| PM-Z01 | Signoff + deploy-target decision | DONE | (this doc) | fork target decided; backlog noted |

**Score:** 6/6 tasks done. 0 partial. 0 blocked.

---

## Changes by File

### PM-01 — storage domain
- **`common/models/procedure.py`** (new) — `Procedure` + `ProcedureStats` models, MemClaw tenancy (tenant/fleet/agent TEXT), `Vector(VECTOR_DIM)=1024`, `skill_doc_id` back-link.
- **`.../migrations/versions/023_procedures.py`** (new) — two tables + CHECK constraints (risk_level, status) + indexes; clean `downgrade`.
- **`.../routers/procedures.py`** (new) — create / get / list (tenant-scoped, excludes quarantined) / patch-stats.
- **`.../services/postgres_service.py`**, **`schemas.py`**, **`routers/__init__.py`**, **`app.py`**, **`common/models/__init__.py`** — service methods, field projections, registration.

### PM-02 — ranker
- **`core-api/.../services/procedure_service.py`** (new) — `rank_procedures` (semantic cosine via MemClaw embedder + ported Jaccard `_context_overlap` + reliability), `compute_reliability` (Laplace-smoothed).
- **`core-api/.../clients/storage_client.py`** — `create/get/list/update_procedure_stats`.

### PM-03 — MCP runtime loop
- **`core-api/.../mcp_server.py`** — `memclaw_procedure_suggest` (trust 0), `_record` (trust 1, quarantine at ≥3 attempts & score <0.3), `_write` (trust 1, embeds for suggestability); `import uuid`.
- **`core-api/.../tools/memclaw_procedure_{suggest,record,write}.py`** (new) — ToolSpecs (auto-discovered via pkgutil).

### PM-04 — Forge bridge
- **`core-api/.../services/forge/procedure_bridge.py`** (new) — `build_procedure_from_cluster` (tools_sequence from representative trace memory_ids; context from entities+goal; reliability seeded from cluster outcomes).
- **`core-api/.../services/forge/forge_service.py`** — `procedure_emitter` param + guarded emit after `candidate_writer`.
- **`core-api/.../services/forge/cron_handler.py`** — `_make_procedure_emitter`, wired into the cron call.

### PM-05 — telemetry loop
- **`core-api/.../services/procedure_service.py`** — `bump_skill_telemetry` (RMW of `documents.data.telemetry`, status untouched).
- **`core-api/.../mcp_server.py`** — record handler mirrors outcome to linked skill telemetry, quarantine logs lifecycle-review signal.

---

## Verification

### Local Tests (real Postgres + pgvector via `docker-compose.dev.yml db`)
```
# Migration
$ alembic upgrade head            # 022 → 023 applied
$ alembic downgrade -1 && upgrade head   # roundtrip clean

# core-api sprint tests (tests/, pythonpath = both src trees)
$ pytest tests/test_procedure_service.py tests/test_mcp_procedures.py tests/test_forge_procedure_bridge.py -q
19 passed

# storage sprint tests (PYTHONPATH=<repo root>)
$ pytest core-storage-api/tests/test_procedures.py -q
4 passed

# Forge regression (param addition is additive)
$ pytest tests/test_forge_distill.py tests/test_forge_cron_tick.py -q
80 passed
```
**Total: 23 new sprint tests green; 80 Forge regression green; ruff clean on all new files.**

### End-to-end loop proven (PM-03 e2e test)
`write → suggest (returns request_id + ranked) → record success×3 (reliability rises) → record failure×3 (quarantines) → suggest no longer returns it`. PM-05 adds: `record` against a Forge-linked procedure bumps the parent skill's `telemetry.fires_*`.

### Pre-existing failures (NOT caused by this sprint)
`tests/test_integration.py` shows 14 failures on **clean `main`** (verified by stash) in memories/entities/documents/agents/fleet — an environmental issue (test DB built from real migrations + `create_all`), orthogonal to procedural memory. This sprint adds zero new failures.

---

## Definition of Done Checklist

- [x] Dedicated `procedures` domain with migration, model, router, service
- [x] Runtime ranker reusing MemClaw embeddings (no Brain runtime import)
- [x] Three MCP tools registered and trust-gated
- [x] Reliability scoring + quarantine, verified end-to-end
- [x] Forge bridge emits linked procedures, additive + failure-isolated
- [x] Skill Factory Phase-4 telemetry implemented via the record path
- [x] All new code ruff-clean; 23 sprint tests pass

---

## Blocked / Carried Forward

### Backlog (next sprint)
| ID | Item | Type | Priority | Reason deferred |
|----|------|------|----------|-----------------|
| PM-N1 | Real tool-call capture into `session_traces.signals_summary` → swap `_extract_tools_sequence` off the memory_ids proxy | feature | P2 | Needs a harness-side signal extractor; v1 proxy is honest + functional |
| PM-N2 | Deploy procedural-memory MemClaw build (host TBD) | deployment | P2 | MemClaw not installed on .53 (verified); deploy is a separate effort |
| PM-N3 | Surface `memclaw_procedure_*` in the OpenClaw plugin `tools.json` | feature | P3 | Plugin sync via `scripts/export_tool_specs.py` |
| PM-N4 | Routing-weight learning / autotuner (Brain training subsystem) | feature | P3 | Out of scope by design; Forge + reliability loop already cover mining |
| PM-N5 | Reliability → skill-lifecycle transition (auto stale/quarantine of skills) | feature | P3 | PM-05 logs the signal; forcing RBAC-gated transitions needs design |

---

## Sprint Close Summary

**Sprint procedural-memory is CLOSED.** The objective was achieved: MemClaw now has a runtime procedural-memory loop (suggest/record/reliability/quarantine) that did not exist before, and it is wired into the existing Forge so mined skills become runtime-suggestable — completing the Skill Factory's own deferred Phase-4 outcome loop instead of duplicating Forge's mining.

### Key discoveries
1. **MemClaw's Skill Factory / Forge already IS the auto-learning loop** Brain's `failure_analyzer` + curriculum would have ported — mining outcome-labeled `session_traces` into skills. The real gap was the *runtime suggest + reliability-scoring half*, which this sprint delivered. This reshaped the plan from "port the mining subsystem" to "bridge into Forge."
2. **`VECTOR_DIM` is 1024 (bge-m3)**, not Brain's 768 (nomic) — pulled from `common.constants`, never hardcoded.
3. **`record` keys on `procedure_id`, not `request_id`** — avoids a server-side suggestion-signal store (Brain used `training_records` for this); cleaner and Forge owns trajectory capture.
4. **Pre-existing `test_integration.py` failures** in this environment are unrelated (confirmed via stash) — the test DB is built from real migrations *and* `Base.metadata.create_all`.

### What's left for next sprint
- Real tool-call capture (PM-N1) to replace the memory_ids `tools_sequence` proxy.
- Deployment (PM-N2) once a host is chosen.
- Plugin exposure (PM-N3).
