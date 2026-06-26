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
    "score below 0.3 (after which it stops being suggested). "
    "Set validation_passed=True ONLY when the outcome was checked by an INDEPENDENT "
    "verifier (a separate evaluator agent / test run / CI gate — not the same agent "
    "that ran the procedure self-grading). Verified outcomes additionally move a "
    "verified-counter pair and surface 'verified_reliability' in the response, "
    "distinguishing a proven-reliable procedure from one with only self-reported "
    "wins. Leave validation_passed unset/None for self-reported outcomes. "
    "Optional request_id (from suggest) and latency_ms are recorded for telemetry. "
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
