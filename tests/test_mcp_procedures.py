"""End-to-end tests for the procedural-memory MCP tools (PM-03).

Exercises the real handlers (memclaw_procedure_suggest / _record / _write)
and the real ranker, with an in-memory fake storage client standing in for
core-storage. Verifies the loop: write → suggest → record success raises
reliability → record failures quarantine → quarantined drops out of suggest.
"""

from __future__ import annotations

import uuid

import pytest

from core_api import mcp_server
from core_api.services import procedure_service
from tests._mcp_test_helpers import parse_envelope


class FakeStorage:
    """Minimal in-memory stand-in for the procedures storage surface."""

    def __init__(self) -> None:
        self.procs: dict[str, dict] = {}

    async def create_procedure(self, data: dict) -> dict:
        pid = uuid.uuid4().hex
        proc = dict(data)
        proc["id"] = pid
        proc.setdefault("stats", {})
        proc["stats"] = {
            "procedure_id": pid,
            "success_count": proc["stats"].get("success_count", 0),
            "failure_count": proc["stats"].get("failure_count", 0),
            "reliability_score": proc["stats"].get("reliability_score", 0.5),
            "is_quarantined": proc["stats"].get("is_quarantined", False),
        }
        self.procs[pid] = proc
        return proc

    async def get_procedure(self, pid: str) -> dict | None:
        return self.procs.get(pid)

    async def list_procedures(
        self, tenant_id, *, fleet_id=None, include_quarantined=False, limit=200
    ) -> list[dict]:
        out = []
        for p in self.procs.values():
            if p.get("tenant_id") != tenant_id:
                continue
            if fleet_id is not None and p.get("fleet_id") != fleet_id:
                continue
            if not include_quarantined and p["stats"].get("is_quarantined"):
                continue
            out.append(p)
        return out[:limit]

    async def update_procedure_stats(self, pid: str, patch: dict) -> dict:
        self.procs[pid]["stats"].update(patch)
        return self.procs[pid]["stats"]


@pytest.fixture
def proc_env(monkeypatch):
    """Patch auth + wire a shared FakeStorage into handler and ranker."""
    storage = FakeStorage()
    tenant = "test-tenant"

    monkeypatch.setattr(mcp_server, "_check_auth", lambda: None)
    monkeypatch.setattr(mcp_server, "_check_write_scope", lambda: None)
    monkeypatch.setattr(mcp_server, "_get_tenant", lambda: tenant)
    monkeypatch.setattr(mcp_server, "_get_agent_id", lambda: "agent-x")
    monkeypatch.setattr(
        mcp_server, "_refuse_default_agent_on_gateway", lambda a: None
    )
    monkeypatch.setattr(mcp_server, "get_storage_client", lambda: storage)
    monkeypatch.setattr(procedure_service, "get_storage_client", lambda: storage)

    async def _no_embed(text, tenant_config=None, instruction=None):
        return None

    monkeypatch.setattr(procedure_service, "get_query_embedding", _no_embed)
    # memclaw_procedure_write imports get_query_embedding from common.embedding
    import common.embedding

    monkeypatch.setattr(common.embedding, "get_query_embedding", _no_embed)
    return {"storage": storage, "tenant": tenant}


async def _write_proc(name="deploy-eu-west", context=None):
    return await mcp_server.memclaw_procedure_write(
        name=name,
        tools_sequence=["bash:deploy", "bash:check", "bash:retry"],
        context_features=context or {"framework": "terraform", "region": "eu-west"},
    )


@pytest.mark.asyncio
async def test_write_then_suggest_returns_request_id(proc_env):
    await _write_proc()
    out = await mcp_server.memclaw_procedure_suggest(
        context_features={"framework": "terraform", "region": "eu-west"},
        task="deploy to eu-west",
    )
    payload = parse_envelope(out)
    assert "request_id" in payload
    assert payload["count"] == 1
    assert payload["procedures"][0]["name"] == "deploy-eu-west"
    assert payload["procedures"][0]["tools_sequence"] == [
        "bash:deploy",
        "bash:check",
        "bash:retry",
    ]


@pytest.mark.asyncio
async def test_record_success_raises_reliability(proc_env):
    created = parse_envelope(await _write_proc())
    pid = created["id"]
    assert created["stats"]["reliability_score"] == 0.5

    last = None
    for _ in range(3):
        last = parse_envelope(
            await mcp_server.memclaw_procedure_record(
                procedure_id=pid, outcome_type="success"
            )
        )
    assert last["reliability_score"] > 0.5
    assert last["is_quarantined"] is False


@pytest.mark.asyncio
async def test_record_failures_quarantine_and_drop_from_suggest(proc_env):
    created = parse_envelope(await _write_proc())
    pid = created["id"]

    # Three failures: reliability falls below 0.3 with >=3 attempts → quarantine.
    last = None
    for _ in range(3):
        last = parse_envelope(
            await mcp_server.memclaw_procedure_record(
                procedure_id=pid, outcome_type="failure"
            )
        )
    assert last["is_quarantined"] is True
    assert last["reliability_score"] < 0.3

    # Quarantined procedure no longer surfaces in suggest.
    suggest = parse_envelope(
        await mcp_server.memclaw_procedure_suggest(
            context_features={"framework": "terraform", "region": "eu-west"}
        )
    )
    assert suggest["count"] == 0


@pytest.mark.asyncio
async def test_record_rejects_bad_outcome_type(proc_env):
    created = parse_envelope(await _write_proc())
    out = await mcp_server.memclaw_procedure_record(
        procedure_id=created["id"], outcome_type="maybe"
    )
    env = parse_envelope(out)
    assert env.get("error", {}).get("code") == "INVALID_ARGUMENTS"


@pytest.mark.asyncio
async def test_record_unknown_procedure_returns_not_found(proc_env):
    out = await mcp_server.memclaw_procedure_record(
        procedure_id="does-not-exist", outcome_type="success"
    )
    env = parse_envelope(out)
    assert env.get("error", {}).get("code") == "NOT_FOUND"
