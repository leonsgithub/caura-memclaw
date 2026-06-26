"""CrossContextEnrich — Phase 2 cross-context retrieval.

Runs after PostFilterResults. When cross_context=True, re-issues the same
query embedding without a caller_agent_id (→ storage returns only scope_team
/ scope_org rows), applies a lower threshold and a score discount, then
appends the surviving rows to filtered_rows capped at cc_ratio of the total.

This surfaces shared/infra knowledge that Phase 1 might crowd out with
higher-scoring own memories — same pattern as Brain MCP's 2-phase retrieval.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

from core_api.clients.storage_client import get_storage_client
from core_api.constants import SEARCH_OVERFETCH_FACTOR
from core_api.pipeline.context import PipelineContext
from core_api.pipeline.step import StepOutcome, StepResult
from core_api.schemas import EntityLinkOut

logger = logging.getLogger(__name__)


class CrossContextEnrich:
    @property
    def name(self) -> str:
        return "cross_context_enrich"

    async def execute(self, ctx: PipelineContext) -> StepResult | None:
        if not ctx.data.get("cross_context"):
            return StepResult(outcome=StepOutcome.SKIPPED)

        data = ctx.data
        phase1 = data["filtered_rows"]
        phase1_ids = {str(r.Memory.id) for r in phase1}

        embedding = data.get("embedding")
        if not embedding:
            logger.warning("cross_context_enrich: no embedding in ctx, skipping Phase 2")
            return StepResult(outcome=StepOutcome.SKIPPED)

        top_m = data.get("cc_top_m", 3)
        threshold = data.get("cc_threshold", 0.15)
        ratio = data.get("cc_ratio", 0.3)
        discount = data.get("cc_discount", 0.85)

        # ponytail: no caller_agent_id → scope_team/scope_org only; preferred_agent_ids boosts same-project hits
        search_p2: dict = {
            "tenant_id": data["tenant_id"],
            "query": data["query"],
            "embedding": embedding,
            "search_params": data["search_params"],
            "top_k": top_m * SEARCH_OVERFETCH_FACTOR,
            "recall_boost_enabled": data.get("recall_boost_enabled", True),
        }
        if data.get("caller_agent_id"):
            search_p2["preferred_agent_ids"] = [data["caller_agent_id"]]
        readable = data.get("readable_tenant_ids")
        if readable and readable != [data["tenant_id"]]:
            search_p2["readable_tenant_ids"] = readable

        sc = get_storage_client()
        try:
            p2_rows = await sc.scored_search(search_p2)
        except Exception:
            logger.warning("cross_context_enrich: Phase 2 search failed, skipping", exc_info=True)
            return StepResult(outcome=StepOutcome.SKIPPED)

        cross: list[SimpleNamespace] = []
        for row in p2_rows:
            if str(row.get("id", "")) in phase1_ids:
                continue
            vec_sim = row.get("vec_sim") or row.get("similarity") or 0
            if float(vec_sim) < threshold:
                continue
            ns = SimpleNamespace(
                Memory=SimpleNamespace(
                    **{
                        k: v
                        for k, v in row.items()
                        if k
                        not in (
                            "score",
                            "similarity",
                            "vec_sim",
                            "fts_score",
                            "freshness",
                            "entity_boost",
                            "recall_boost",
                            "temporal_boost",
                            "status_penalty",
                            "entity_links",
                            "has_embedding",
                        )
                    }
                ),
                score=round(float(row.get("score", vec_sim)) * discount, 4),
                similarity=row.get("similarity"),
                vec_sim=row.get("vec_sim"),
                fts_score=row.get("fts_score"),
                freshness=row.get("freshness"),
                entity_boost=row.get("entity_boost"),
                recall_boost=row.get("recall_boost"),
                temporal_boost=row.get("temporal_boost"),
                status_penalty=row.get("status_penalty"),
                has_embedding=row.get("has_embedding", True),
                entity_links=[
                    EntityLinkOut(entity_id=lnk["entity_id"], role=lnk.get("role"))
                    for lnk in row.get("entity_links", [])
                ],
            )
            ns.Memory.source_type = "cross_context"
            cross.append(ns)
            if len(cross) >= top_m:
                break

        if not cross:
            return None

        max_cross = max(1, int((len(phase1) + len(cross)) * ratio))
        cross = cross[:max_cross]

        data["filtered_rows"].extend(cross)
        logger.debug(
            "cross_context_enrich: added %d Phase 2 rows (cap=%d, phase1=%d)",
            len(cross),
            max_cross,
            len(phase1),
        )
        return None
