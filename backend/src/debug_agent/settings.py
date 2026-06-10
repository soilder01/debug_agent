import os

from pydantic import BaseModel, SecretStr


class ArkSettings(BaseModel):
    api_key: SecretStr
    base_url: str = "https://ark-cn-beijing.bytedance.net/api/v3"
    content_tasks_url: str = "https://ark-cn-beijing.bytedance.net/api/v3/contents/generations/tasks"
    seed2_lite_model_id: str = "ep-20260609151048-sbfnk"
    seed2_pro_model_id: str = "ep-20260609191630-7gkjm"

    @classmethod
    def from_env(cls) -> "ArkSettings":
        api_key = os.environ.get("ARK_API_KEY", "")
        if not api_key:
            raise RuntimeError("ARK_API_KEY is required for live Ark model calls")
        return cls(
            api_key=SecretStr(api_key),
            base_url=os.environ.get("ARK_BASE_URL", cls.model_fields["base_url"].default),
            content_tasks_url=os.environ.get(
                "ARK_CONTENT_TASKS_URL", cls.model_fields["content_tasks_url"].default
            ),
            seed2_lite_model_id=os.environ.get(
                "ARK_SEED2_LITE_MODEL_ID", cls.model_fields["seed2_lite_model_id"].default
            ),
            seed2_pro_model_id=os.environ.get(
                "ARK_SEED2_PRO_MODEL_ID", cls.model_fields["seed2_pro_model_id"].default
            ),
        )
