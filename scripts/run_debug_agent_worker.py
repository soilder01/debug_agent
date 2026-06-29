from __future__ import annotations

import asyncio
import signal
import sys

from debug_agent.api.routes import job_worker


async def main() -> int:
    stop_event = asyncio.Event()

    def request_stop() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, signame, None)
        if signum is None:
            continue
        try:
            loop.add_signal_handler(signum, request_stop)
        except NotImplementedError:
            signal.signal(signum, lambda _signum, _frame: request_stop())

    started = job_worker.start()
    print(
        f"[worker] debug job worker {'started' if started else 'already running'}",
        file=sys.stderr,
        flush=True,
    )
    await stop_event.wait()
    await job_worker.stop()
    print("[worker] debug job worker stopped", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
