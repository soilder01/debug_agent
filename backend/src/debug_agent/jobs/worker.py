import asyncio
import threading
from collections.abc import Callable

from pydantic import BaseModel

from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob


class AsyncJobWorkerStatus(BaseModel):
    running: bool
    processed_count: int
    error_count: int
    last_error: str | None
    completion_hook_enabled: bool


class AsyncJobWorker:
    def __init__(
        self,
        service: DebugJobService,
        idle_sleep_seconds: float = 0.1,
        on_job_completed: Callable[[SubmittedDebugJob], None] | None = None,
    ) -> None:
        self._service = service
        self._idle_sleep_seconds = idle_sleep_seconds
        self._on_job_completed = on_job_completed
        self._thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._processed_count = 0
        self._error_count = 0
        self._last_error: str | None = None

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._stop_requested.clear()
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()
        return True

    async def stop(self) -> None:
        self._stop_requested.set()
        if self._thread is None:
            return
        await asyncio.to_thread(self._thread.join)

    async def tick(self) -> None:
        try:
            result = await self._service.run_next_job()
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            return
        if result is not None:
            self._processed_count += 1
            if result.status == "completed" and self._on_job_completed is not None:
                try:
                    self._on_job_completed(result)
                except Exception as exc:
                    self._error_count += 1
                    self._last_error = str(exc)

    def status(self) -> AsyncJobWorkerStatus:
        return AsyncJobWorkerStatus(
            running=self._thread is not None and self._thread.is_alive(),
            processed_count=self._processed_count,
            error_count=self._error_count,
            last_error=self._last_error,
            completion_hook_enabled=self._on_job_completed is not None,
        )

    def _run_in_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        while not self._stop_requested.is_set():
            await self.tick()
            await asyncio.sleep(self._idle_sleep_seconds)
