# MemClaw Improvement Ideas

Synthesized from Hermes DevOps feedback and meow-171 comparison notes.

---

## 1. Reduce OpenAI dependency

**Problem:** Every write calls OpenAI's embedding API. If OpenAI is down, writes fail. Adds per-op cost and ~500ms latency. Breaks in air-gap/offline environments.

**Ideas:**
- Local embedder fallback (e.g. `nomic-embed-text` via Ollama) configurable in `.env`
- Write queue that retries on OpenAI failure instead of hard-failing the tool call
- Optional embedding-free "lite" mode for ephemeral/low-value memories

---

## 2. Auto-recall wiring (reduce "remember to query" burden)

**Problem:** Unlike Mnemosyne (auto-injects into system prompt), MemClaw requires the agent to explicitly call `memclaw_recall`. Agents forget. The SOUL.md hook partially solves this but it's fragile and project-specific.

**Ideas:**
- Official session-start hook or MCP lifecycle event that fires `memclaw_recall` automatically
- "Warm context" endpoint: returns a compact summary of the agent's top-N most relevant memories for injection into system prompt on session start — combines Mnemosyne's zero-overhead injection with MemClaw's semantic retrieval

---

## 3. Default namespace isolation

**Problem:** Isolation is not automatic — agents must consciously choose and enforce `fleet`/`scope_agent`/`scope_team` model. Easy to accidentally bleed memories across agents.

**Ideas:**
- Default `visibility` on write should be `scope_agent` (not `scope_org`) unless explicitly widened
- Registration step should require explicit scoping declaration, not let it default to global
- Warn (or block) on write when `agent_id` is not set

---

## 4. Lower setup friction

**Problem:** MCP config + headers + registration + scoping discipline is medium-complexity vs Honcho's `hermes memory setup`. Barrier to adoption.

**Ideas:**
- `memclaw-init` CLI that generates the MCP config block, registers the agent, and validates the connection in one command
- Header defaults baked into the MCP server config so clients don't need to pass `X-Agent-ID` every call

---

## 5. Migration tooling (Mnemosyne / Honcho → MemClaw)

**Problem:** No migration path from Mnemosyne (§-delimited flat file) or Honcho. Users who want to upgrade lose existing memories.

**Ideas:**
- `memclaw-import --from mnemosyne <profile.txt>` that parses §-delimited blocks and bulk-writes them
- Honcho export → MemClaw import (depends on Honcho's export format)

---

## 6. Latency improvements

**Problem:** 500–1500ms per op is the top objection vs local-first alternatives.

**Ideas:**
- Redis cache for recent recalls by `(agent_id, query_hash)` — already have Redis in the stack
- Batch embedding endpoint: write N memories in one OpenAI call instead of N calls
- Pre-warm: on agent registration, embed and cache the agent's top-K memories so first recall is fast

---

## 7. "Hot memory" injection (hybrid mode)

**Problem:** Mnemosyne's zero-latency auto-injection is genuinely useful for always-relevant facts (user name, env, preferences). MemClaw forces a round-trip even for these.

**Idea:** `memclaw_hot` tag on memories — flagged memories get included in a lightweight "warm context" payload returned at session start, no separate recall needed. Agent gets the best of both: semantic search for deep recall, instant injection for hot facts.

---

## 8. Observability surface

**Problem:** Health endpoint exists but there's no easy way to see memory health over time, procedure reliability trends, or which agents are most/least active.

**Ideas:**
- `memclaw_stats` tool already exists — expose a simple HTML dashboard from the server (single-page, no framework)
- Procedure reliability trend: graph success rate over time per procedure so agents know when a procedure is degrading
- Per-agent memory audit: list all memories by agent, flag stale/conflicted ones

---

## 9. Keystone visibility

**Problem:** Keystone rules are MemClaw's strongest safety differentiator but aren't surfaced to agents at recall time — agents may not know which keystones apply.

**Idea:** Include active keystone summaries in `memclaw_recall` response when relevant (e.g. if recall touches a domain covered by a keystone, surface the rule). Makes safety rails visible rather than silent.

---

## Priority order (rough)

| # | Idea | Effort | Impact |
|---|------|--------|--------|
| 2 | Auto-recall wiring | Low | High — removes #1 adoption friction |
| 3 | Default namespace isolation | Low | High — prevents cross-agent bleed |
| 6 | Redis recall cache | Low | High — already have Redis |
| 1 | Local embedder fallback | Medium | High — removes hard OpenAI dependency |
| 4 | `memclaw-init` CLI | Medium | Medium — lowers barrier to new agents |
| 7 | Hot memory injection | Medium | Medium — closes Mnemosyne UX gap |
| 5 | Migration tooling | Medium | Medium — enables upgrades from Mnemosyne |
| 8 | Observability dashboard | Medium | Low-Medium — ops quality of life |
| 9 | Keystone visibility in recall | Low | Low-Medium — polish |
