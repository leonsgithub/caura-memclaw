"""ToolSpec for memclaw_review — low-weight memory curation surface (BP-05)."""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import ToolSpec

_DESCRIPTION = (
    "Read-only curation surface. Returns memories flagged by low weight, "
    "sorted ascending (worst-rated first). "
    "threshold: max weight to include (default 0.4). "
    "scope: agent (own only, default) | all (full tenant). "
    "Each record includes weight + recall_count as triage signals. "
    "Act on results via memclaw_manage (transition to outdated/archived). "
    "Mirrors Brain review_low_rated."
)

_SPEC = ToolSpec(
    name="memclaw_review",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_review,
    plugin_exposed=True,
    trust_required=0,
    error_codes=("INVALID_ARGUMENTS", "INTERNAL_ERROR"),
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
