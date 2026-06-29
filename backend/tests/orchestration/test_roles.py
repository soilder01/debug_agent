from debug_agent.orchestration.roles import logical_agent_roles


def test_logical_agent_roles_are_stable_and_complete() -> None:
    roles = logical_agent_roles()

    assert [role.role_id for role in roles] == [
        "case_intake",
        "experiment_planner",
        "model_runner",
        "judge_comparator",
        "evidence_artifact",
        "report_root_cause",
        "hypothesis_strategist",
        "probe_synthesizer",
        "causal_comparator",
        "writeback_operator",
    ]
    assert all(role.display_name for role in roles)
    assert all(role.responsibility for role in roles)
