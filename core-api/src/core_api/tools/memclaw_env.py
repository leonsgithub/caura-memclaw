"""ToolSpec for memclaw_env — stable-infra fact store (BP-03).

Env truths are named, tenant-wide facts (URLs, ports, hostnames) stored
as documents in the reserved '_env_truths' collection.  A verify op bumps
verification_count + verified_at without touching the value, matching the
Brain upsert_env_truth / verify_env_truth semantics without a new migration.
"""

from core_api import mcp_server

from ._builders import mcp_register
from ._registry import register
from ._types import OpSpec, ToolSpec

_DESCRIPTION = (
    "Stable-infra fact store. op: upsert|get|list|verify. "
    "upsert(name, value) writes a named fact (URL, port, hostname) tenant-wide; "
    "re-upsert with a new value resets verification_count. "
    "verify(name) bumps verification_count and verified_at without changing the value. "
    "get(name) returns value + confidence + verified_at + verification_count. "
    "list returns all env truths for this tenant."
)

_SPEC = ToolSpec(
    name="memclaw_env",
    description=_DESCRIPTION,
    handler=mcp_server.memclaw_env,
    plugin_exposed=True,
    trust_required=0,
    ops=(
        OpSpec(
            name="upsert",
            description="Write or update a named infra fact. Resets verification_count when value changes.",
            required_params=("name", "value"),
            trust_required=1,
        ),
        OpSpec(
            name="get",
            description="Retrieve a single env truth by name.",
            required_params=("name",),
        ),
        OpSpec(
            name="list",
            description="List all env truths for this tenant.",
            required_params=(),
        ),
        OpSpec(
            name="verify",
            description="Confirm a fact is still accurate; bumps verification_count and verified_at.",
            required_params=("name",),
        ),
    ),
    error_codes=("INVALID_ARGUMENTS", "NOT_FOUND", "INTERNAL_ERROR"),
)
register(_SPEC)
mcp_register(mcp_server.mcp, _SPEC)
