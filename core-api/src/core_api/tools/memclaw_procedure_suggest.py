"""ToolSpec for memclaw_procedure_suggest — Procedural Memory (PM-03).

Suggests reliability-ranked tool-call procedures for the caller's current
context. Read-only (trust 0); quarantined procedures are excluded. Returns
a request_id the agent echoes back via ``memclaw_procedure_record``.
"""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import ToolSpec

_DESCRIPTION = (
    "Suggest reliability-ranked tool-call procedures for the current task. Pass "
    "context_features (framework, region, library, …) and an optional task goal; "
    "get back a request_id plus ranked procedures (id, name, tools_sequence, score). "
    "Follow one, then report how it went with memclaw_procedure_record using that "
    "procedure's id. Read-only; quarantined (proven-unreliable) procedures are excluded."
)

_SPEC = ToolSpec(
    name="memclaw_procedure_suggest",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_procedure_suggest,
    plugin_exposed=True,
    trust_required=0,
    impl_status="live",
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
