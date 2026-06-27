"""BP-03: memclaw_env — stable-infra fact store (env truths)."""

from __future__ import annotations

import pytest

from core_api import mcp_server
from tests._mcp_test_helpers import parse_envelope


class FakeDocStore:
    """Minimal in-memory document store for the env-truth surface tests."""

    def __init__(self) -> None:
        self._docs: dict[tuple[str, str, str], dict] = {}

    async def get_document(self, tenant_id, collection, doc_id, *, read=True, readable_tenant_ids=None):
        return self._docs.get((tenant_id, collection, doc_id))

    async def upsert_document(self, data: dict) -> dict:
        # Mirror the storage-side guard: the public write path refuses
        # '_'-prefixed (system-managed) collections. Env truths live in
        # '_env_truths', so a regression that routes them here would 400
        # in production — make the double fail loudly instead of silently
        # accepting it (the bug this test now guards against).
        if data["collection"].startswith("_"):
            raise RuntimeError(
                f"Collection '{data['collection']}' is system-managed; "
                "use upsert_document_system."
            )
        return await self.upsert_document_system(data)

    async def upsert_document_system(self, data: dict) -> dict:
        key = (data["tenant_id"], data["collection"], data["doc_id"])
        self._docs[key] = dict(data)
        return data

    async def list_documents(self, tenant_id, collection, fleet_id=None, limit=50, offset=0):
        return [
            {**v, "doc_id": k[2]}
            for k, v in self._docs.items()
            if k[0] == tenant_id and k[1] == collection
        ]


@pytest.fixture
def env_env(monkeypatch):
    store = FakeDocStore()
    monkeypatch.setattr(mcp_server, "_check_auth", lambda: None)
    monkeypatch.setattr(mcp_server, "_check_write_scope", lambda: None)
    monkeypatch.setattr(mcp_server, "_get_tenant", lambda: "test-tenant")
    monkeypatch.setattr(mcp_server, "_get_agent_id", lambda: "agent-x")
    monkeypatch.setattr(mcp_server, "get_storage_client", lambda: store)
    return store


@pytest.mark.asyncio
async def test_env_full_lifecycle(env_env):
    """Acceptance criteria: upsert → verify×2 (count==2, value unchanged) →
    upsert new value (count resets) → list → missing key NOT_FOUND."""
    # Upsert initial value
    out = parse_envelope(
        await mcp_server.memclaw_env(op="upsert", name="brain_url", value="http://192.168.1.53:9001/mcp")
    )
    assert out["ok"] is True
    assert out["verification_count"] == 0
    initial_verified_at = out["verified_at"]

    # Verify twice — count climbs, value unchanged
    for expected_count in (1, 2):
        v = parse_envelope(await mcp_server.memclaw_env(op="verify", name="brain_url"))
        assert v["value"] == "http://192.168.1.53:9001/mcp"
        assert v["verification_count"] == expected_count
        assert v["verified_at"] >= initial_verified_at

    # get returns same fields
    got = parse_envelope(await mcp_server.memclaw_env(op="get", name="brain_url"))
    assert got["verification_count"] == 2
    assert got["value"] == "http://192.168.1.53:9001/mcp"

    # Upsert new value → count resets
    out2 = parse_envelope(
        await mcp_server.memclaw_env(op="upsert", name="brain_url", value="http://192.168.1.53:9002/mcp")
    )
    assert out2["verification_count"] == 0
    assert out2["value"] == "http://192.168.1.53:9002/mcp"

    # list returns it
    lst = parse_envelope(await mcp_server.memclaw_env(op="list"))
    assert lst["count"] == 1
    assert lst["truths"][0]["name"] == "brain_url"

    # missing key → NOT_FOUND
    missing = parse_envelope(await mcp_server.memclaw_env(op="get", name="does-not-exist"))
    assert missing.get("error", {}).get("code") == "NOT_FOUND"


@pytest.mark.asyncio
async def test_env_upsert_same_value_keeps_count(env_env):
    """Re-upsert with the same value preserves verification_count."""
    await mcp_server.memclaw_env(op="upsert", name="port", value="9001")
    await mcp_server.memclaw_env(op="verify", name="port")
    # Same value → count not reset
    out = parse_envelope(await mcp_server.memclaw_env(op="upsert", name="port", value="9001"))
    assert out["verification_count"] == 1

    # Different value → count resets
    out2 = parse_envelope(await mcp_server.memclaw_env(op="upsert", name="port", value="9002"))
    assert out2["verification_count"] == 0


@pytest.mark.asyncio
async def test_env_invalid_op_and_missing_params(env_env):
    bad_op = parse_envelope(await mcp_server.memclaw_env(op="frobnicate", name="x"))
    assert bad_op.get("error", {}).get("code") == "INVALID_ARGUMENTS"

    no_name = parse_envelope(await mcp_server.memclaw_env(op="get"))
    assert no_name.get("error", {}).get("code") == "INVALID_ARGUMENTS"

    no_value = parse_envelope(await mcp_server.memclaw_env(op="upsert", name="x"))
    assert no_value.get("error", {}).get("code") == "INVALID_ARGUMENTS"
