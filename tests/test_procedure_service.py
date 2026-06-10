"""Unit tests for the procedure ranker (Procedural Memory PM-02).

Pure algorithmic — the storage client and embedding provider are mocked,
so no Postgres or embedder is required. Verifies the reliability-weighted
ordering that makes procedural suggestion useful, plus the helper math.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from core_api.services import procedure_service as ps


def _proc(name: str, reliability: float, context: dict | None = None) -> dict:
    return {
        "id": f"id-{name}",
        "name": name,
        "context_features": context or {"framework": "terraform", "region": "eu-west"},
        "embedding": None,  # force semantic=0 so reliability/context decide
        "stats": {"reliability_score": reliability, "is_quarantined": False},
    }


@pytest.mark.unit
class TestRankerMath:
    def test_context_overlap_jaccard(self):
        a = {"framework": "terraform", "region": "eu-west"}
        assert ps._context_overlap(a, a) == 1.0
        assert ps._context_overlap(a, {"framework": "ansible"}) < 1.0
        assert ps._context_overlap({}, a) == 0.0

    def test_cosine_guards(self):
        assert ps._cosine(None, [1.0]) == 0.0
        assert ps._cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
        assert ps._cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_compute_reliability_monotonic(self):
        assert ps.compute_reliability(0, 0) == 0.5
        assert ps.compute_reliability(5, 0) > 0.5
        assert ps.compute_reliability(0, 5) < 0.5
        # more wins → higher; more losses → lower
        assert ps.compute_reliability(9, 1) > ps.compute_reliability(5, 5)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rank_orders_by_reliability_when_context_equal():
    """Same context + no embeddings → reliability_score decides order."""
    candidates = [
        _proc("low", 0.2),
        _proc("high", 0.9),
        _proc("mid", 0.55),
    ]
    fake_sc = AsyncMock()
    fake_sc.list_procedures = AsyncMock(return_value=candidates)

    with patch.object(ps, "get_storage_client", return_value=fake_sc), patch.object(
        ps, "get_query_embedding", new=AsyncMock(return_value=None)
    ):
        ranked = await ps.rank_procedures(
            "tenant-x",
            {"framework": "terraform", "region": "eu-west"},
            task="deploy to eu-west",
        )

    names = [r["procedure"]["name"] for r in ranked]
    assert names == ["high", "mid", "low"]
    assert ranked[0]["breakdown"]["reliability"] == 0.9


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rank_rewards_context_match():
    """A better context match outranks a higher-reliability poor match."""
    strong_match = _proc(
        "match", 0.5, context={"framework": "terraform", "region": "eu-west"}
    )
    weak_match = _proc("nomatch", 0.6, context={"framework": "ansible"})
    fake_sc = AsyncMock()
    fake_sc.list_procedures = AsyncMock(return_value=[weak_match, strong_match])

    with patch.object(ps, "get_storage_client", return_value=fake_sc), patch.object(
        ps, "get_query_embedding", new=AsyncMock(return_value=None)
    ):
        ranked = await ps.rank_procedures(
            "tenant-x",
            {"framework": "terraform", "region": "eu-west"},
        )

    assert ranked[0]["procedure"]["name"] == "match"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rank_empty_when_no_candidates():
    fake_sc = AsyncMock()
    fake_sc.list_procedures = AsyncMock(return_value=[])
    with patch.object(ps, "get_storage_client", return_value=fake_sc):
        ranked = await ps.rank_procedures("tenant-x", {"framework": "terraform"})
    assert ranked == []
