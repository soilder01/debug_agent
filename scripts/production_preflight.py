from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EndpointResult = dict[str, Any]

ENDPOINTS: list[tuple[str, str]] = [
    ("health", "/health"),
    ("readiness", "/api/operations/readiness"),
    ("artifact_retention", "/api/operations/artifact-retention"),
    ("pilot_gate", "/api/operations/pilot-gate"),
]


def endpoint_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def fetch_json(base_url: str, path: str, *, timeout_seconds: float) -> EndpointResult:
    url = endpoint_url(base_url, path)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
            return {
                "ok": True,
                "status_code": response.status,
                "url": url,
                "payload": json.loads(body) if body else {},
                "error": "",
            }
    except HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "url": url,
            "payload": {},
            "error": exc.read().decode("utf-8", errors="replace"),
        }
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "status_code": 0,
            "url": url,
            "payload": {},
            "error": str(exc),
        }


def run_preflight(base_url: str, *, timeout_seconds: float) -> dict[str, Any]:
    endpoints = {
        name: fetch_json(base_url, path, timeout_seconds=timeout_seconds)
        for name, path in ENDPOINTS
    }
    return build_preflight_report(base_url=base_url, endpoints=endpoints)


def build_preflight_report(*, base_url: str, endpoints: dict[str, EndpointResult]) -> dict[str, Any]:
    checks = [
        _health_check(endpoints.get("health", {})),
        _readiness_check(endpoints.get("readiness", {})),
        _artifact_retention_check(endpoints.get("artifact_retention", {})),
        _pilot_gate_check(endpoints.get("pilot_gate", {})),
    ]
    status = _overall_status(checks)
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_url": base_url.rstrip("/"),
        "status": status,
        "checks": checks,
        "endpoints": endpoints,
        "next_actions": _next_actions(checks),
    }


def _health_check(result: EndpointResult) -> dict[str, str]:
    payload = _payload(result)
    passed = bool(result.get("ok")) and payload.get("status") == "ok"
    return _check(
        key="health",
        label="Backend health",
        status="passed" if passed else "failed",
        detail=f"status_code={result.get('status_code', 0)}, service={payload.get('service', '')}",
        action="Start the backend service and confirm /health returns status=ok.",
    )


def _readiness_check(result: EndpointResult) -> dict[str, str]:
    payload = _payload(result)
    level = str(payload.get("level", "unknown"))
    if not result.get("ok") or level == "critical":
        status = "failed"
    elif level == "degraded":
        status = "warning"
    else:
        status = "passed"
    return _check(
        key="readiness",
        label="Production readiness",
        status=status,
        detail=f"level={level}",
        action="Resolve critical and warning readiness checks before production-candidate traffic.",
    )


def _artifact_retention_check(result: EndpointResult) -> dict[str, str]:
    payload = _payload(result)
    if not result.get("ok"):
        status = "failed"
    elif int(payload.get("eligible_file_count", 0) or 0) > 0:
        status = "warning"
    else:
        status = "passed"
    return _check(
        key="artifact_retention",
        label="Artifact retention",
        status=status,
        detail=(
            f"eligible_file_count={payload.get('eligible_file_count', 0)}, "
            f"eligible_size_bytes={payload.get('eligible_size_bytes', 0)}"
        ),
        action="Review retention dry run and execute confirmed cleanup if artifact growth is expected.",
    )


def _pilot_gate_check(result: EndpointResult) -> dict[str, str]:
    payload = _payload(result)
    gate_status = str(payload.get("status", "unknown"))
    if not result.get("ok") or gate_status == "failed":
        status = "failed"
    elif gate_status == "warning":
        status = "warning"
    else:
        status = "passed"
    evidence = payload.get("batch_evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
    return _check(
        key="pilot_gate",
        label="Pilot gate",
        status=status,
        detail=(
            f"status={gate_status}, completed_jobs={evidence.get('completed_jobs', 0)}, "
            f"best_batch_id={evidence.get('best_batch_id', '')}"
        ),
        action="Resolve failed pilot gate checks before pilot rollout.",
    )


def _payload(result: EndpointResult) -> dict[str, Any]:
    payload = result.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def _check(*, key: str, label: str, status: str, detail: str, action: str) -> dict[str, str]:
    return {
        "key": key,
        "label": label,
        "status": status,
        "detail": detail,
        "action": "No action required." if status == "passed" else action,
    }


def _overall_status(checks: list[dict[str, str]]) -> str:
    if any(check["status"] == "failed" for check in checks):
        return "failed"
    if any(check["status"] == "warning" for check in checks):
        return "warning"
    return "passed"


def _next_actions(checks: list[dict[str, str]]) -> list[str]:
    return [check["action"] for check in checks if check["status"] != "passed"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Debug Agent production preflight checks.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--allow-warning", action="store_true")
    args = parser.parse_args(argv)

    report = run_preflight(args.base_url, timeout_seconds=args.timeout_seconds)
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"status": report["status"], "next_actions": report["next_actions"]}, ensure_ascii=False, indent=2))
    if report["status"] == "failed":
        return 1
    if report["status"] == "warning" and not args.allow_warning:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
