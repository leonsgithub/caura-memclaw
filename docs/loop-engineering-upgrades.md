> ## ⚠️ SUPERSEDED — 2026-06-26
>
> **This design was scrapped before implementation. Five-sixths of it was a category error. Kept as a historical record; do not build from it.**
>
> The premise below — "elevate MemClaw to **100% support** for Loop Engineering" — is the wrong goal. After re-reading the source paper (`/home/leon/dev/research/learningsystem/Loop-Engineering-IEEE.pdf`), the load-bearing thesis is explicit (Table V, §VII.E, §XII):
>
> > **"Loop engineering is a set of capabilities, not a product."**
>
> A loop has **six organs**, and they live in the **harness**, not in any one tool:
>
> | Organ | Move | Where it lives |
> |---|---|---|
> | Automations | Scheduling | Claude Code `/loop`, Cloud Routines, GH Actions |
> | Worktrees | Handoff | git `--worktree` |
> | Skills | Discovery | `SKILL.md` |
> | Connectors | Persistence/Discovery | MCP |
> | Sub-agents | Verification | `.claude/agents/reviewer.md` + `/goal` |
> | **Memory** | **Persistence** | **on-disk state — this is MemClaw** |
>
> MemClaw is **one** organ: **Memory**. This doc had the memory store grow three organs the harness already owns:
>
> - **Upgrade A (`verify_run`)** — put a subprocess-sandbox *evaluator* inside the memory store. But the evaluator is a separate **agent** (Fig. 3), a harness organ — not a function call in MemClaw. **Dropped.**
> - **Upgrade B (`cost_audit` / TDCF)** — instrumented an **invented** formula, `base_cost × 2^(turn_distance/10)`. The paper's "cost scales with turns survived" (§II.C) is *motivational intuition for why verification matters*, not a mechanism it proposes building. Speculative gold-plating. **Dropped.**
> - **Upgrade C (`schedule_loop`)** — reinvented the harness's **scheduling** organ (`/loop` + Cloud Routines) inside a memory server; the worker even punted payload execution back to the harness, making it pure duplication. **Dropped.**
>
> **What survived:** the one genuinely in-lane gap — the paper's *Nodding Loop* (§VI.A), an agent grading its own homework. `memclaw_procedure_record` already accepts `validation_passed` but **silently drops it**, so procedure reliability moves on self-reported `outcome_type` alone. The replacement sprint wires that one field through so an *independent* evaluator's verdict is distinguishable from a self-graded one — MemClaw staying in its Memory lane and being honest about what verified vs. merely claimed.
>
> **Replacement plan:** [`sprints/sprint-loop-engineering/capability_tasks.json`](../sprints/sprint-loop-engineering/capability_tasks.json) (LE-01 + signoff). Reframed goal: *MemClaw is the best possible Memory organ in someone else's loop, not the whole loop.*
>
> ---

# Loop Engineering Capability Upgrades for MemClaw

This design document outlines three discrete architectural and feature additions to MemClaw, elevating it to 100% support for the Loop Engineering paradigm. These upgrades specifically address the major gaps in **Isolated Verification (Idea 3)**, **Turn-Distance Cost Optimization (Idea 4)**, and **Proactive Propulsion/Scheduling (Idea 2 & 5)**.

---

## 1. Overview & Architectural Realignment

By closing these three gaps, MemClaw shifts from a **reactive memory store** that logs history to a **proactive feedback substrate** that drives self-correcting agent loops.

```
       DURABLE CONTEXT (Idea 1 substrate: write/recall)
                           │
                           ▼
  🤖 GENERATOR AGENT  ───►  🔄 PROACTIVE SCHEDULING (Upgrade C: schedule_loop)
         ▲                 │  (Spins up next cycle autonomously)
         │                 ▼
         └─────  🔬 ISOLATED EVALUATOR AGENT (Upgrade A: verify_run)
                 (Runs tests, curls, audits; records turn_distance in Upgrade B)
```

---

## 2. Upgrade A: Isolated Verification Subsystem (GAP: Idea 3)

### 2.1 Motivation
Tuning a self-critical generator fails because the generator and its internal checker share representation patterns and cognitive priors. If the generator is blind to a design flaw, its self-correction is equally blind. We require a separate **Evaluator Agent** that *acts* — executing tests, calling URLs, inspecting filesystem side-effects — structurally isolated from the generator.

### 2.2 Core Design: Sandboxed Evaluator & `verification_runs`
We introduce an asynchronous verification system. Verification runs in a separate execution boundary, using distinct, non-persisted agent prompts.

1. **Database Schema**: Add the `verification_runs` table.
   ```sql
   CREATE TABLE verification_runs (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       org_id VARCHAR(255) NOT NULL,
       run_id VARCHAR(255) NOT NULL,            -- Associated generator trace
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       status VARCHAR(50) NOT NULL,             -- 'pending', 'passed', 'failed', 'error'
       target_branch VARCHAR(255),
       criteria JSONB NOT NULL,                 -- Action specification (commands, curls)
       results JSONB,                           -- stdout/stderr, execution logs, exit codes
       verified_by VARCHAR(255) NOT NULL        -- 'evaluator' vs 'human'
   );
   ```

2. **Verification Actions**:
   Verification is defined by an array of executable operations:
   - `command` — executes shell tests (e.g. `pytest tests/test_auth.py`).
   - `http_check` — performs explicit API calls and expects specific statuses / JSON values.
   - `fs_audit` — checks file existence, size, permissions, or structural content.

3. **Active Weight Telemetry Integration**:
   Whenever a verification run completes:
   - If it **passes**: Associated procedures used in the generation trace gain a reliability bonus (+0.1) and clear failure states.
   - If it **fails**: Associated procedures Used in the generation trace are heavily penalized (-0.3). If a procedure suffers $\geq 3$ consecutive failures and score dips below $0.3$, it is auto-quarantined. This closes the telemetry loop with hard test metrics instead of subjective generator claims.

### 2.3 MCP Tool Surface
We introduce the `memclaw_verify_run` tool to the MCP surface:

```json
{
  "name": "memclaw_verify_run",
  "description": "Trigger an isolated verification run against a completed task branch/state. Executes command, http, or filesystem checks in a sandboxed, separate-agent environment, logging precise execution telemetry.",
  "parameters": {
    "type": "object",
    "properties": {
      "run_id": {
        "type": "string",
        "description": "The generator session run ID to verify."
      },
      "criteria": {
        "type": "array",
        "description": "List of verification operations requested.",
        "items": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["command", "http", "filesystem"] },
            "target": { "type": "string", "description": "Command string, URL, or filepath" },
            "expected": { "type": "string", "description": "Regex matching output, status code, or hash" }
          },
          "required": ["type", "target"]
        }
      }
    },
    "required": ["run_id", "criteria"]
  }
}
```

---

## 3. Upgrade B: Turn-Distance Cost Optimization (GAP: Idea 4)

### 3.1 Motivation
The cost of an error scales exponentially with the distance in conversation turns between its introduction and discovery. A bug addressed in turn $T+1$ is trivial; a bug discovered in turn $T+50$ forces expensive rollbacks and refactors. MemClaw must track this distance metric and provide early signals to force corrective actions before the turn distance grows toxic.

### 3.2 Core Design: Tracking & Penalizing Drift
We augment trace logging and memory metadata with turn indices.

1. **Session & Turn Indexes**:
   - Every `write` or `recall` records the current session's sequential `turn_index`.
   - When **Conflict & Contradiction Signal (SF-102 Signal 1)** detects a collision:
     - Resolve the memory's `introduced_at_turn` and current `conflict_detected_at_turn`.
     - Calculate:
       $$\text{turn\_distance} = T_{\text{conflict}} - T_{\text{introduced}}$$
     - If $\text{turn\_distance}$ spans multiple sessions, map it to cumulative elapsed system turns for the associated tenant/project scope.

2. **The Loop Cost Function**:
   - The system tracks a rolling **Turn-Distance Cost Factor (TDCF)**:
     $$\text{TDCF} = \text{base\_cost} \times 2^{\frac{\text{turn\_distance}}{10}}$$
   - A rolling average of TDCF is exposed via `memclaw_stats`.
   - High TDCF (e.g. contradictions popping up 25+ turns later) triggers a warning on the controller dashboard ("High turn-distance detected for core config. Prompt/State alignment is drifting").

### 3.3 MCP Tool Surface
We introduce `memclaw_cost_audit` to allow agents or controllers to check state drift liability:

```json
{
  "name": "memclaw_cost_audit",
  "description": "Analyze recent memory usages and contradiction cycles. Returns turn-distance metrics, identifying high-cost state drift (stale memories used across dozens of turns before correction) and issuing early warning flags.",
  "parameters": {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "default": 10 }
    }
  }
}
```

---

## 4. Upgrade C: Proactive Propulsion Scheduling (GAP: Idea 2 & 5)

### 4.1 Motivation
Currently, MemClaw's scheduling is administrative (background maintenance like purging/archiving). In loop engineering, scheduling must be **proactive and task-directed**. The loop must propel itself: when an agent is waiting for external dependencies (a physical build, a deploy, a long CI pipeline, or a morning cron), it must programmatically plan and spawn its next execution turn.

### 4.2 Core Design: Propulsion Tickets & Triggers
We introduce **Propulsion Tickets** stored in a designated collection `__loop_propulsion__` within the document store.

1. **Ticket Anatomy**:
   ```json
   {
     "ticket_id": "prop_88291a8f",
     "run_id": "run_auth_overhaul",
     "scheduled_at": "2026-06-26T14:30:00Z",
     "trigger": {
       "type": "event | time | webhook",
       "value": "ci_pipeline_complete | delay_seconds=1800 | cron_expression"
     },
     "task_payload": {
       "prompt": "Evaluate the auth test logs and fix any remaining failures.",
       "context_filters": { "scope": "auth/tenant_isolation" }
     },
     "lifecycle_status": "queued | fired | abandoned | succeeded"
   }
   ```

2. **The Worker Loop Engine**:
   The lifecycle audit driver/cron (`POST /admin/lifecycle/fanout/loops`) continuously:
   - Evaluates active time-based triggers that have passed their deadline.
   - Listens to registered webhooks (e.g., CI completion notification).
   - Resolves target conditions, posts a task back to the execution harness queue, and boots the agent back up with the specified payload and the restored context state. This achieves autonomous cross-session continuation.

### 4.3 MCP Tool Surface
We expose `memclaw_schedule_loop` to give the agent full propulsion controller capability:

```json
{
  "name": "memclaw_schedule_loop",
  "description": "Schedule programmatically the next cycle/turn of the current loop. Takes a target trigger condition (delay, cron, or explicit webhook status) and bundles the task payload with session context so execution resumes autonomously.",
  "parameters": {
    "type": "object",
    "properties": {
      "trigger_type": { "type": "string", "enum": ["delay", "cron", "webhook_event"] },
      "trigger_value": { "type": "string", "description": "Seconds to delay, cron rule, or event label name" },
      "task_prompt": { "type": "string", "description": "The instructions for the next agent iteration on wakeup." },
      "context_keys": {
        "type": "array",
        "description": "Specific memory IDs or collections to seed as hot context upon wakeup.",
        "items": { "type": "string" }
      }
    },
    "required": ["trigger_type", "trigger_value", "task_prompt"]
  }
}
```

---

## 5. Summary of Verification Goals

To prove these three capabilities are fully operational, the test suite must exercise:
1. **Isolated Verification**:
   - Seed a fake flaky procedure.
   - Trigger `memclaw_verify_run` with failing mock tests on a branch.
   - Asset that the procedure is immediately docked in reliability score and gets auto-quarantined on the 3rd fail, failing the gate pre-promotion.
2. **Turn Distance**:
   - Write memory $M$ at Turn 1.
   - Edit/re-write a contradictory memory $M'$ at Turn 25.
   - Run `memclaw_cost_audit` and verify it reports a contradiction turn distance of exactly 24, calculating the appropriate exponential cost warning.
3. **Propulsion Scheduling**:
   - Call `memclaw_schedule_loop` with a 2-second delay.
   - Assert the ticket is stored in the `__loop_propulsion__` collection and moves from `queued` to `fired` when the lifecycle tick triggers.
