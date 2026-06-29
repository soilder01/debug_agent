from __future__ import annotations

from fastapi import APIRouter, Query

from debug_agent.api.schemas import PerformanceSummaryResponse
from debug_agent.telemetry.performance import performance_summary


def build_system_router() -> APIRouter:
    router = APIRouter()
    router.get("/health")(health)
    router.get("/performance/summary")(get_performance_summary)
    router.get("/api/performance/summary")(get_performance_summary)
    return router


def health() -> dict[str, str]:
    return {"status": "ok", "service": "debug-agent-backend"}


def get_performance_summary(
    component: str | None = None,
    operation: str | None = None,
    limit: int = Query(default=50, ge=0, le=200),
) -> PerformanceSummaryResponse:
    return PerformanceSummaryResponse.model_validate(
        performance_summary(component=component, operation=operation, limit=limit)
    )
