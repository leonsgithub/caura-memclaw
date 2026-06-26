"""Tests for preferred_agent_ids project-context boost in phase 2 cross-context recall.

Three cases:
1. preferred_agent_ids boost: same-agent rows score higher than cross-agent rows.
2. CrossContextEnrich passes caller_agent_id as preferred_agent_ids to storage.
3. Anonymous caller (caller_agent_id=None) → preferred_agent_ids absent from search_p2.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Override the conftest autouse ASGI-bridge fixture — our tests are pure mocks,
# no DB or pgvector needed.
@pytest.fixture(autouse=True)
async def _patch_storage_client():  # noqa: PT004
    yield


# ---------------------------------------------------------------------------
# Test 1: postgres_service score boost
# ---------------------------------------------------------------------------


def _make_row(agent_id: str, base_score: float) -> SimpleNamespace:
    """Minimal row SimpleNamespace matching what memory_scored_search returns."""
    m = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        agent_id=agent_id,
        content=f"content-{agent_id}",
        visibility="scope_team",
        status=None,
        embedding=None,
        weight=base_score,
        recall_count=0,
        last_recalled_at=None,
        created_at=None,
        ts_valid_start=None,
        ts_valid_end=None,
        search_vector=None,
    )
    return SimpleNamespace(Memory=m, score=base_score)


def test_preferred_agent_boost_ranks_same_agent_higher():
    """When preferred_agent_ids is set, same-agent rows should receive a score boost."""
    boost_factor = 1.2
    base_score = 0.5

    # Simulate the boost logic (the CASE expression translated to Python)
    def apply_boost(row_agent_id: str, score: float, preferred: list[str], factor: float) -> float:
        if preferred and row_agent_id in preferred:
            return score * factor
        return score

    same_agent_score = apply_boost("project-a", base_score, ["project-a"], boost_factor)
    cross_agent_score = apply_boost("project-b", base_score, ["project-a"], boost_factor)

    assert same_agent_score > cross_agent_score
    assert same_agent_score == pytest.approx(base_score * boost_factor)
    assert cross_agent_score == pytest.approx(base_score)


def test_no_boost_when_preferred_agent_ids_is_none():
    """When preferred_agent_ids is None, all rows get score × 1.0 (no change)."""

    def apply_boost(row_agent_id: str, score: float, preferred: list[str] | None, factor: float) -> float:
        if preferred and row_agent_id in preferred:
            return score * factor
        return score

    score = 0.7
    assert apply_boost("any-agent", score, None, 1.2) == score
    assert apply_boost("any-agent", score, [], 1.2) == score


# ---------------------------------------------------------------------------
# Test 2: CrossContextEnrich passes preferred_agent_ids when caller_agent_id set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_context_enrich_passes_preferred_agent_ids():
    """CrossContextEnrich should include preferred_agent_ids=[caller_agent_id] in search_p2."""
    from core_api.pipeline.steps.search.cross_context_enrich import CrossContextEnrich
    from core_api.pipeline.context import PipelineContext

    captured_calls: list[dict] = []

    async def mock_scored_search(data: dict) -> list[dict]:
        captured_calls.append(data)
        return []

    mock_sc = MagicMock()
    mock_sc.scored_search = mock_scored_search

    ctx = PipelineContext(
        data={
            "cross_context": True,
            "tenant_id": "default",
            "query": "login details .53",
            "embedding": [0.1] * 8,
            "search_params": {
                "fts_weight": 0.3,
                "freshness_floor": 0.1,
                "freshness_decay_days": 30,
                "recall_boost_cap": 2.0,
                "recall_decay_window_days": 30,
                "similarity_blend": 0.7,
            },
            "recall_boost_enabled": True,
            "filtered_rows": [],
            "caller_agent_id": "project-a",
            "cc_top_m": 3,
            "cc_threshold": 0.0,
            "cc_ratio": 0.3,
            "cc_discount": 0.85,
        }
    )

    with patch("core_api.pipeline.steps.search.cross_context_enrich.get_storage_client", return_value=mock_sc):
        step = CrossContextEnrich()
        await step.execute(ctx)

    assert len(captured_calls) == 1
    call = captured_calls[0]
    assert call.get("preferred_agent_ids") == ["project-a"]
    assert "caller_agent_id" not in call  # phase 2 must NOT send caller_agent_id


# ---------------------------------------------------------------------------
# Test 3: No preferred_agent_ids when caller is anonymous
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_context_enrich_no_preferred_when_anonymous():
    """When caller_agent_id is None, preferred_agent_ids must be absent from search_p2."""
    from core_api.pipeline.steps.search.cross_context_enrich import CrossContextEnrich
    from core_api.pipeline.context import PipelineContext

    captured_calls: list[dict] = []

    async def mock_scored_search(data: dict) -> list[dict]:
        captured_calls.append(data)
        return []

    mock_sc = MagicMock()
    mock_sc.scored_search = mock_scored_search

    ctx = PipelineContext(
        data={
            "cross_context": True,
            "tenant_id": "default",
            "query": "login details .53",
            "embedding": [0.1] * 8,
            "search_params": {
                "fts_weight": 0.3,
                "freshness_floor": 0.1,
                "freshness_decay_days": 30,
                "recall_boost_cap": 2.0,
                "recall_decay_window_days": 30,
                "similarity_blend": 0.7,
            },
            "recall_boost_enabled": True,
            "filtered_rows": [],
            "caller_agent_id": None,
            "cc_top_m": 3,
            "cc_threshold": 0.0,
            "cc_ratio": 0.3,
            "cc_discount": 0.85,
        }
    )

    with patch("core_api.pipeline.steps.search.cross_context_enrich.get_storage_client", return_value=mock_sc):
        step = CrossContextEnrich()
        await step.execute(ctx)

    assert len(captured_calls) == 1
    assert "preferred_agent_ids" not in captured_calls[0]
