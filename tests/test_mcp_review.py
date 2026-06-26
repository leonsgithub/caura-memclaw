"""BP-05: memclaw_review — low-weight memory curation surface."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from core_api import mcp_server
from tests._mcp_test_helpers import parse_envelope


def _make_row(agent_id: str, content: str, weight: float) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": "test-tenant",
        "agent_id": agent_id,
        "content": content,
        "memory_type": "episodic",
        "created_at": datetime.now(UTC).isoformat(),
        "weight": weight,
        "recall_count": 0,
        "status": "active",
        "visibility": "scope_agent",
    }


class FakeMemoryStore:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    async def list_memories_by_filters(self, payload: dict) -> list[dict]:
        weight_max = payload.get("weight_max")
        written_by = payload.get("written_by")
        order = payload.get("order", "desc")
        limit = payload.get("limit", 50)

        result = list(self._rows)
        if written_by:
            result = [r for r in result if r["agent_id"] == written_by]
        if weight_max is not None:
            result = [r for r in result if r["weight"] <= weight_max]
        result.sort(key=lambda r: r["weight"], reverse=(order == "desc"))
        return result[:limit]


@pytest.fixture
def review_env(monkeypatch):
    rows = [
        _make_row("agent-a", "high quality memory", 0.9),
        _make_row("agent-a", "medium memory", 0.5),
        _make_row("agent-a", "low quality memory", 0.2),
        _make_row("agent-a", "very low memory", 0.1),
        _make_row("agent-b", "other agent private", 0.15),
    ]
    store = FakeMemoryStore(rows)
    monkeypatch.setattr(mcp_server, "_check_auth", lambda: None)
    monkeypatch.setattr(mcp_server, "_get_tenant", lambda: "test-tenant")
    monkeypatch.setattr(mcp_server, "_get_agent_id", lambda: "agent-a")
    monkeypatch.setattr(mcp_server, "get_storage_client", lambda: store)
    return store


@pytest.mark.asyncio
async def test_review_returns_only_below_threshold(review_env):
    """Only memories at or below threshold are returned."""
    out = parse_envelope(await mcp_server.memclaw_review(threshold=0.4, agent_id="agent-a"))
    assert out["count"] == 2
    assert all(r["weight"] <= 0.4 for r in out["flagged"])


@pytest.mark.asyncio
async def test_review_ascending_weight_order(review_env):
    """Results are sorted ascending by weight (worst first)."""
    out = parse_envelope(await mcp_server.memclaw_review(threshold=0.5, agent_id="agent-a"))
    weights = [r["weight"] for r in out["flagged"]]
    assert weights == sorted(weights), "Expected ascending weight order"


@pytest.mark.asyncio
async def test_review_scope_agent_excludes_other_agent(review_env):
    """scope=agent does not expose another agent's memories."""
    out = parse_envelope(
        await mcp_server.memclaw_review(threshold=0.5, scope="agent", agent_id="agent-a")
    )
    agent_ids = {r["agent_id"] for r in out["flagged"]}
    assert "agent-b" not in agent_ids


@pytest.mark.asyncio
async def test_review_record_has_signal_fields(review_env):
    """Every flagged record carries weight + recall_count as triage signals."""
    out = parse_envelope(await mcp_server.memclaw_review(threshold=0.9, agent_id="agent-a"))
    for rec in out["flagged"]:
        assert "weight" in rec
        assert "recall_count" in rec
        assert "id" in rec and "content" in rec


@pytest.mark.asyncio
async def test_review_invalid_scope(review_env):
    out = parse_envelope(await mcp_server.memclaw_review(scope="galaxy"))
    assert out.get("error", {}).get("code") == "INVALID_ARGUMENTS"
