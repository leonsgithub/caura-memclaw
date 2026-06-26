"""BP-04: memclaw_export — visibility-scoped bulk memory export."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest

from core_api import mcp_server
from tests._mcp_test_helpers import parse_envelope


def _make_row(agent_id: str, content: str, visibility: str = "scope_agent") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": "test-tenant",
        "agent_id": agent_id,
        "content": content,
        "memory_type": "episodic",
        "created_at": datetime.now(UTC).isoformat(),
        "weight": 0.5,
        "visibility": visibility,
    }


class FakeMemoryStore:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    async def list_memories_by_filters(self, payload: dict) -> list[dict]:
        written_by = payload.get("written_by")
        if written_by:
            return [r for r in self._rows if r["agent_id"] == written_by]
        return list(self._rows)


@pytest.fixture
def export_env(monkeypatch):
    rows = [
        _make_row("agent-a", "alpha memory"),
        _make_row("agent-a", "alpha memory 2"),
        _make_row("agent-b", "beta private memory"),
    ]
    store = FakeMemoryStore(rows)
    monkeypatch.setattr(mcp_server, "_check_auth", lambda: None)
    monkeypatch.setattr(mcp_server, "_get_tenant", lambda: "test-tenant")
    monkeypatch.setattr(mcp_server, "_get_agent_id", lambda: "agent-a")
    monkeypatch.setattr(mcp_server, "get_storage_client", lambda: store)

    async def _fake_require_trust(tenant_id, agent_id, min_level=0):
        return (min_level, None, None)

    monkeypatch.setattr(mcp_server, "_require_trust", _fake_require_trust)
    monkeypatch.setattr(mcp_server, "_get_readable_tenants", lambda: None)
    return store


@pytest.mark.asyncio
async def test_export_scope_agent_excludes_other_agent(export_env):
    """Agent A's export (scope=agent) must not include agent B's memories."""
    out = parse_envelope(
        await mcp_server.memclaw_export(scope="agent", agent_id="agent-a")
    )
    assert "error" not in out
    assert out["count"] == 2
    ids_returned = {r["agent_id"] for r in out["records"]}
    assert "agent-b" not in ids_returned
    assert "agent-a" in ids_returned


@pytest.mark.asyncio
async def test_export_scope_all_includes_all(export_env):
    """scope=all returns all rows visible to this tenant."""
    out = parse_envelope(
        await mcp_server.memclaw_export(scope="all", agent_id="agent-a")
    )
    assert out["count"] == 3


@pytest.mark.asyncio
async def test_export_stable_record_fields(export_env):
    """Every record has the documented stable fields."""
    out = parse_envelope(
        await mcp_server.memclaw_export(scope="agent", agent_id="agent-a")
    )
    for rec in out["records"]:
        for field in ("id", "content", "type", "created_at", "weight", "agent_id", "visibility"):
            assert field in rec, f"Missing field '{field}' in record"


@pytest.mark.asyncio
async def test_export_jsonl_format(export_env):
    """format=jsonl returns newline-delimited JSON records."""
    raw = await mcp_server.memclaw_export(scope="agent", format="jsonl", agent_id="agent-a")
    # Strip latency trailer before splitting
    body = raw.split("\n\n_latency_ms:")[0]
    lines = [l for l in body.splitlines() if l.strip()]
    assert len(lines) == 2
    for line in lines:
        rec = json.loads(line)
        assert "id" in rec and "content" in rec


@pytest.mark.asyncio
async def test_export_invalid_scope_and_format(export_env):
    bad_scope = parse_envelope(await mcp_server.memclaw_export(scope="galaxy"))
    assert bad_scope.get("error", {}).get("code") == "INVALID_ARGUMENTS"

    bad_fmt = parse_envelope(await mcp_server.memclaw_export(format="csv"))
    assert bad_fmt.get("error", {}).get("code") == "INVALID_ARGUMENTS"
