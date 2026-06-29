from pathlib import Path

from debug_agent.assistant.knowledge_base import DebugLesson, default_knowledge_base


def test_project_knowledge_base_retrieves_usage_flow() -> None:
    knowledge_base = default_knowledge_base()

    chunks = knowledge_base.search("用户怎么使用调查工作台提交调试任务", limit=3)

    assert chunks
    assert any("调查工作台" in chunk.title or "调查工作台" in chunk.content for chunk in chunks)


def test_enterprise_knowledge_documents_are_delivery_grade() -> None:
    knowledge_dir = Path(__file__).resolve().parents[2] / "src" / "debug_agent" / "assistant" / "knowledge"
    documents = sorted(knowledge_dir.glob("*.md"))

    assert len(documents) >= 10
    for document in documents:
        assert len(document.read_text(encoding="utf-8").splitlines()) >= 500, document.name


def test_vector_knowledge_base_builds_sqlite_index(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'knowledge.db').as_posix()}"
    knowledge_base = default_knowledge_base(database_url=database_url)

    status = knowledge_base.index_status()
    chunks = knowledge_base.search("企业级落地交付 服务对象 验收标准", limit=3)

    assert status.document_count >= 10
    assert status.chunk_count >= 200
    assert status.embedding_provider == "local-hash-v1"
    assert chunks
    assert chunks[0].source == "enterprise_delivery_handbook.md"


def test_debug_lesson_is_persisted_and_retrievable(tmp_path) -> None:
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'knowledge.db').as_posix()}"
    knowledge_base = default_knowledge_base(database_url=database_url)

    knowledge_base.add_debug_lesson(
        DebugLesson(
            lesson_id="lesson-video-right-arm",
            job_id="job-1",
            case_id="case-video-1",
            failure_summary="视频动作片段漏掉右臂套袋动作",
            root_cause="prompt_scoring_alignment_gap",
            confidence="medium",
            debug_loop_decision="stopped_evidence_exhausted",
            evidence_boundary="三轮 probe 后没有 supported causal comparison",
            recommended_action="补充右臂动作评分点并人工复核",
            source_uri="http://localhost:8000/xiaod/views/jobs/job-1/report",
            approved=False,
        )
    )

    status = knowledge_base.index_status()
    chunks = knowledge_base.search("右臂套袋 动作 证据耗尽", limit=3)

    assert status.debug_lesson_count == 1
    assert any(chunk.source_type == "debug_lesson" for chunk in chunks)
