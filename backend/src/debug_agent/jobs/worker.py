import asyncio
import inspect
import threading
from collections.abc import Callable

from pydantic import BaseModel

from debug_agent.jobs.service import DebugJobService, SubmittedDebugJob


class AsyncJobWorkerStatus(BaseModel):
    running: bool
    max_concurrency: int
    active_count: int
    processed_count: int
    error_count: int
    recovered_stale_job_count: int
    last_error: str | None
    completion_hook_enabled: bool


class AsyncJobWorker:
    def __init__(
        self,
        service: DebugJobService,
        idle_sleep_seconds: float = 0.1,
        max_concurrency: int = 1,
        stale_running_job_seconds: float | None = 15 * 60,
        on_job_completed: Callable[[SubmittedDebugJob], object] | None = None,
    ) -> None:
        self._service = service
        self._idle_sleep_seconds = idle_sleep_seconds
        self._max_concurrency = max(1, max_concurrency)
        self._stale_running_job_seconds = stale_running_job_seconds
        self._on_job_completed = on_job_completed
        self._thread: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._active_count = 0
        self._processed_count = 0
        self._error_count = 0
        self._recovered_stale_job_count = 0
        self._last_error: str | None = None

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return False
        self._recover_stale_running_jobs()
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
        self._recover_stale_running_jobs()
        await self._run_one()

    async def _run_one(self) -> None:
        self._active_count += 1
        try:
            result = await self._service.run_next_job()
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            return
        finally:
            self._active_count -= 1
        if result is None:
            return
        self._processed_count += 1
        if result.status == "completed" and self._on_job_completed is not None:
            try:
                hook_result = self._on_job_completed(result)
                if inspect.isawaitable(hook_result):
                    await hook_result
            except Exception as exc:
                self._error_count += 1
                self._last_error = str(exc)

    def status(self) -> AsyncJobWorkerStatus:
        return AsyncJobWorkerStatus(
            running=self._thread is not None and self._thread.is_alive(),
            max_concurrency=self._max_concurrency,
            active_count=self._active_count,
            processed_count=self._processed_count,
            error_count=self._error_count,
            recovered_stale_job_count=self._recovered_stale_job_count,
            last_error=self._last_error,
            completion_hook_enabled=self._on_job_completed is not None,
        )

    def _recover_stale_running_jobs(self) -> None:
        if self._stale_running_job_seconds is None:
            return
        try:
            recovered_job_ids = self._service.recover_stale_running_jobs(
                stale_after_seconds=self._stale_running_job_seconds,
            )
        except Exception as exc:
            self._error_count += 1
            self._last_error = str(exc)
            return
        self._recovered_stale_job_count += len(recovered_job_ids)

    def _run_in_thread(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        active_tasks: set[asyncio.Task[None]] = set()
        while not self._stop_requested.is_set():
            while len(active_tasks) < self._max_concurrency and not self._stop_requested.is_set():
                task = asyncio.create_task(self._run_one())
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)
            if active_tasks:
                await asyncio.wait(
                    active_tasks,
                    timeout=self._idle_sleep_seconds,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            await asyncio.sleep(self._idle_sleep_seconds)
        if active_tasks:
            await asyncio.gather(*active_tasks, return_exceptions=True)
