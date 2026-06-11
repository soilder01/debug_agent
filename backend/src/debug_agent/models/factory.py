from debug_agent.cases.models import DebugCase
from debug_agent.models.adapters import ModelAdapter
from debug_agent.models.ark import ArkModelAdapter
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.settings import ArkSettings, ModelRuntimeSettings


def build_model_adapter(
    case: DebugCase,
    settings: ModelRuntimeSettings | None = None,
) -> ModelAdapter:
    runtime_settings = settings or ModelRuntimeSettings.from_env()
    if runtime_settings.provider == "fake":
        return FakeModelAdapter(outputs=[prediction.raw_output for prediction in case.predictions])

    if runtime_settings.provider == "ark-seed2-lite":
        ark_settings = ArkSettings.from_env()
        return ArkModelAdapter(settings=ark_settings, model_id=ark_settings.seed2_lite_model_id)
    if runtime_settings.provider == "ark-seed2-pro":
        ark_settings = ArkSettings.from_env()
        return ArkModelAdapter(settings=ark_settings, model_id=ark_settings.seed2_pro_model_id)

    raise ValueError(f"Unsupported model provider: {runtime_settings.provider}")
