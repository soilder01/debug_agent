from time import perf_counter

from fastapi import FastAPI, Request

from debug_agent.api.routes import router
from debug_agent.telemetry.performance import record_performance_event

app = FastAPI(title="Handwriting OCR Debug Agent", version="0.1.0")
app.include_router(router)


@app.middleware("http")
async def record_api_performance(request: Request, call_next):
    started_at = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        record_performance_event(
            component="api",
            operation=f"{request.method} {route_path}",
            duration_ms=int((perf_counter() - started_at) * 1000),
            status="failed" if status_code >= 500 else "succeeded",
            metadata={"status_code": status_code},
        )
