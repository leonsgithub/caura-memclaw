"""Tests for the Forge → procedures bridge (Procedural Memory PM-04).

Two layers:
  * unit — ``build_procedure_from_cluster`` derives a procedure payload
    (non-empty tools_sequence, context from entities/goal, reliability
    seeded from the cluster's outcome labels).
  * integration — ``run_forge_distill`` invokes an injected
    ``procedure_emitter`` once per minted skill, with skill_doc_id linkage,
    and a failing emitter never aborts the skill mint.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from core_api.services.forge.distill_prompt import DISTILL_SCHEMA_VERSION
from core_api.services.forge.forge_service import run_forge_distill
from core_api.services.forge.procedure_bridge import build_procedure_from_cluster
from core_api.services.session_trace import SessionTraceRow


def _trace(run_id="r1", agent_id="a1", outcome="success", entities=None, memory_ids=None):
    return SessionTraceRow(
        tenant_id="t1",
        fleet_id="f1",
        run_id=run_id,
        agent_id=agent_id,
        outcome_label=outcome,
        memory_ids=memory_ids if memory_ids is not None else [f"{run_id}-m1", f"{run_id}-m2"],
        entity_ids=entities if entities is not None else ["e1", "e2"],
        signals_summary={},
        started_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        ended_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
        goal_phrase="deploy eu-west fallback dns",
    )


_CANDIDATE_DOC = {
    "doc_id": "forge/deploy-eu-west-dns",
    "collection": "skills",
    "data": {
        "name": "Deploy to eu-west · fallback DNS at step 7",
        "slug": "deploy-eu-west-dns",
        "summary": "Switches to fallback DNS when step 7 hangs.",
        "goal": "Deploy to eu-west without hanging on step 7.",
        "cluster_fingerprint": "fp:v1:7a4f",
        "status": "candidate",
    },
}


# ── unit ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestBuildProcedureFromCluster:
    def test_tools_sequence_non_empty_from_representative(self):
        traces = [
            _trace("r1", "a1", memory_ids=["m1"]),
            _trace("r2", "a2", memory_ids=["x1", "x2", "x3"]),  # representative
        ]
        proc = build_procedure_from_cluster(
            traces, _CANDIDATE_DOC, tenant_id="t1", fleet_id="f1"
        )
        assert proc["tools_sequence"] == ["x1", "x2", "x3"]
        assert proc["skill_doc_id"] == "forge/deploy-eu-west-dns"
        assert proc["agent_id"] == "forge"
        assert proc["name"].startswith("Deploy to eu-west")
        assert proc["context_features"]["goal"]
        assert "e1" in proc["context_features"]["entities"]

    def test_reliability_seeded_high_from_successes(self):
        traces = [_trace(f"r{i}", f"a{i}", outcome="success") for i in range(4)]
        proc = build_procedure_from_cluster(
            traces, _CANDIDATE_DOC, tenant_id="t1", fleet_id="f1"
        )
        assert proc["stats"]["success_count"] == 4
        assert proc["stats"]["failure_count"] == 0
        assert proc["stats"]["reliability_score"] > 0.5

    def test_reliability_seeded_low_from_failures(self):
        traces = [_trace(f"r{i}", f"a{i}", outcome="failure") for i in range(4)]
        proc = build_procedure_from_cluster(
            traces, _CANDIDATE_DOC, tenant_id="t1", fleet_id="f1"
        )
        assert proc["stats"]["failure_count"] == 4
        assert proc["stats"]["reliability_score"] < 0.5


# ── integration with run_forge_distill ────────────────────────────


def _passing_traces(n: int) -> list[SessionTraceRow]:
    return [
        _trace(run_id=f"r{i}", agent_id=f"agent{i}", entities=["e1", "e2", "e3"],
               memory_ids=[f"m{i}-1", f"m{i}-2"])
        for i in range(n)
    ]


def _golden_llm_response() -> dict[str, Any]:
    return {
        "schema_version": DISTILL_SCHEMA_VERSION,
        "kind": "create",
        "goal_phrase": "deploy eu-west fallback dns step 7",
        "domain": "devops",
        "step_skeleton": ["preflight", "deploy", "switch dns", "verify"],
        "name": "Deploy to eu-west · fallback DNS at step 7",
        "slug": "deploy-eu-west-dns",
        "description": "Use fallback DNS resolver when eu-west deploy step 7 hangs.",
        "summary": "Switches to fallback DNS before retrying.",
        "content": "## When to use\n…\n## Steps\n1. …",
        "tags": ["deploy", "eu-west", "dns"],
        "evidence": "4 sessions / 3 agents, 100% success when applied.",
        "goal": "Deploy to eu-west without hanging on step 7.",
    }


async def _llm_returns_golden(_prompt: str) -> str:
    return json.dumps(_golden_llm_response())


async def _memory_fetcher_always(memory_ids: list[str]) -> dict[str, str]:
    return {mid: f"content of {mid}" for mid in memory_ids}


async def _poison_never(_fp: str) -> bool:
    return False


def _patch_build(monkeypatch, traces):
    async def fake_build(*_a, **_k):
        return traces
    import core_api.services.forge.forge_service as svc
    monkeypatch.setattr(svc, "build_session_traces", fake_build)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_forge_emits_linked_procedure(monkeypatch):
    _patch_build(monkeypatch, _passing_traces(4))
    skills: list[dict] = []
    procs: list[dict] = []

    async def writer(doc):
        skills.append(doc)

    async def emitter(proc):
        procs.append(proc)

    result = await run_forge_distill(
        run_label="test-run",
        tenant_id="acme",
        fleet_id="ops",
        window_start=datetime(2026, 5, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 15, tzinfo=timezone.utc),
        llm_fn=_llm_returns_golden,
        memory_fetcher=_memory_fetcher_always,
        poison_checker=_poison_never,
        candidate_writer=writer,
        procedure_emitter=emitter,
    )
    assert result.candidates_written == 1
    assert len(skills) == 1
    assert len(procs) == 1
    proc = procs[0]
    assert proc["skill_doc_id"] == skills[0]["doc_id"]
    assert proc["tools_sequence"]  # non-empty
    assert proc["tenant_id"] == "acme"
    assert proc["stats"]["reliability_score"] > 0.5  # all-success cluster


@pytest.mark.unit
@pytest.mark.asyncio
async def test_emitter_failure_does_not_abort_mint(monkeypatch):
    _patch_build(monkeypatch, _passing_traces(4))
    skills: list[dict] = []

    async def writer(doc):
        skills.append(doc)

    async def boom(_proc):
        raise RuntimeError("storage down")

    result = await run_forge_distill(
        run_label="test-run",
        tenant_id="acme",
        fleet_id="ops",
        window_start=datetime(2026, 5, 1, tzinfo=timezone.utc),
        window_end=datetime(2026, 5, 15, tzinfo=timezone.utc),
        llm_fn=_llm_returns_golden,
        memory_fetcher=_memory_fetcher_always,
        poison_checker=_poison_never,
        candidate_writer=writer,
        procedure_emitter=boom,
    )
    # Skill mint succeeded despite the emitter raising.
    assert result.candidates_written == 1
    assert len(skills) == 1
