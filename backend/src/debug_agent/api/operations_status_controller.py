from __future__ import annotations

import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from debug_agent.api.debug_batch_routes import DebugBatchViewBuilder, best_batch_comparison_item
from debug_agent.api.operations_routes import (
    PilotGateCheck,
    PilotGateResponse,
    PilotGateThresholds,
    ProductionReadinessCheck,
    ProductionReadinessResponse,
    RuntimeConfigSummary,
    RuntimePathStatus,
)
from debug_agent.api.schemas import DebugBatchComparisonResponse, DebugBatchProgressResponse
from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.settings import DebugAgentSettings, LarkSpreadsheetSettings
from debug_agent.storage.repository import DebugJobRepository


LarkBotEventMode = Literal["webhook", "long_connection"]


class OperationsStatusController:
    def __init__(
        self,
        *,
        settings: Callable[[], DebugAgentSettings],
        spreadsheet_settings: Callable[[], LarkSpreadsheetSettings],
        writeback_client_configured: Callable[[], bool],
        job_repository: DebugJobRepository,
        debug_batch_view_builder: DebugBatchViewBuilder,
        worker_status: Callable[[], object],
        connector_status: Callable[[], LarkConnectorStatus],
        database_kind: Callable[[str], str],
        database_path: Callable[[str], str],
        sqlite_database_path: Callable[[str], Path | None],
        redacted_database_url: Callable[[str], str],
        lark_event_mode: Callable[[], LarkBotEventMode],
        lark_bot_verification_token: Callable[[], str],
        lark_bot_encrypt_key: Callable[[], str],
        webhook_token_readiness_status: Callable[[], Literal["ok", "warning", "critical"]],
        encrypt_key_readiness_status: Callable[[], Literal["ok", "warning", "critical"]],
    ) -> None:
        self._settings = settings
        self._spreadsheet_settings = spreadsheet_settings
        self._writeback_client_configured = writeback_client_configured
        self._job_repository = job_repository
        self._debug_batch_view_builder = debug_batch_view_builder
        self._worker_status = worker_status
        self._connector_status = connector_status
        self._database_kind = database_kind
        self._database_path = database_path
        self._sqlite_database_path = sqlite_database_path
        self._redacted_database_url = redacted_database_url
        self._lark_event_mode = lark_event_mode
        self._lark_bot_verification_token = lark_bot_verification_token
        self._lark_bot_encrypt_key = lark_bot_encrypt_key
        self._webhook_token_readiness_status = webhook_token_readiness_status
        self._encrypt_key_readiness_status = encrypt_key_readiness_status

    def get_readiness(self) -> ProductionReadinessResponse:
        settings = self._settings()
        worker_status = self._worker_status()
        connector_status = self._connector_status()
        paths = self.runtime_paths()
        checks = self.production_readiness_checks(
            paths=paths, worker_status=worker_status, connector_status=connector_status
        )
        return ProductionReadinessResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            level=production_readiness_level(checks),
            config=RuntimeConfigSummary(
                environment=settings.environment,
                database_url=self._redacted_database_url(settings.database_url),
                database_kind=self._database_kind(settings.database_url),
                database_path=self._database_path(settings.database_url),
                artifact_root=str(settings.image_artifact_dir),
                artifact_retention_days=settings.artifact_retention_days,
                report_base_url=settings.report_base_url,
                auto_writeback_enabled=settings.auto_writeback_enabled,
                queue_max_concurrency=settings.queue_max_concurrency,
                retry_max_attempts=settings.retry_max_attempts,
                stale_running_job_seconds=settings.stale_running_job_seconds,
                require_trusted_actor=settings.require_trusted_actor,
                enable_fixture_fallback=settings.enable_fixture_fallback,
                usage_budget_units=settings.usage_budget_units,
                enforce_usage_budget=settings.enforce_usage_budget,
                lark_configured=self._spreadsheet_settings().reference is not None,
                lark_connector_mode=connector_status.mode,
                lark_identity=connector_status.identity,
                lark_profile=connector_status.profile,
                lark_event_mode=self._lark_event_mode(),
                lark_bot_verification_configured=bool(self._lark_bot_verification_token()),
                lark_bot_encrypt_configured=bool(self._lark_bot_encrypt_key()),
                worker_running=worker_status.running,
                worker_completion_hook_enabled=worker_status.completion_hook_enabled,
            ),
            paths=paths,
            checks=checks,
            export_urls={
                "observability": "/api/observability/summary",
                "performance": "/api/performance/summary",
                "debug_jobs": "/api/exports/debug-jobs.zip",
                "readiness": "/api/operations/readiness",
                "artifact_retention": "/api/operations/artifact-retention",
                "artifact_retention_cleanup": "/api/operations/artifact-retention/cleanup",
                "database_backup": "/api/operations/database-backup.zip",
                "operations_support_bundle": "/api/operations/support-bundle.zip",
                "lark_bot_preflight": "/api/lark/bot/preflight",
                "lark_bot_go_live_gate": "/api/lark/bot/go-live-gate",
                "lark_bot_permission_checklist": "/api/lark/bot/permission-checklist",
                "lark_bot_setup_package": "/api/lark/bot/setup-package.zip",
            },
        )

    def get_pilot_gate(
        self,
        *,
        limit: int = 5,
        min_completed_jobs: int = 20,
        min_success_rate: float = 0.8,
        max_p95_duration_ms: int = 12_000,
        max_estimated_cost_units: float | None = None,
        max_model_call_errors: int = 0,
        max_writeback_failed: int = 0,
        max_lark_operation_failures: int = 0,
    ) -> PilotGateResponse:
        settings = self._settings()
        resolved_max_cost = (
            max_estimated_cost_units
            if max_estimated_cost_units is not None
            else settings.usage_budget_units
            if settings.usage_budget_units > 0
            else 100.0
        )
        thresholds = PilotGateThresholds(
            min_completed_jobs=min_completed_jobs,
            min_success_rate=min_success_rate,
            max_p95_duration_ms=max_p95_duration_ms,
            max_estimated_cost_units=resolved_max_cost,
            max_model_call_errors=max_model_call_errors,
            max_writeback_failed=max_writeback_failed,
            max_lark_operation_failures=max_lark_operation_failures,
        )
        comparison = self._debug_batch_view_builder.build_comparison_response(
            batch_ids=None, limit=limit
        )
        compared_batches = [
            self._debug_batch_view_builder.build_progress(batch_id)
            for batch_id in comparison.batch_ids
        ]
        readiness = self.get_readiness()
        lark_operation_failures = self._job_repository.count_lark_operation_audits(
            status="failed"
        )
        checks = pilot_gate_checks(
            thresholds=thresholds,
            comparison=comparison,
            compared_batches=compared_batches,
            readiness=readiness,
            lark_operation_failures=lark_operation_failures,
        )
        return PilotGateResponse(
            generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
            status=pilot_gate_status(checks),
            thresholds=thresholds,
            batch_evidence=self._debug_batch_view_builder.build_pilot_gate_batch_evidence(
                compared_batches=compared_batches, comparison=comparison
            ),
            checks=checks,
            comparison=comparison,
            export_urls={
                "readiness": "/api/operations/readiness",
                "batch_comparison": "/api/debug-batches/comparison",
                "batch_comparison_csv": comparison.export_url,
                "support_bundle": "/api/operations/support-bundle.zip",
            },
        )

    def runtime_paths(self) -> list[RuntimePathStatus]:
        settings = self._settings()
        paths = [
            ("artifact_root", "产物根目录", settings.image_artifact_dir),
            ("run_artifacts", "运行产物目录", settings.image_artifact_dir / "runs"),
        ]
        database_path = self._sqlite_database_path(settings.database_url)
        if database_path is not None:
            paths.append(("database_parent", "数据库目录", database_path.parent))
        return [runtime_path_status(name=name, label=label, path=path) for name, label, path in paths]

    def production_readiness_checks(
        self,
        *,
        paths: list[RuntimePathStatus],
        worker_status: object,
        connector_status: LarkConnectorStatus,
    ) -> list[ProductionReadinessCheck]:
        settings = self._settings()
        path_checks = [
            ProductionReadinessCheck(
                key=f"path_{path.name}",
                label=path.label,
                status="ok" if path.writable else "critical",
                detail=f"{path.path} {'可写' if path.writable else '不可写或父目录不存在'}",
                action="确认运行用户对目录有读写权限。" if not path.writable else "无需处理。",
            )
            for path in paths
        ]
        checks = [
            *path_checks,
            ProductionReadinessCheck(
                key="database",
                label="数据库配置",
                status="ok" if self._database_kind(settings.database_url) == "sqlite" else "warning",
                detail=(
                    f"{self._database_kind(settings.database_url)} / "
                    f"{self._redacted_database_url(settings.database_url)}"
                ),
                action="生产候选建议配置持久化数据库，并纳入备份策略。",
            ),
            ProductionReadinessCheck(
                key="report_base_url",
                label="报告基地址",
                status="warning"
                if "localhost" in settings.report_base_url
                or "127.0.0.1" in settings.report_base_url
                else "ok",
                detail=settings.report_base_url,
                action="生产候选应配置飞书和操作者可访问的内网或公网地址。",
            ),
            ProductionReadinessCheck(
                key="worker",
                label="后台进程",
                status="ok" if worker_status.running else "warning",
                detail=(
                    f"running={worker_status.running}, "
                    f"max_concurrency={worker_status.max_concurrency}"
                ),
                action="试点运行前启动后台进程并确认队列能被消费。"
                if not worker_status.running
                else "无需处理。",
            ),
            ProductionReadinessCheck(
                key="lark_connector",
                label="Lark Connector",
                status="ok" if self._spreadsheet_settings().reference is not None else "warning",
                detail=(
                    f"{connector_status.mode}/{connector_status.identity}/"
                    f"{connector_status.profile or 'default'}"
                ),
                action="配置 LARK_SPREADSHEET_URL、LARK_CLI_PROFILE 和身份后执行连接检查。",
            ),
            ProductionReadinessCheck(
                key="lark_bot_webhook_token",
                label="飞书机器人回调 Token",
                status=self._webhook_token_readiness_status(),
                detail=(
                    f"mode={self._lark_event_mode()}; "
                    f"configured={bool(self._lark_bot_verification_token())}"
                ),
                action=(
                    "长连接模式不需要 LARK_BOT_VERIFICATION_TOKEN。"
                    if self._lark_event_mode() == "long_connection"
                    else (
                        "配置 LARK_BOT_VERIFICATION_TOKEN，并与飞书事件订阅中的 Verification Token 保持一致。"
                        if not self._lark_bot_verification_token()
                        else "无需处理。"
                    )
                ),
            ),
            ProductionReadinessCheck(
                key="lark_bot_encrypt_key",
                label="飞书机器人 Encrypt Key",
                status=self._encrypt_key_readiness_status(),
                detail=(
                    f"mode={self._lark_event_mode()}; "
                    f"configured={bool(self._lark_bot_encrypt_key())}"
                ),
                action=(
                    "长连接模式不需要 LARK_BOT_ENCRYPT_KEY。"
                    if self._lark_event_mode() == "long_connection"
                    else (
                        "配置 LARK_BOT_ENCRYPT_KEY，并与飞书事件订阅中的 Encrypt Key 保持一致，以启用签名校验和密文回调。"
                        if not self._lark_bot_encrypt_key()
                        else "无需处理。"
                    )
                ),
            ),
            ProductionReadinessCheck(
                key="auto_writeback",
                label="自动写回",
                status="critical"
                if settings.auto_writeback_enabled and not self._writeback_client_configured()
                else "ok",
                detail=(
                    f"auto_writeback_enabled={settings.auto_writeback_enabled}, "
                    f"client_configured={self._writeback_client_configured()}"
                ),
                action="开启自动写回前必须配置可用的 Lark 写回 client。",
            ),
            ProductionReadinessCheck(
                key="trusted_actor",
                label="操作者约束",
                status="ok" if settings.require_trusted_actor else "warning",
                detail=f"require_trusted_actor={settings.require_trusted_actor}",
                action="生产候选建议开启 DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR，避免匿名写操作。",
            ),
            ProductionReadinessCheck(
                key="usage_budget",
                label="预算门禁",
                status="ok"
                if settings.enforce_usage_budget and settings.usage_budget_units > 0
                else "warning",
                detail=(
                    f"budget={settings.usage_budget_units}, "
                    f"enforcement={settings.enforce_usage_budget}"
                ),
                action="生产候选建议配置 DEBUG_AGENT_USAGE_BUDGET_UNITS 并开启 DEBUG_AGENT_ENFORCE_USAGE_BUDGET。",
            ),
            ProductionReadinessCheck(
                key="artifact_retention",
                label="产物保留策略",
                status="ok" if settings.artifact_retention_days > 0 else "warning",
                detail=f"retention_days={settings.artifact_retention_days}",
                action="生产候选建议配置 DEBUG_AGENT_ARTIFACT_RETENTION_DAYS，并定期查看干跑结果。",
            ),
        ]
        return checks


def pilot_gate_checks(
    *,
    thresholds: PilotGateThresholds,
    comparison: DebugBatchComparisonResponse,
    compared_batches: list[DebugBatchProgressResponse],
    readiness: ProductionReadinessResponse,
    lark_operation_failures: int,
) -> list[PilotGateCheck]:
    best_item = best_batch_comparison_item(comparison)
    completed_jobs = sum(batch.completed_count for batch in compared_batches)
    return [
        pilot_check(
            key="production_readiness",
            label="生产运行就绪",
            passed=readiness.level != "critical",
            warning=readiness.level == "degraded",
            detail=f"readiness={readiness.level}",
            action="先处理 readiness 中的 critical 或 warning 项，再开放试点流量。",
        ),
        pilot_check(
            key="batch_comparison",
            label="批次对比覆盖",
            passed=len(comparison.items) >= 2,
            warning=len(comparison.items) == 1,
            detail=f"compared_batches={len(comparison.items)}",
            action="至少准备两个批次，用相同 model_runner 公平复测锁定对比 meta agent 配置。",
        ),
        pilot_check(
            key="scale_coverage",
            label="真实样本覆盖",
            passed=completed_jobs >= thresholds.min_completed_jobs,
            detail=f"completed_jobs={completed_jobs}, required={thresholds.min_completed_jobs}",
            action="继续执行 operator-approved 真实批次，直到完成样本数达到准入阈值。",
        ),
        pilot_check(
            key="success_rate",
            label="批次成功率",
            passed=best_item is not None and best_item.success_rate >= thresholds.min_success_rate,
            detail=(
                f"best_success_rate={best_item.success_rate if best_item is not None else 0}, "
                f"required={thresholds.min_success_rate}"
            ),
            action="优先排查失败样本、模型调用错误和证据归因失败，再重跑对照批次。",
        ),
        pilot_check(
            key="latency_p95",
            label="P95 耗时",
            passed=best_item is not None
            and best_item.p95_duration_ms <= thresholds.max_p95_duration_ms,
            detail=(
                f"best_p95_ms={best_item.p95_duration_ms if best_item is not None else 0}, "
                f"limit={thresholds.max_p95_duration_ms}"
            ),
            action="降低批次并发外的热点耗时，检查 Lark、报告生成、模型调用和 artifact 写入。",
        ),
        pilot_check(
            key="cost_budget",
            label="成本预算",
            passed=best_item is not None
            and best_item.estimated_cost_units <= thresholds.max_estimated_cost_units,
            detail=(
                f"best_cost={best_item.estimated_cost_units if best_item is not None else 0}, "
                f"limit={thresholds.max_estimated_cost_units}"
            ),
            action="对高成本 meta agent 降级或缩小 thinking 使用范围，保持 model_runner 锁定不变。",
        ),
        pilot_check(
            key="model_call_errors",
            label="模型调用错误",
            passed=best_item is not None
            and best_item.model_call_errors <= thresholds.max_model_call_errors,
            detail=(
                f"best_model_call_errors={best_item.model_call_errors if best_item is not None else 0}, "
                f"limit={thresholds.max_model_call_errors}"
            ),
            action="先修复 Ark/API 连接、credential_ref、超时和降级策略，再扩大样本量。",
        ),
        pilot_check(
            key="writeback_failures",
            label="写回失败",
            passed=best_item is not None
            and best_item.writeback_failed <= thresholds.max_writeback_failed,
            detail=(
                f"best_writeback_failed={best_item.writeback_failed if best_item is not None else 0}, "
                f"limit={thresholds.max_writeback_failed}"
            ),
            action="检查写回审计、字段映射、Lark scope 和高风险写确认状态。",
        ),
        pilot_check(
            key="lark_operation_failures",
            label="Lark 操作失败审计",
            passed=lark_operation_failures <= thresholds.max_lark_operation_failures,
            detail=(
                f"failed_lark_operations={lark_operation_failures}, "
                f"limit={thresholds.max_lark_operation_failures}"
            ),
            action="打开 Lark 操作审计，按 scope、auth、risk 分类处理失败记录。",
        ),
        pilot_check(
            key="model_runner_fairness",
            label="公平复测锁定",
            passed=bool(comparison.items)
            and all(item.model_runner_locked for item in comparison.items),
            detail=(
                f"locked_batches={sum(1 for item in comparison.items if item.model_runner_locked)}/"
                f"{len(comparison.items)}"
            ),
            action="任何对照批次都不能解锁 model_runner；baseline/targeted/verification 必须保持原始模型一致。",
        ),
    ]


def pilot_check(
    *,
    key: str,
    label: str,
    passed: bool,
    detail: str,
    action: str,
    warning: bool = False,
) -> PilotGateCheck:
    if passed and not warning:
        return PilotGateCheck(
            key=key, label=label, status="passed", detail=detail, action="无需处理。"
        )
    if passed and warning:
        return PilotGateCheck(key=key, label=label, status="warning", detail=detail, action=action)
    return PilotGateCheck(key=key, label=label, status="failed", detail=detail, action=action)


def pilot_gate_status(checks: list[PilotGateCheck]) -> Literal["passed", "warning", "failed"]:
    if any(check.status == "failed" for check in checks):
        return "failed"
    if any(check.status == "warning" for check in checks):
        return "warning"
    return "passed"


def runtime_path_status(*, name: str, label: str, path: Path) -> RuntimePathStatus:
    exists = path.exists()
    is_directory = path.is_dir()
    writable_target = path if exists else path.parent
    writable = writable_target.exists() and os.access(writable_target, os.W_OK)
    return RuntimePathStatus(
        name=name,
        label=label,
        path=str(path),
        exists=exists,
        is_directory=is_directory,
        writable=writable,
    )


def production_readiness_level(
    checks: list[ProductionReadinessCheck],
) -> Literal["healthy", "degraded", "critical"]:
    if any(check.status == "critical" for check in checks):
        return "critical"
    if any(check.status == "warning" for check in checks):
        return "degraded"
    return "healthy"
