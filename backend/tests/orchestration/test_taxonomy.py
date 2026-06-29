from debug_agent.models.config import (
    AgentModelConfig,
    AgentModelSelection,
    default_agent_model_config,
    sanitize_agent_model_config,
)
from debug_agent.orchestration.taxonomy import (
    agent_role_definition,
    debug_stage_definitions,
    is_source_replay_stage,
    role_for_experiment_step,
    roles_for_stage,
)
from debug_agent.settings import ArkSettings


def test_taxonomy_locks_source_replay_to_model_runner() -> None:
    assert is_source_replay_stage("baseline")
    assert is_source_replay_stage("targeted")
    assert is_source_replay_stage("verification")
    assert is_source_replay_stage("intervention")
    assert not is_source_replay_stage("attribution")
    assert not is_source_replay_stage("hypothesis")
    assert not is_source_replay_stage("causal_comparison")
    assert role_for_experiment_step("baseline_replay") == "model_runner"
    assert role_for_experiment_step("prompt_patch_intervention_rerun") == "model_runner"
    assert "model_runner" in roles_for_stage("baseline")
    assert "model_runner" in roles_for_stage("intervention")
    assert agent_role_definition("model_runner").locked is True  # type: ignore[union-attr]


def test_sanitize_agent_model_config_uses_taxonomy_lock() -> None:
    ark_settings = ArkSettings(
        api_key="",
        video_model_id="locked-source",
        seed2_pro_model_id="pro",
        seed2_lite_model_id="lite",
    )
    incoming = AgentModelConfig(
        roles={
            "model_runner": AgentModelSelection(
                provider="ark",
                model_id="unsafe-source",
                thinking="enabled",
            ),
            "report_root_cause": AgentModelSelection(
                provider="ark",
                model_id="custom-report",
                thinking="enabled",
            ),
        }
    )

    sanitized = sanitize_agent_model_config(incoming, ark_settings=ark_settings)

    assert sanitized.roles["model_runner"].model_id == "locked-source"
    assert sanitized.roles["model_runner"].locked is True
    assert sanitized.roles["report_root_cause"].model_id == "custom-report"


def test_case_intake_defaults_to_seedpro() -> None:
    ark_settings = ArkSettings(
        api_key="",
        video_model_id="locked-source",
        seed2_pro_model_id="seedpro",
        seed2_lite_model_id="lite",
    )

    config = default_agent_model_config(ark_settings)

    assert config.roles["case_intake"].model_id == "seedpro"
    assert config.roles["case_intake"].thinking == "enabled"


def test_hypothesis_closure_agents_default_to_seedpro_strong_reasoning() -> None:
    ark_settings = ArkSettings(
        api_key="",
        video_model_id="locked-source",
        seed2_pro_model_id="seedpro",
        seed2_lite_model_id="lite",
    )

    config = default_agent_model_config(ark_settings)

    for role_id in ("hypothesis_strategist", "probe_synthesizer", "causal_comparator"):
        role = agent_role_definition(role_id)
        assert role is not None
        assert role.default_model_tier == "strong_reasoning"
        assert role.locked is False
        assert config.roles[role_id].model_id == "seedpro"
        assert config.roles[role_id].thinking == "enabled"
        assert config.roles[role_id].max_tokens is None


def test_stage_taxonomy_is_serializable_for_frontend() -> None:
    stages = [stage.model_dump(mode="json") for stage in debug_stage_definitions()]

    baseline = next(stage for stage in stages if stage["stage_id"] == "baseline")
    assert baseline["display_name"] == "基线复测"
    assert baseline["source_replay"] is True
    assert "judge_comparator" in baseline["owner_roles"]

    hypothesis = next(stage for stage in stages if stage["stage_id"] == "hypothesis")
    assert hypothesis["display_name"] == "候选假设"
    assert hypothesis["source_replay"] is False
    assert "hypothesis_strategist" in hypothesis["owner_roles"]

    causal_comparison = next(stage for stage in stages if stage["stage_id"] == "causal_comparison")
    assert causal_comparison["display_name"] == "因果比较"
    assert "causal_comparator" in causal_comparison["owner_roles"]
