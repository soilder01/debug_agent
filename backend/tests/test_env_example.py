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


def test_env_example_defaults_to_usable_ark_lite_model_config() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_MODEL_PROVIDER"] == "ark-video"
    assert values["ARK_BASE_URL"] == "https://ark-cn-beijing.bytedance.net/api/v3"
    assert values["ARK_CONTENT_TASKS_URL"] == "https://ark-cn-beijing.bytedance.net/api/v3/contents/generations/tasks"
    assert values["ARK_SEED2_LITE_MODEL_ID"] == "ep-20260609151048-sbfnk"
    assert values["ARK_SEED2_PRO_MODEL_ID"] == "ep-20260609191630-7gkjm"
    assert values["ARK_VIDEO_MODEL_ID"] == "ep-20260604110333-dhrf7"
    assert values["ARK_VIDEO_MODE"] == "high"
    assert values["ARK_VIDEO_DISABLE_THINKING"] == "1"


def test_env_example_does_not_commit_real_ark_api_key() -> None:
    values = _read_env_example()

    assert values["ARK_API_KEY"] == "replace-with-your-local-ark-api-key"
    assert re.fullmatch(
        r"ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        values["ARK_API_KEY"],
    ) is None


def test_env_example_contains_lark_spreadsheet_connectivity_fixture() -> None:
    values = _read_env_example()

    assert (
        values["LARK_SPREADSHEET_URL"]
        == "https://bytedance.larkoffice.com/sheets/NLews6C2ShValptV7IdcJ62tnWc?sheet=qJAomX"
    )
    assert values["LARK_SHEET_ID"] == "qJAomX"
    assert values["LARK_CLI_TIMEOUT_SECONDS"] == "60"


def test_env_example_contains_report_base_url_for_writeback_links() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_REPORT_BASE_URL"] == "http://localhost:8000"


def test_env_example_disables_auto_writeback_by_default() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_AUTO_WRITEBACK_ENABLED"] == "0"


def test_env_example_keeps_trusted_actor_enforcement_off_for_local_dev() -> None:
    values = _read_env_example()

    assert values["DEBUG_AGENT_REQUIRE_TRUSTED_ACTOR"] == "0"
