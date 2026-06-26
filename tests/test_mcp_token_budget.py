"""Lock the tools/list token count so it can't silently regress.

Asserts ``tools/list`` encodes to ≤ ``CEILING_TOKENS`` cl100k tokens.

Skipped if ``tiktoken`` isn't installed (the package is available in this
repo's venv; a dev running the suite without it just skips this gate).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


tiktoken = pytest.importorskip("tiktoken")

FIXTURES = Path(__file__).parent / "fixtures"

# Measured count after adding memclaw_keystones / memclaw_keystones_set
# (12 tools, CAURA-000): 4906 cl100k. Was 4796 with the 12 tools before
# Phase B's skills migration trimmed it to 10.
#
# 2026-05-14 (FRICTION-REPORT-V3 D5/D6): 5061 cl100k after expanding the
# keystones descriptions to (a) clarify ``agent_id`` is the TARGET agent
# for ``scope=agent`` and must NOT be passed for tenant/fleet scope, and
# (b) call out the ``rules`` (not ``keystones``) response-key shape. The
# external dev who wrote the v3 friction report lost ~10 minutes total
# to those two misreads; the +155 tokens per session are worth more than
# that across the install base.
#
# 2026-06-26: 7353 cl100k. The 5200 ceiling silently lapsed — this gate is
# ``pytest.importorskip("tiktoken")``-guarded and tiktoken was absent from the
# CI/dev env while the surface grew from 12 tools to 20: the 4 procedural-memory
# tools, memclaw_env (BP-03), memclaw_export (BP-04), memclaw_review (BP-05), and
# memclaw_session_start (UX-03). Those 8 tools are the bulk of the +2292; the
# Loop Engineering validation_passed guidance on memclaw_procedure_record added
# 82. Re-baselined to 7500 (current + ~150 headroom) so the gate guards against
# the NEXT silent regression. If trimming is wanted, the procedure/keystones
# descriptions are the longest and the first place to cut.
CEILING_TOKENS = 7500


def _count(path: Path) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    data = json.loads(path.read_text())
    return len(enc.encode(json.dumps(data, separators=(",", ":"))))


def test_tokens_under_ceiling():
    tokens = _count(FIXTURES / "tools_list_baseline_v1.json")
    assert tokens <= CEILING_TOKENS, (
        f"tools/list is {tokens} cl100k tokens — over the {CEILING_TOKENS} "
        "ceiling. If the growth is intentional, raise CEILING_TOKENS in "
        "tests/test_mcp_token_budget.py and document the reason."
    )


@pytest.mark.asyncio
async def test_v1_baseline_matches_live_registry():
    """Guard against a stale baseline fixture — regenerate if this fails."""
    from core_api import mcp_server

    tools = await mcp_server.mcp.list_tools()
    live = []
    for t in tools:
        d = t.model_dump(mode="json") if hasattr(t, "model_dump") else dict(t.__dict__)
        live.append(d)
    live.sort(key=lambda x: x["name"])

    baseline = json.loads((FIXTURES / "tools_list_baseline_v1.json").read_text())
    baseline.sort(key=lambda x: x["name"])
    assert live == baseline, (
        "tools/list output has drifted from tools_list_baseline_v1.json. "
        "If intentional, regenerate the fixture via the snippet in "
        "tests/fixtures/README.md (or scripts/export_tool_specs.py + the "
        "live capture script)."
    )
