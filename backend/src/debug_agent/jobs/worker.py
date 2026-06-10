import asyncio

from pydantic import BaseModel

from debug_agent.jobs.service import DebugJobService


class AsyncJobWorkerStatus(BaseModel):
    running: bool
    processed_count: int
    error_count: int
    last_error: str | None


class AsyncJobWorker:
    def __init__(self, service: DebugJobService, idle_sleep_seconds: float = 0.1) -> None:
        self._service = service
        self._idle_sleep_seconds = idle_sleep_seconds
        self._task: asyncio.Task[None] | None = None
        self._stop_requested = False
        self._processed_count = 0
        self._error_count = 0
        self._last_error: str | None = None

    def start(self) -> bool:
        if self._task is not None and not self._task.done():
            return False
        self._stop_requested = False
        self._task = asyncio.create_task(self._run())
        return True

    async def stop(self) -> None:
        self._stop_requested = True
        if self._task is None:
            return
        await self._task

    async def tick(self) -> None:
        try:
            result = await self._service.run_next_job()
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            return
        if result is not None:
            self._processed_count += 1

    def status(self) -> AsyncJobWorkerStatus:
        return AsyncJobWorkerStatus(
            running=self._task is not None and not self._task.done(),
            processed_count=self._processed_count,
            error_count=self._error_count,
            last_error=self._last_error,
        )

    async def _run(self) -> None:
        while not self._stop_requested:
            await self.tick()
            await asyncio.sleep(self._idle_sleep_seconds)
