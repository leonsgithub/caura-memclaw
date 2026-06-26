"""ToolSpec for memclaw_export — visibility-scoped bulk memory export (BP-04)."""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import ToolSpec

_DESCRIPTION = (
    "Bulk-export memories for the calling tenant. "
    "scope: agent (own only, default) | team | org | all — mirrors memclaw_list visibility. "
    "format: json (envelope with count/records/next_cursor) or jsonl (newline-delimited records). "
    "Paginate with cursor from next_cursor. "
    "Each record: id, content, type, created_at, weight, agent_id, visibility. "
    "trust>=1 required (bulk egress surface)."
)

_SPEC = ToolSpec(
    name="memclaw_export",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_export,
    plugin_exposed=True,
    trust_required=1,
    error_codes=("INVALID_ARGUMENTS", "FORBIDDEN", "INTERNAL_ERROR"),
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
