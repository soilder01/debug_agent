from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from debug_agent.cases.models import DebugCase
from debug_agent.experiments.planner import ExperimentStep
from debug_agent.models.adapters import ModelAdapter
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.models.credentials import get_model_credential
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.orchestration.taxonomy import (
    AgentRoleId,
    agent_role_definition,
    logical_agent_roles,
    role_for_experiment_step,
)
from debug_agent.settings import ArkSettings


AgentModelRole = AgentRoleId


class AgentModelSelection(BaseModel):
    provider: str = "ark"
    model_id: str = ""
    base_url: str = ""
    credential_ref: str = ""
    mode: str = ""
    thinking: Literal["enabled", "disabled"] = "disabled"
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, ge=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1, le=32768)
    locked: bool = False


class AgentModelConfig(BaseModel):
    roles: dict[str, AgentModelSelection] = Field(default_factory=dict)


class ModelCatalogOption(BaseModel):
    provider: str
    model_id: str
    label: str
    description: str
    modes: list[str] = Field(default_factory=list)
    supports_thinking: bool = True
    supports_vision: bool = False
    supports_video: bool = False
    locked_for_roles: list[str] = Field(default_factory=list)
    default_parameters: dict[str, object] = Field(default_factory=dict)
    source: str = "local"


class AgentModelRuntimeConfig(BaseModel):
    default_config: AgentModelConfig
    catalog: list[ModelCatalogOption]


def default_agent_model_config(ark_settings: ArkSettings | None = None) -> AgentModelConfig:
    resolved = ark_settings or ArkSettings.from_env()
    source_selection = AgentModelSelection(
        provider="ark",
        model_id=resolved.video_model_id,
        mode=resolved.video_mode,
        thinking="disabled" if resolved.video_disable_thinking else "enabled",
        locked=True,
    )
    pro_selection = AgentModelSelection(
        provider="ark",
        model_id=resolved.seed2_pro_model_id,
        mode="",
        thinking="enabled",
        temperature=0.2,
    )
    lite_selection = AgentModelSelection(
        provider="ark",
        model_id=resolved.seed2_lite_model_id,
        mode="",
        thinking="disabled",
        temperature=0.2,
    )
    return AgentModelConfig(
        roles={
            role.role_id: (
                source_selection
                if role.default_model_tier == "source_locked"
                else pro_selection
                if role.default_model_tier == "strong_reasoning"
                else lite_selection
            )
            for role in logical_agent_roles()
        }
    )


def default_model_catalog(ark_settings: ArkSettings | None = None) -> list[ModelCatalogOption]:
    resolved = ark_settings or ArkSettings.from_env()
    return [
        ModelCatalogOption(
            provider="ark",
            model_id=resolved.video_model_id,
            label="SeedPro 2.0 high no-thinking",
            description="公平复测和原始多模态样本重跑使用的固定模型配置。",
            modes=["high"],
            supports_thinking=True,
            supports_vision=True,
            supports_video=True,
            locked_for_roles=["model_runner"],
            default_parameters={"mode": resolved.video_mode, "thinking": "disabled"},
        ),
        ModelCatalogOption(
            provider="ark",
            model_id=resolved.seed2_pro_model_id,
            label="Seed2 Pro",
            description="适合深挖策略、归因、报告和严格推理。",
            supports_thinking=True,
            default_parameters={"thinking": "enabled", "temperature": 0.2},
        ),
        ModelCatalogOption(
            provider="ark",
            model_id=resolved.seed2_lite_model_id,
            label="Seed2 Lite",
            description="适合低成本的整理、写回和轻量辅助任务。",
            supports_thinking=True,
            default_parameters={"thinking": "disabled", "temperature": 0.2},
        ),
    ]


def sanitize_agent_model_config(config: AgentModelConfig | None, ark_settings: ArkSettings | None = None) -> AgentModelConfig:
    default_config = default_agent_model_config(ark_settings)
    if config is None:
        return default_config
    merged = dict(default_config.roles)
    for role_id, selection in config.roles.items():
        role = agent_role_definition(role_id)
        if role is not None and role.locked:
            continue
        merged[role_id] = selection
    for role in logical_agent_roles():
        if role.locked:
            merged[role.role_id] = default_config.roles[role.role_id]
    return AgentModelConfig(roles=merged)


def downgrade_meta_agent_config(config: AgentModelConfig, reason: str) -> AgentModelConfig:
    lightweight = config.roles.get("writeback_operator") or config.roles.get("case_intake")
    if lightweight is None:
        return config
    downgraded = dict(config.roles)
    for role in logical_agent_roles():
        if role.locked or role.default_model_tier != "strong_reasoning":
            continue
        selection = lightweight.model_copy(deep=True)
        selection.locked = False
        downgraded[role.role_id] = selection
    del reason
    return AgentModelConfig(roles=downgraded)


class StageModelRouter:
    def __init__(
        self,
        *,
        case: DebugCase,
        config: AgentModelConfig,
        ark_settings: ArkSettings | None = None,
    ) -> None:
        self._case = case
        self._config = config
        self._ark_settings = ark_settings
        self._adapters: dict[str, ModelAdapter] = {}

    def adapter_for_step(self, step: ExperimentStep) -> ModelAdapter:
        role_id = role_for_experiment_step(step.name)
        if role_id not in self._adapters:
            self._adapters[role_id] = build_adapter_for_selection(
                case=self._case,
                selection=self._config.roles.get(role_id) or self._config.roles["model_runner"],
            )
        return self._adapters[role_id]


def build_adapter_for_selection(*, case: DebugCase, selection: AgentModelSelection) -> ModelAdapter:
    if selection.provider == "fake":
        return FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])
    if selection.provider not in {"ark", "api"}:
        raise ValueError(f"Unsupported model provider: {selection.provider}")
    credential_api_key = get_model_credential(selection.credential_ref)
    try:
        ark_settings = ArkSettings.from_env()
    except RuntimeError:
        if selection.provider != "api" or not selection.base_url:
            raise
        ark_settings = ArkSettings(api_key=SecretStr(credential_api_key or ""))
    if selection.base_url:
        ark_settings = ark_settings.model_copy(update={"base_url": selection.base_url})
    if credential_api_key is not None:
        ark_settings = ark_settings.model_copy(update={"api_key": SecretStr(credential_api_key)})
    return ArkModelAdapter(
        settings=ark_settings,
        model_id=selection.model_id,
        mode=selection.mode,
        disable_thinking=selection.thinking == "disabled",
        temperature=selection.temperature,
        top_p=selection.top_p,
        max_tokens=selection.max_tokens,
    )


def build_stage_model_router(
    *,
    case: DebugCase,
    config: AgentModelConfig | None,
) -> Callable[[ExperimentStep], ModelAdapter]:
    sanitized = sanitize_agent_model_config(config)
    router = StageModelRouter(case=case, config=sanitized)
    return router.adapter_for_step
