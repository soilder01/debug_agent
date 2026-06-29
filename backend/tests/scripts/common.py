# ruff: noqa: F401,F811
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from types import SimpleNamespace
import pytest

SCRIPT_ROOT = Path(__file__).parents[3] / "scripts"


def load_preflight_module() -> ModuleType:
    script = SCRIPT_ROOT / "production_preflight.py"
    spec = importlib.util.spec_from_file_location("production_preflight", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_pilot_record_module() -> ModuleType:
    script = SCRIPT_ROOT / "pilot_validation_record.py"
    spec = importlib.util.spec_from_file_location("pilot_validation_record", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lark_bot_probe_module() -> ModuleType:
    script = SCRIPT_ROOT / "lark_bot_webhook_probe.py"
    spec = importlib.util.spec_from_file_location("lark_bot_webhook_probe", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lark_bot_consumer_module() -> ModuleType:
    script = SCRIPT_ROOT / "lark_bot_long_connection_consumer.py"
    spec = importlib.util.spec_from_file_location("lark_bot_long_connection_consumer", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_xiaod_bot_e2e_smoke_module() -> ModuleType:
    script = SCRIPT_ROOT / "xiaod_bot_e2e_smoke.py"
    spec = importlib.util.spec_from_file_location("xiaod_bot_e2e_smoke", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_xiaod_debug_chain_monitor_module() -> ModuleType:
    script = SCRIPT_ROOT / "xiaod_debug_chain_monitor.py"
    spec = importlib.util.spec_from_file_location("xiaod_debug_chain_monitor", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def json_bytes(payload: dict[str, object]) -> bytes:
    import json

    return json.dumps(payload).encode("utf-8")
