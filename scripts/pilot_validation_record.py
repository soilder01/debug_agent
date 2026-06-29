from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FetchResult = dict[str, Any]


def endpoint_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def fetch_bytes(base_url: str, path: str, *, timeout_seconds: float) -> FetchResult:
    url = endpoint_url(base_url, path)
    request = Request(url, headers={"Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return {
                "ok": True,
                "status_code": response.status,
                "url": url,
                "content": response.read(),
                "error": "",
            }
    except HTTPError as exc:
        return {
            "ok": False,
            "status_code": exc.code,
            "url": url,
            "content": b"",
            "error": exc.read().decode("utf-8", errors="replace"),
        }
    except (OSError, URLError) as exc:
        return {
            "ok": False,
            "status_code": 0,
            "url": url,
            "content": b"",
            "error": str(exc),
        }


def fetch_json(base_url: str, path: str, *, timeout_seconds: float) -> tuple[FetchResult, dict[str, Any]]:
    result = fetch_bytes(base_url, path, timeout_seconds=timeout_seconds)
    if not result["ok"]:
        return result, {}
    try:
        payload = json.loads(bytes(result["content"]).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        result["ok"] = False
        result["error"] = str(exc)
        return result, {}
    return result, payload if isinstance(payload, dict) else {}


def collect_validation_record(
    *,
    base_url: str,
    output_dir: Path,
    batch_ids: list[str],
    operator: str,
    environment: str,
    timeout_seconds: float,
    include_support_bundle: bool,
    include_database_backup: bool,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloads: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}

    for name, path in [
        ("readiness", "/api/operations/readiness"),
        ("pilot_gate", "/api/operations/pilot-gate"),
        ("artifact_retention", "/api/operations/artifact-retention"),
        ("batch_comparison", _batch_comparison_path(batch_ids, csv=False)),
    ]:
        result, payload = fetch_json(base_url, path, timeout_seconds=timeout_seconds)
        file_path = output_dir / f"{name}.json"
        file_path.write_text(
            json.dumps(payload if payload else _serializable_result(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        downloads[name] = _download_record(result=result, file_path=file_path)
        payloads[name] = payload

    csv_result = fetch_bytes(base_url, _batch_comparison_path(batch_ids, csv=True), timeout_seconds=timeout_seconds)
    csv_path = output_dir / "batch_comparison.csv"
    csv_path.write_bytes(bytes(csv_result["content"]))
    downloads["batch_comparison_csv"] = _download_record(result=csv_result, file_path=csv_path)

    if include_support_bundle:
        bundle_result = fetch_bytes(base_url, "/api/operations/support-bundle.zip", timeout_seconds=timeout_seconds)
        bundle_path = output_dir / "operations_support_bundle.zip"
        bundle_path.write_bytes(bytes(bundle_result["content"]))
        downloads["operations_support_bundle"] = _download_record(result=bundle_result, file_path=bundle_path)

    if include_database_backup:
        backup_result = fetch_bytes(base_url, "/api/operations/database-backup.zip", timeout_seconds=timeout_seconds)
        backup_path = output_dir / "database_backup.zip"
        backup_path.write_bytes(bytes(backup_result["content"]))
        downloads["database_backup"] = _download_record(result=backup_result, file_path=backup_path)

    record = build_record(
        base_url=base_url,
        output_dir=output_dir,
        operator=operator,
        environment=environment,
        batch_ids=batch_ids,
        payloads=payloads,
        downloads=downloads,
    )
    record_path = output_dir / "pilot-validation-record.md"
    record_path.write_text(record["markdown"], encoding="utf-8")
    summary_path = output_dir / "pilot-validation-summary.json"
    summary_path.write_text(json.dumps(record["summary"], ensure_ascii=False, indent=2), encoding="utf-8")
    record["record_path"] = str(record_path)
    record["summary_path"] = str(summary_path)
    return record


def build_record(
    *,
    base_url: str,
    output_dir: Path,
    operator: str,
    environment: str,
    batch_ids: list[str],
    payloads: dict[str, dict[str, Any]],
    downloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    readiness = payloads.get("readiness", {})
    pilot_gate = payloads.get("pilot_gate", {})
    artifact_retention = payloads.get("artifact_retention", {})
    comparison = payloads.get("batch_comparison", {})
    gate_evidence = _dict_value(pilot_gate, "batch_evidence")
    thresholds = _dict_value(pilot_gate, "thresholds")
    best_item = _best_comparison_item(comparison)
    status = str(pilot_gate.get("status") or _download_status(downloads))
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    compared_ids = batch_ids or [str(item) for item in comparison.get("batch_ids", []) if item]
    summary = {
        "generated_at": generated_at,
        "status": status,
        "base_url": base_url.rstrip("/"),
        "operator": operator,
        "environment": environment,
        "batch_ids": compared_ids,
        "readiness_level": readiness.get("level", "unknown"),
        "completed_jobs": gate_evidence.get("completed_jobs", 0),
        "best_batch_id": gate_evidence.get("best_batch_id", ""),
        "best_success_rate": gate_evidence.get("best_success_rate", 0),
        "best_p95_duration_ms": gate_evidence.get("best_p95_duration_ms", 0),
        "best_estimated_cost_units": gate_evidence.get("best_estimated_cost_units", 0),
        "artifact_retention_candidates": artifact_retention.get("eligible_file_count", 0),
        "downloads": downloads,
    }
    markdown = validation_markdown(
        summary=summary,
        thresholds=thresholds,
        best_item=best_item,
        output_dir=output_dir,
    )
    return {"summary": summary, "markdown": markdown}


def validation_markdown(
    *,
    summary: dict[str, Any],
    thresholds: dict[str, Any],
    best_item: dict[str, Any],
    output_dir: Path,
) -> str:
    downloads = summary["downloads"]
    return "\n".join(
        [
            "# Debug Agent Pilot Validation Record",
            "",
            "## Run Metadata",
            "",
            f"- Date: {summary['generated_at']}",
            f"- Operator: {summary['operator']}",
            f"- Environment: {summary['environment']}",
            f"- Backend URL: {summary['base_url']}",
            f"- Batch IDs compared: {', '.join(summary['batch_ids']) or 'latest batches'}",
            f"- Model configuration summary: {best_item.get('model_profile', 'not available')}",
            f"- `model_runner` locked: {'yes' if best_item.get('model_runner_locked') is True else 'unknown'}",
            "",
            "## Required Evidence",
            "",
            f"- Production readiness JSON: {_file_ref(downloads, 'readiness')}",
            f"- Pilot gate JSON: {_file_ref(downloads, 'pilot_gate')}",
            f"- Batch comparison CSV: {_file_ref(downloads, 'batch_comparison_csv')}",
            f"- Operations support bundle: {_file_ref(downloads, 'operations_support_bundle')}",
            f"- Database backup location: {_file_ref(downloads, 'database_backup')}",
            f"- Artifact retention dry-run output: {_file_ref(downloads, 'artifact_retention')}",
            f"- Output directory: {output_dir}",
            "",
            "## Gate Thresholds",
            "",
            f"- Minimum completed samples: {thresholds.get('min_completed_jobs', '')}",
            f"- Minimum success rate: {thresholds.get('min_success_rate', '')}",
            f"- Maximum P95 latency: {thresholds.get('max_p95_duration_ms', '')}",
            f"- Maximum estimated cost units: {thresholds.get('max_estimated_cost_units', '')}",
            f"- Maximum model call errors: {thresholds.get('max_model_call_errors', '')}",
            f"- Maximum writeback failures: {thresholds.get('max_writeback_failed', '')}",
            f"- Maximum Lark operation failures: {thresholds.get('max_lark_operation_failures', '')}",
            "",
            "## Results",
            "",
            f"- Gate status: {summary['status']}",
            f"- Production readiness: {summary['readiness_level']}",
            f"- Completed samples: {summary['completed_jobs']}",
            f"- Best batch: {summary['best_batch_id']}",
            f"- Best batch success rate: {summary['best_success_rate']}",
            f"- Best batch P95 latency: {summary['best_p95_duration_ms']}",
            f"- Best batch estimated cost: {summary['best_estimated_cost_units']}",
            f"- Artifact retention candidates: {summary['artifact_retention_candidates']}",
            "",
            "## Decision",
            "",
            "- Decision: pass / conditional pass / fail",
            "- Rationale:",
            "- Required follow-up:",
            "- Approver:",
            "- Approval time:",
            "",
            "## Notes",
            "",
            "- Do not approve pilot rollout from a single small successful batch.",
            "- Do not compare meta agent configurations unless `model_runner` remains locked for source replay, baseline, targeted, and verification stages.",
            "- Store database backups only in approved secure storage; the operations support bundle is redacted, but database backups are not.",
            "",
        ]
    )


def _batch_comparison_path(batch_ids: list[str], *, csv: bool) -> str:
    base_path = "/api/debug-batches/comparison.csv" if csv else "/api/debug-batches/comparison"
    if not batch_ids:
        return base_path
    return f"{base_path}?{urlencode({'batch_ids': ','.join(batch_ids)})}"


def _download_record(*, result: FetchResult, file_path: Path) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "status_code": result.get("status_code", 0),
        "url": result.get("url", ""),
        "file": str(file_path),
        "error": result.get("error", ""),
    }


def _serializable_result(result: FetchResult) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "status_code": result.get("status_code", 0),
        "url": result.get("url", ""),
        "content_length": len(bytes(result.get("content", b""))),
        "error": result.get("error", ""),
    }


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def _best_comparison_item(comparison: dict[str, Any]) -> dict[str, Any]:
    best_batch_id = str(comparison.get("best_batch_id", ""))
    items = comparison.get("items", [])
    if not isinstance(items, list):
        return {}
    for item in items:
        if isinstance(item, dict) and item.get("batch_id") == best_batch_id:
            return item
    first = items[0] if items else {}
    return first if isinstance(first, dict) else {}


def _download_status(downloads: dict[str, dict[str, Any]]) -> str:
    return "failed" if any(not item.get("ok") for item in downloads.values()) else "passed"


def _file_ref(downloads: dict[str, dict[str, Any]], key: str) -> str:
    item = downloads.get(key)
    if item is None:
        return "not downloaded"
    if not item.get("ok"):
        return f"{item.get('file', '')} (failed: {item.get('error', '')})"
    return str(item.get("file", ""))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Debug Agent pilot validation evidence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output-dir", default="dogfood-output/pilot-validation")
    parser.add_argument("--batch-ids", default="", help="Comma-separated batch ids to compare.")
    parser.add_argument("--operator", default="")
    parser.add_argument("--environment", default="production-candidate")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--include-support-bundle", action="store_true")
    parser.add_argument("--include-database-backup", action="store_true")
    parser.add_argument("--allow-warning", action="store_true")
    args = parser.parse_args(argv)

    record = collect_validation_record(
        base_url=args.base_url,
        output_dir=Path(args.output_dir),
        batch_ids=[item.strip() for item in args.batch_ids.split(",") if item.strip()],
        operator=args.operator,
        environment=args.environment,
        timeout_seconds=args.timeout_seconds,
        include_support_bundle=args.include_support_bundle,
        include_database_backup=args.include_database_backup,
    )
    status = str(record["summary"]["status"])
    print(json.dumps({"status": status, "record_path": record["record_path"]}, ensure_ascii=False, indent=2))
    if status == "failed":
        return 1
    if status == "warning" and not args.allow_warning:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
