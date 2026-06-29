from __future__ import annotations

import json
from collections.abc import Callable
from urllib import request as urllib_request

from fastapi import APIRouter
from pydantic import SecretStr

from debug_agent.api.schemas import (
    AgentModelConnectionTestRequest,
    AgentModelConnectionTestResponse,
    ModelCatalogResponse,
)
from debug_agent.models.config import (
    AgentModelRuntimeConfig,
    ModelCatalogOption,
    default_agent_model_config,
    default_model_catalog,
)
from debug_agent.models.credentials import register_model_credential
from debug_agent.orchestration.taxonomy import debug_stage_definitions, logical_agent_roles
from debug_agent.settings import ArkSettings


def build_model_router(
    *,
    fetch_compatible_model_ids: Callable[..., list[str]] | None = None,
) -> APIRouter:
    router = APIRouter()
    router.get("/agent-models", response_model=ModelCatalogResponse)(get_agent_model_catalog)

    @router.post("/agent-models/test", response_model=AgentModelConnectionTestResponse)
    def test_agent_model_connection_route(
        request: AgentModelConnectionTestRequest,
    ) -> AgentModelConnectionTestResponse:
        return test_agent_model_connection(
            request,
            fetch_compatible_model_ids=fetch_compatible_model_ids or _fetch_compatible_model_ids,
        )

    return router


def get_agent_model_catalog(live: bool = False) -> ModelCatalogResponse:
    try:
        ark_settings = ArkSettings.from_env()
    except RuntimeError:
        ark_settings = ArkSettings(api_key=SecretStr(""))
    live_models: list[ModelCatalogOption] = []
    live_probe_error = ""
    if live:
        try:
            live_models = _fetch_live_ark_model_options(ark_settings)
        except Exception as exc:
            live_probe_error = str(exc)
    return ModelCatalogResponse(
        runtime=AgentModelRuntimeConfig(
            default_config=default_agent_model_config(ark_settings),
            catalog=default_model_catalog(ark_settings),
        ),
        agent_roles=[role.model_dump(mode="json") for role in logical_agent_roles()],
        debug_stages=[stage.model_dump(mode="json") for stage in debug_stage_definitions()],
        live_models=live_models,
        live_model_count=len(live_models),
        live_probe_error=live_probe_error,
    )


def test_agent_model_connection(
    request: AgentModelConnectionTestRequest,
    *,
    fetch_compatible_model_ids: Callable[..., list[str]] | None = None,
) -> AgentModelConnectionTestResponse:
    try:
        resolved_fetch = fetch_compatible_model_ids or _fetch_compatible_model_ids
        model_ids = resolved_fetch(
            base_url=request.base_url,
            api_key=request.api_key,
        )
    except Exception as exc:
        return AgentModelConnectionTestResponse(ok=False, message=str(exc))
    model_found = request.model_id in model_ids if request.model_id else False
    if request.model_id and not model_found:
        return AgentModelConnectionTestResponse(
            ok=False,
            message=f"连接成功，但未在 /models 中找到模型：{request.model_id}",
            model_count=len(model_ids),
            model_found=False,
        )
    credential_ref = register_model_credential(request.api_key)
    return AgentModelConnectionTestResponse(
        ok=True,
        message="连接成功；API key 已保存为当前后端会话凭据引用，不会明文写入任务配置或持久库。",
        model_count=len(model_ids),
        model_found=model_found,
        credential_ref=credential_ref,
    )


def _fetch_live_ark_model_options(ark_settings: ArkSettings) -> list[ModelCatalogOption]:
    request = urllib_request.Request(
        f"{ark_settings.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {ark_settings.api_key.get_secret_value()}"},
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=30) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    rows = decoded.get("data") if isinstance(decoded, dict) else []
    if not isinstance(rows, list):
        return []
    options: list[ModelCatalogOption] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if not isinstance(model_id, str) or not model_id:
            continue
        status = row.get("status")
        if status == "Shutdown":
            continue
        raw_modalities = row.get("modalities")
        modalities = raw_modalities if isinstance(raw_modalities, dict) else {}
        raw_input_modalities = modalities.get("input_modalities")
        input_modalities = (
            [item for item in raw_input_modalities if isinstance(item, str)]
            if isinstance(raw_input_modalities, list)
            else []
        )
        options.append(
            ModelCatalogOption(
                provider="ark",
                model_id=model_id,
                label=str(row.get("name") or model_id),
                description=str(row.get("version") or row.get("domain") or "Ark live model"),
                modes=[],
                supports_thinking="reasoning" in model_id.lower() or "seed" in model_id.lower(),
                supports_vision="image" in input_modalities,
                supports_video="video" in input_modalities or "video" in model_id.lower(),
                source="ark-live",
            )
        )
    return options


def _fetch_compatible_model_ids(*, base_url: str, api_key: str) -> list[str]:
    normalized_base_url = base_url.strip().rstrip("/")
    if not normalized_base_url:
        raise ValueError("base_url is required")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    request = urllib_request.Request(
        f"{normalized_base_url}/models",
        headers=headers,
        method="GET",
    )
    with urllib_request.urlopen(request, timeout=30) as response:
        decoded = json.loads(response.read().decode("utf-8"))
    rows = decoded.get("data") if isinstance(decoded, dict) else []
    if not isinstance(rows, list):
        raise ValueError("model list response must contain a data array")
    model_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        model_id = row.get("id")
        if isinstance(model_id, str) and model_id:
            model_ids.append(model_id)
    return model_ids
