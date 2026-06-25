"""Shared agent-id constants.

A tiny, dependency-free module so both the MCP server (``mcp_server``) and the
REST routes (``routes.memories``) can reference the reserved default identity
without importing each other — avoids the heavy/cross-private import that would
otherwise couple the route module to the whole MCP tool surface.
"""

import os

# Reserved fallback identity used when a caller omits ``agent_id`` on the
# single-tenant / standalone path. On the enterprise gateway this value is
# explicitly refused (see ``mcp_server._refuse_default_agent_on_gateway``) so
# anonymous writes are never silently attributed to one shared identity.
#
# Override per-deployment with ``MEMCLAW_DEFAULT_AGENT_ID`` (e.g.
# ``caura-memclaw-ab12cd`` = project slug + a stable host fingerprint) so an
# omitted ``agent_id`` lands in a recognisable bucket instead of the generic
# ``mcp-agent``. Keep it STABLE — it is the memory-ownership key; a value that
# changes over time orphans prior memories and resets trust registration.
DEFAULT_AGENT_ID = os.environ.get("MEMCLAW_DEFAULT_AGENT_ID", "").strip() or "mcp-agent"
