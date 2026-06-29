from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from typing import Iterator
from contextlib import contextmanager


TelemetryValue = str | int | float | bool | None


@dataclass(frozen=True)
class PerformanceEvent:
    component: str
    operation: str
    duration_ms: int
    status: str = "succeeded"
    metadata: dict[str, TelemetryValue] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PerformanceRecorder:
    def __init__(self, *, max_events: int = 2_000) -> None:
        self._events: deque[PerformanceEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def record(
        self,
        *,
        component: str,
        operation: str,
        duration_ms: int,
        status: str = "succeeded",
        metadata: dict[str, TelemetryValue] | None = None,
    ) -> PerformanceEvent:
        event = PerformanceEvent(
            component=component,
            operation=operation,
            duration_ms=max(0, int(duration_ms)),
            status=status,
            metadata=_clean_metadata(metadata or {}),
        )
        with self._lock:
            self._events.append(event)
        return event

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    def events(
        self,
        *,
        component: str | None = None,
        operation: str | None = None,
        limit: int = 50,
    ) -> list[PerformanceEvent]:
        with self._lock:
            events = list(self._events)
        filtered = _filter_events(events, component=component, operation=operation)
        return filtered[-limit:]

    def summary(
        self,
        *,
        component: str | None = None,
        operation: str | None = None,
        limit: int = 50,
    ) -> dict[str, object]:
        with self._lock:
            events = list(self._events)
        filtered = _filter_events(events, component=component, operation=operation)
        return {
            "total_count": len(filtered),
            "aggregates": _aggregate_events(filtered),
            "recent_events": [
                _event_dict(event)
                for event in filtered[-limit:]
            ],
        }


performance_recorder = PerformanceRecorder()


def record_performance_event(
    *,
    component: str,
    operation: str,
    duration_ms: int,
    status: str = "succeeded",
    metadata: dict[str, TelemetryValue] | None = None,
) -> PerformanceEvent:
    return performance_recorder.record(
        component=component,
        operation=operation,
        duration_ms=duration_ms,
        status=status,
        metadata=metadata,
    )


@contextmanager
def measure_performance(
    *,
    component: str,
    operation: str,
    metadata: dict[str, TelemetryValue] | None = None,
) -> Iterator[None]:
    started_at = perf_counter()
    status = "succeeded"
    failure_metadata: dict[str, TelemetryValue] = {}
    try:
        yield
    except Exception as exc:
        status = "failed"
        failure_metadata = {"error_type": type(exc).__name__}
        raise
    finally:
        record_performance_event(
            component=component,
            operation=operation,
            duration_ms=int((perf_counter() - started_at) * 1000),
            status=status,
            metadata={**(metadata or {}), **failure_metadata},
        )


def performance_summary(
    *,
    component: str | None = None,
    operation: str | None = None,
    limit: int = 50,
) -> dict[str, object]:
    return performance_recorder.summary(component=component, operation=operation, limit=limit)


def recent_performance_events(
    *,
    component: str | None = None,
    operation: str | None = None,
    limit: int = 50,
) -> list[PerformanceEvent]:
    return performance_recorder.events(component=component, operation=operation, limit=limit)


def _filter_events(
    events: list[PerformanceEvent],
    *,
    component: str | None,
    operation: str | None,
) -> list[PerformanceEvent]:
    return [
        event
        for event in events
        if (component is None or event.component == component)
        and (operation is None or event.operation == operation)
    ]


def _aggregate_events(events: list[PerformanceEvent]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[PerformanceEvent]] = {}
    for event in events:
        buckets.setdefault((event.component, event.operation), []).append(event)
    aggregates: list[dict[str, object]] = []
    for (component, operation), bucket in sorted(buckets.items()):
        durations = sorted(event.duration_ms for event in bucket)
        aggregates.append(
            {
                "component": component,
                "operation": operation,
                "count": len(bucket),
                "failed_count": sum(1 for event in bucket if event.status != "succeeded"),
                "avg_ms": round(sum(durations) / len(durations), 2),
                "p50_ms": _percentile(durations, 0.50),
                "p95_ms": _percentile(durations, 0.95),
                "max_ms": max(durations),
                "latest_ms": bucket[-1].duration_ms,
            }
        )
    return aggregates


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    index = min(len(sorted_values) - 1, max(0, int(round((len(sorted_values) - 1) * percentile))))
    return sorted_values[index]


def _event_dict(event: PerformanceEvent) -> dict[str, object]:
    return {
        "component": event.component,
        "operation": event.operation,
        "duration_ms": event.duration_ms,
        "status": event.status,
        "metadata": event.metadata,
        "occurred_at": event.occurred_at.isoformat(),
    }


def _clean_metadata(metadata: dict[str, TelemetryValue]) -> dict[str, TelemetryValue]:
    return {str(key): value for key, value in metadata.items() if value is None or isinstance(value, str | int | float | bool)}
