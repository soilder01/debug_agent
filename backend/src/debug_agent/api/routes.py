from __future__ import annotations

import sys
import types
from typing import Any

from debug_agent.api import routes_runtime as _runtime

__all__ = ["AssistantChatResponse", "XiaoDTurnDecision", "router"]

_LOCAL_ATTRS = {
    "_runtime",
    "_RoutesFacadeModule",
    "_LOCAL_ATTRS",
    "__all__",
    "__getattr__",
    "__dir__",
    "Any",
    "sys",
    "types",
}

router = _runtime.router
AssistantChatResponse = _runtime.AssistantChatResponse
XiaoDTurnDecision = _runtime.XiaoDTurnDecision


def __getattr__(name: str) -> Any:
    return getattr(_runtime, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_runtime)))


class _RoutesFacadeModule(types.ModuleType):
    def __getattribute__(self, name: str) -> Any:
        if name not in _LOCAL_ATTRS and not name.startswith("__"):
            runtime = types.ModuleType.__getattribute__(self, "_runtime")
            if hasattr(runtime, name):
                return getattr(runtime, name)
        return types.ModuleType.__getattribute__(self, name)

    def __getattr__(self, name: str) -> Any:
        return getattr(_runtime, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in _LOCAL_ATTRS or name.startswith("__"):
            types.ModuleType.__setattr__(self, name, value)
        else:
            setattr(_runtime, name, value)

    def __delattr__(self, name: str) -> None:
        if name in _LOCAL_ATTRS or name.startswith("__"):
            types.ModuleType.__delattr__(self, name)
        elif hasattr(_runtime, name):
            delattr(_runtime, name)
        else:
            types.ModuleType.__delattr__(self, name)


sys.modules[__name__].__class__ = _RoutesFacadeModule
