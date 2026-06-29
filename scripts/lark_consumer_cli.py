from __future__ import annotations

import argparse
import os
import sys
import subprocess
import threading

try:
    from scripts.lark_consumer_utils import resolve_executable
except ModuleNotFoundError:
    from lark_consumer_utils import resolve_executable


EVENT_KEY = "im.message.receive_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume Lark bot long-connection events."
    )
    parser.add_argument("--base-url", default="", help="Debug Agent backend base URL.")
    parser.add_argument("--event-key", default=EVENT_KEY)
    parser.add_argument(
        "--transport",
        choices=("lark-cli", "sdk"),
        default=os.environ.get("LARK_EVENT_TRANSPORT", "lark-cli"),
        help="Long-connection transport. sdk consumes both IM messages and card actions.",
    )
    parser.add_argument(
        "--profile", default="", help="lark-cli profile, defaults to LARK_CLI_PROFILE."
    )
    parser.add_argument(
        "--identity",
        default="",
        help="lark-cli identity, defaults to LARK_CLI_IDENTITY.",
    )
    parser.add_argument("--lark-cli", default="lark-cli")
    parser.add_argument("--max-events", type=int, default=0)
    parser.add_argument("--timeout", default="")
    parser.add_argument("--ready-timeout-seconds", type=int, default=30)
    parser.add_argument("--completion-poll-seconds", type=float, default=10)
    parser.add_argument("--no-send-replies", action="store_true")
    parser.add_argument(
        "--seen-events-path",
        default=os.environ.get("LARK_BOT_CONSUMER_SEEN_EVENTS_PATH", ""),
        help=(
            "Path for persistent message/card dedup state. "
            "Defaults to .tmp/lark-bot-consumer-seen-events.jsonl; use 'off' to disable."
        ),
    )
    parser.add_argument(
        "--app-id", default="", help="Feishu/Lark app id for SDK transport."
    )
    parser.add_argument(
        "--app-secret", default="", help="Feishu/Lark app secret for SDK transport."
    )
    parser.add_argument(
        "--verification-token",
        default="",
        help="Optional Verification Token for SDK event dispatcher.",
    )
    parser.add_argument(
        "--encrypt-key",
        default="",
        help="Optional Encrypt Key for SDK event dispatcher.",
    )
    return parser.parse_args()


def build_consume_command(
    *, args: argparse.Namespace, profile: str, identity: str
) -> list[str]:
    command = [resolve_executable(args.lark_cli)]
    if profile:
        command.extend(["--profile", profile])
    command.extend(["event", "consume", args.event_key, "--as", identity or "bot"])
    if args.max_events:
        command.extend(["--max-events", str(args.max_events)])
    if args.timeout:
        command.extend(["--timeout", args.timeout])
    return command


def stream_stderr(
    process: subprocess.Popen[str], ready: threading.Event, event_key: str
) -> None:
    assert process.stderr is not None
    ready_marker = f"[event] ready event_key={event_key}"
    for line in process.stderr:
        print(line.rstrip(), file=sys.stderr, flush=True)
        if ready_marker in line:
            ready.set()
