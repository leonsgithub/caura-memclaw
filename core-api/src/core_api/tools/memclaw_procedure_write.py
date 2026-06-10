"""ToolSpec for memclaw_procedure_write — Procedural Memory (PM-03).

Explicitly captures a procedure (tool-call sequence + context). Embeds the
procedure with MemClaw's embedder so it is semantically suggestable, then
persists it with a fresh reliability row. Trust ≥ 1. Forge-mined
procedures arrive via the PM-04 bridge, not this tool.
"""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import ToolSpec

_DESCRIPTION = (
    "Capture a reusable procedure: name, tools_sequence (ordered tool-call ids), and "
    "context_features (when it applies). Optionally pass pattern_signature, "
    "reasoning_guide, risk_level (low|medium|high), and fleet_id. The procedure is "
    "embedded so memclaw_procedure_suggest can surface it, and starts at reliability "
    "0.5 until outcomes are recorded. Trust ≥ 1."
)

_SPEC = ToolSpec(
    name="memclaw_procedure_write",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_procedure_write,
    plugin_exposed=True,
    trust_required=1,
    impl_status="live",
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
