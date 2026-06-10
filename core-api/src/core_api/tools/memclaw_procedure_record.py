"""ToolSpec for memclaw_procedure_record — Procedural Memory (PM-03).

Records a success/failure outcome against a procedure: moves the
reliability counters, recomputes ``reliability_score``, and quarantines a
procedure that proves unreliable. The write side of the procedural loop;
trust ≥ 1.
"""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import ToolSpec

_DESCRIPTION = (
    "Report the outcome of following a procedure. procedure_id = the id from a "
    "memclaw_procedure_suggest result; outcome_type: success|failure. Updates the "
    "procedure's reliability_score and quarantines it once it has ≥3 attempts and a "
    "score below 0.3 (after which it stops being suggested). Optional request_id "
    "(from suggest), latency_ms, and validation_passed are recorded for telemetry. "
    "Trust ≥ 1 — agents can only record against procedures in their own tenant."
)

_SPEC = ToolSpec(
    name="memclaw_procedure_record",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_procedure_record,
    plugin_exposed=True,
    trust_required=1,
    impl_status="live",
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
