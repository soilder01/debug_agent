from fastapi.testclient import TestClient

from debug_agent.assistant import chat as assistant_chat
from debug_agent.main import app
from debug_agent.models.adapters import ModelResponse


def test_assistant_chat_returns_rag_answer_with_citations(monkeypatch) -> None:
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "调查工作台怎么提交调试任务？"})

    assert response.status_code == 200
    payload = response.json()
    assert "调查工作台" in payload["answer"]
    assert payload["model_provider"] == "local-rag"
    assert payload["citations"]
    assert payload["citations"][0]["source"].endswith(".md")


def test_assistant_chat_supports_frontend_api_prefix(monkeypatch) -> None:
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/api/assistant/chat", json={"question": "数据导入怎么选？"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["citations"]


def test_assistant_chat_answers_identity_questions(monkeypatch) -> None:
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你是谁？"})

    assert response.status_code == 200
    payload = response.json()
    assert "小D" in payload["answer"]
    assert "Debug Agent" in payload["answer"]
    assert "整个产品" in payload["answer"]
    assert "DebugJob" in payload["answer"]
    assert "表格" in payload["answer"]
    assert payload["citations"]


def test_assistant_chat_answers_short_identity_question(monkeypatch) -> None:
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你是？"})

    assert response.status_code == 200
    payload = response.json()
    assert "小D" in payload["answer"]
    assert "Debug Agent" in payload["answer"]


def test_assistant_chat_uses_configured_model_for_general_questions(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            assert "用户消息：帮我写一句火星咖啡馆欢迎语" in prompt
            assert image_uri == ""
            return ModelResponse(
                model_name="fake-ark",
                model_provider="ark",
                model_id=self.kwargs["model_id"],
                trial=0,
                raw_output="欢迎来到火星咖啡馆。",
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setenv("ARK_CHAT_MODEL_ID", "ep-chat-default")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "帮我写一句火星咖啡馆欢迎语"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "欢迎来到火星咖啡馆。"
    assert payload["model_provider"] == "ark"
    assert payload["model_id"] == "ep-chat-default"
    assert payload["citations"] == []


def test_assistant_chat_allows_request_model_override(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            return ModelResponse(
                model_name="fake-ark",
                model_provider="ark",
                model_id=self.kwargs["model_id"],
                trial=0,
                raw_output="已按指定模型回答。",
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setenv("ARK_CHAT_MODEL_ID", "ep-chat-default")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post(
        "/assistant/chat",
        json={"question": "你会什么？", "model_id": "ep-user-selected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "已按指定模型回答。"
    assert payload["model_id"] == "ep-user-selected"


def test_assistant_chat_falls_back_when_model_returns_empty_answer(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            return ModelResponse(
                model_name="fake-ark",
                model_provider="ark",
                model_id="ep-fake",
                trial=0,
                raw_output="  ",
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "帮我写一句火星咖啡馆欢迎语"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].strip()
    assert payload["answer"] != "  "
    assert payload["model_provider"] == "local-rag"


def test_assistant_chat_reports_ark_endpoint_closed_reason(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            raise RuntimeError(
                'Ark HTTP 400 Bad Request: {"error":{"code":"InvalidEndpoint.ClosedEndpoint"}}'
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你会什么？"})

    assert response.status_code == 200
    payload = response.json()
    assert "Ark endpoint 已关闭或临时不可用" in payload["answer"]
    assert payload["model_provider"] == "local-rag"


def test_assistant_chat_reports_ark_access_denied_reason(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            raise RuntimeError('Ark HTTP 403 Forbidden: {"error":{"code":"AccessDenied"}}')

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你会什么？"})

    assert response.status_code == 200
    payload = response.json()
    assert "没有访问权限" in payload["answer"]
    assert "AccessDenied" in payload["answer"]
    assert payload["model_provider"] == "local-rag"


def test_assistant_chat_strips_control_chars_from_model_answer(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            return ModelResponse(
                model_name="fake-ark",
                model_provider="ark",
                model_id="ep-fake",
                trial=0,
                raw_output="我是小D\u0085，可以帮你处理 badcase。\u0000",
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你会什么？"})

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert answer == "我是小D，可以帮你处理 badcase。"


def test_assistant_chat_strips_emoji_from_model_answer(monkeypatch) -> None:
    class FakeArkModelAdapter:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def generate(self, prompt: str, image_uri: str) -> ModelResponse:
            return ModelResponse(
                model_name="fake-ark",
                model_provider="ark",
                model_id="ep-fake",
                trial=0,
                raw_output="我是小D😉，可以帮你处理 badcase ✅",
            )

    monkeypatch.setenv("ARK_API_KEY", "fake-key")
    monkeypatch.setattr(assistant_chat, "ArkModelAdapter", FakeArkModelAdapter)
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": "你会什么？"})

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert answer == "我是小D，可以帮你处理 badcase"


def test_assistant_chat_rejects_empty_question() -> None:
    client = TestClient(app)

    response = client.post("/assistant/chat", json={"question": ""})

    assert response.status_code == 422


def test_assistant_knowledge_status_and_search_api() -> None:
    client = TestClient(app)

    status_response = client.get("/assistant/knowledge/status")
    search_response = client.post(
        "/assistant/knowledge/search",
        json={"query": "企业级落地交付 服务对象 验收标准", "limit": 3},
    )

    assert status_response.status_code == 200
    status = status_response.json()
    assert status["document_count"] >= 10
    assert status["chunk_count"] >= 200
    assert status["embedding_provider"] == "local-hash-v1"
    assert search_response.status_code == 200
    search = search_response.json()
    assert search["chunks"]
    assert search["chunks"][0]["source"] == "enterprise_delivery_handbook.md"


def test_assistant_knowledge_debug_lesson_api_persists_and_searches() -> None:
    client = TestClient(app)

    lesson_response = client.post(
        "/assistant/knowledge/debug-lessons",
        json={
            "lesson_id": "api-lesson-right-arm",
            "job_id": "job-api-lesson",
            "case_id": "case-api-lesson",
            "failure_summary": "视频动作片段漏掉右臂套袋动作",
            "root_cause": "prompt_scoring_alignment_gap",
            "confidence": "medium",
            "debug_loop_decision": "stopped_evidence_exhausted",
            "evidence_boundary": "三轮 probe 后仍没有 supported causal comparison",
            "recommended_action": "补充右臂动作评分点并人工复核",
            "source_uri": "http://localhost:8000/xiaod/views/jobs/job-api-lesson/report",
            "approved": False,
        },
    )
    search_response = client.post(
        "/assistant/knowledge/search",
        json={"query": "右臂套袋 动作 证据耗尽", "limit": 5},
    )

    assert lesson_response.status_code == 200
    assert lesson_response.json()["chunk"]["source_type"] == "debug_lesson"
    assert search_response.status_code == 200
    assert any(chunk["source_type"] == "debug_lesson" for chunk in search_response.json()["chunks"])
