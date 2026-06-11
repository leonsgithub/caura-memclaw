# Procedural-Memory MemClaw — Deploy & Global Claude Code Integration

**Status:** LIVE 2026-06-11. Registered globally in Claude Code (user scope).
**Host:** `192.168.1.53` (alongside the brain stack).
**MCP endpoint:** `http://192.168.1.53:8000/mcp` — exposes `memclaw_procedure_suggest` / `_record` / `_write` (+ 12 other memclaw tools).

---

## What runs where

| Container | Host port | Notes |
|-----------|-----------|-------|
| `caura-memclaw-core-api-1` | 8000 | REST + MCP gateway. **This is what Claude connects to.** |
| `caura-memclaw-core-storage-api-1` | 8012 | remapped from 8002 (brain dashboard owns 8002) |
| `caura-memclaw-db-1` | 5432 | pgvector/pg16 (brain's db is on 5433 — no clash) |
| `caura-memclaw-redis-1` | 6379 | |

All four are `restart: unless-stopped` (see `docker-compose.override.yml`) → survive reboot.

## Config

- Source: fork `leonsgithub/caura-memclaw`, branch `feat/sprint-procedural-memory`, cloned to `~/dev/caura-memclaw` on .53.
- Images **built from source** (`docker compose build core-storage-api core-api`) — the published ghcr.io images do NOT contain the procedure tools.
- `env.dev` (tracked) provides the base: `IS_STANDALONE=true`, `USE_LLM_FOR_MEMORY_CREATION=false`.
- `.env` (untracked, mode 600) overrides:
  - `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY=sk-proj-…` (1024-dim via `text-embedding-3-small` + `OPENAI_EMBEDDING_SEND_DIMENSIONS=true`)
  - `STORAGE_API_PORT=8012`
- **Auth:** standalone mode → no API key required on the MCP; tenant is `default`. The procedure tools don't call `_require_trust`, so they work with the default agent.

## Reproduce / restart

```bash
ssh ubuntu@192.168.1.53
cd ~/dev/caura-memclaw
docker compose up -d            # start (images already built)
docker compose build core-storage-api core-api && docker compose up -d   # rebuild after a git pull
docker compose logs -f core-api # tail
```

Migrations run automatically on `core-storage-api` startup (alembic → head `023`).

## Global Claude Code registration

```bash
claude mcp add --scope user --transport http memclaw http://192.168.1.53:8000/mcp
claude mcp list   # memclaw: … ✓ Connected
```

Writes to `~/.claude.json` → available in **all projects**. Remove with `claude mcp remove memclaw -s user`.

## Verification (all passed 2026-06-11)

- `GET /api/v1/health` → `{"status":"ok","storage":"connected","redis":"connected"}`
- MCP `tools/list` → 15 tools incl. the 3 `memclaw_procedure_*`
- End-to-end via MCP: `write` (OpenAI embedding stored) → `suggest` (ranked, request_id) → `record` (reliability 0.5 → 0.667)
- `claude mcp list` → `memclaw … ✓ Connected` (user scope)

## Notes / caveats

- **.53 is resource-tight** (2.5 GB RAM, ~6 GB free disk after build) and shares the box with brain. Both stacks coexist with ~1.5 GB RAM free. If contention shows up, move this stack to the workstation (192.168.1.112, 15 GB RAM) — same steps, register `http://192.168.1.112:8000/mcp`.
- **Embedder swap** is one `.env` line + `docker compose up -d`: local TEI bge-m3 (`--profile embed-local`, needs RAM .53 lacks) or any 1024-dim OpenAI-compatible endpoint. Clawrouter (192.168.1.181:9000) is 768-dim → incompatible without a `VECTOR_DIM` change.
- The OpenAI key is only in `.53:~/dev/caura-memclaw/.env` (mode 600). It is **not** committed.
