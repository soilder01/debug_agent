import re
from pathlib import Path


def _read_env_example() -> dict[str, str]:
    env_path = Path(__file__).parents[2] / ".env.example"
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def test_env_example_documents_ark_model_config_without_internal_ids() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_MODEL_PROVIDER"] == "ark-video"
    assert values["ARK_BASE_URL"] == "https://ark.example.com/api/v3"
    assert (
        values["ARK_CONTENT_TASKS_URL"]
        == "https://ark.example.com/api/v3/contents/generations/tasks"
    )
    assert values["ARK_SEEDANCE2_MODEL_ID"] == "replace-with-seedance2-model-id"
    assert values["ARK_SEED2_LITE_MODEL_ID"] == "replace-with-seed2-lite-model-id"
    assert values["ARK_SEED2_PRO_MODEL_ID"] == "replace-with-seed2-pro-model-id"
    assert values["ARK_CHAT_MODEL_ID"] == "replace-with-chat-model-id"
    assert values["ARK_VIDEO_MODEL_ID"] == "replace-with-video-model-id"
    assert values["ARK_VIDEO_MODE"] == "high"
    assert values["ARK_VIDEO_DISABLE_THINKING"] == "1"


def test_env_example_does_not_commit_real_ark_api_key() -> None:
    values = _read_env_example()

    assert values["ARK_API_KEY"] == "replace-with-your-local-ark-api-key"
    assert (
        re.fullmatch(
            r"ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            values["ARK_API_KEY"],
        )
        is None
    )


def test_env_example_keeps_lark_spreadsheet_fixture_empty_by_default() -> None:
    values = _read_env_example()

    assert values["LARK_SPREADSHEET_URL"] == ""
    assert values["LARK_SHEET_ID"] == ""
    assert values["LARK_CLI_TIMEOUT_SECONDS"] == "60"
    assert values["LARK_REPORT_DOCS_ENABLED"] == "0"
    assert values["LARK_REPORT_DOC_IDENTITY"] == "user"
    assert values["LARK_REPORT_DOC_PROFILE"] == ""
    assert values["LARK_REPORT_DOC_PARENT_TOKEN"] == ""
    assert values["LARK_REPORT_DOC_PARENT_POSITION"] == ""
    assert values["LARK_CLI_PROFILE"] == "xiaoD"
    assert values["LARK_CLI_IDENTITY"] == "bot"
    assert values["LARK_EVENT_MODE"] == "long_connection"
    assert values["LARK_BOT_VERIFICATION_TOKEN"] == ""
    assert values["LARK_BOT_ENCRYPT_KEY"] == ""
    assert values["LARK_BOT_ACTION_TOKEN_SECRET"] == ""


def test_env_example_contains_report_base_url_for_writeback_links() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_REPORT_BASE_URL"] == "http://localhost:8000"


def test_env_example_disables_auto_writeback_by_default() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_AUTO_WRITEBACK_ENABLED"] == "0"


def test_env_example_enables_auto_closure_by_default() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_AUTO_CLOSURE_ENABLED"] == "1"


def test_env_example_keeps_trusted_actor_enforcement_off_for_local_dev() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR"] == "0"
