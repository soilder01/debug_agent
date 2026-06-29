from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    title: str
    content: str
    source: str
    tags: tuple[str, ...] = ()
    source_type: str = "manual"
    source_uri: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class DebugLesson:
    lesson_id: str
    job_id: str
    case_id: str
    failure_summary: str
    root_cause: str
    confidence: str
    debug_loop_decision: str
    evidence_boundary: str
    recommended_action: str
    source_uri: str = ""
    approved: bool = False


@dataclass(frozen=True)
class KnowledgeIndexStatus:
    document_count: int
    chunk_count: int
    debug_lesson_count: int
    embedding_provider: str
    database_url: str = ""


class LocalHashEmbeddingProvider:
    """Deterministic embedding provider for offline tests and local dogfood.

    It is intentionally simple but vector-based. Production can replace this provider
    with Ark/ByteDance embeddings without changing the retrieval contract.
    """

    provider_id = "local-hash-v1"

    def __init__(self, dimension: int = 96) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        vector = [0.0 for _ in range(self.dimension)]
        terms = _terms(text)
        if not terms:
            return vector
        for term in terms:
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + min(2.0, len(term) / 8)
            vector[index] += sign * weight
        return _normalize_vector(vector)


class SQLiteKnowledgeVectorStore:
    def __init__(
        self,
        database_url: str,
        *,
        embedding_provider: LocalHashEmbeddingProvider | None = None,
    ) -> None:
        self.database_url = database_url
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()

    def rebuild(self, chunks: list[KnowledgeChunk]) -> KnowledgeIndexStatus:
        with self._connect() as connection:
            self._ensure_schema(connection)
            connection.execute("DELETE FROM knowledge_chunks WHERE source_type = 'manual'")
            connection.execute("DELETE FROM knowledge_documents WHERE source_type = 'manual'")
            for source in sorted({chunk.source for chunk in chunks}):
                source_chunks = [chunk for chunk in chunks if chunk.source == source]
                document_id = f"manual:{source}"
                connection.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_documents (
                        document_id, source_type, source_uri, title, metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        document_id,
                        "manual",
                        source,
                        source,
                        json.dumps({"chunk_count": len(source_chunks)}, ensure_ascii=False),
                    ),
                )
                for chunk in source_chunks:
                    self._upsert_chunk(connection, document_id=document_id, chunk=chunk)
            connection.commit()
            return self.status(connection)

    def search(self, query: str, *, limit: int = 5) -> list[KnowledgeChunk]:
        query_embedding = self.embedding_provider.embed(query)
        query_terms = _terms(query)
        with self._connect() as connection:
            self._ensure_schema(connection)
            rows = connection.execute(
                """
                SELECT chunk_id, title, content, source, source_type, source_uri,
                       tags_json, metadata_json, embedding_json, embedding_provider
                FROM knowledge_chunks
                """
            ).fetchall()
        scored: list[tuple[float, KnowledgeChunk]] = []
        for row in rows:
            chunk = _chunk_from_row(row)
            embedding = _loads_float_list(str(row["embedding_json"]))
            vector_score = _cosine_similarity(query_embedding, embedding)
            text_score = _term_score(query_terms, chunk)
            title_score = _title_score(query_terms, chunk)
            source_bonus = 0.04 if chunk.source_type == "manual" else 0.0
            score = vector_score * 0.42 + text_score * 0.42 + title_score * 0.12 + source_bonus
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].source_type, item[1].source, item[1].chunk_id))
        return [chunk for _, chunk in scored[:limit]]

    def upsert_debug_lesson(self, lesson: DebugLesson) -> KnowledgeChunk:
        chunk = debug_lesson_to_chunk(lesson)
        with self._connect() as connection:
            self._ensure_schema(connection)
            connection.execute(
                """
                INSERT OR REPLACE INTO debug_lessons (
                    lesson_id, job_id, case_id, failure_summary, root_cause, confidence,
                    debug_loop_decision, evidence_boundary, recommended_action, source_uri,
                    approved, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    lesson.lesson_id,
                    lesson.job_id,
                    lesson.case_id,
                    lesson.failure_summary,
                    lesson.root_cause,
                    lesson.confidence,
                    lesson.debug_loop_decision,
                    lesson.evidence_boundary,
                    lesson.recommended_action,
                    lesson.source_uri,
                    1 if lesson.approved else 0,
                ),
            )
            document_id = f"debug_lesson:{lesson.lesson_id}"
            connection.execute(
                """
                INSERT OR REPLACE INTO knowledge_documents (
                    document_id, source_type, source_uri, title, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    document_id,
                    "debug_lesson",
                    lesson.source_uri,
                    f"Debug lesson {lesson.case_id}",
                    json.dumps({"job_id": lesson.job_id, "approved": lesson.approved}, ensure_ascii=False),
                ),
            )
            self._upsert_chunk(connection, document_id=document_id, chunk=chunk)
            connection.commit()
        return chunk

    def status(self, connection: sqlite3.Connection | None = None) -> KnowledgeIndexStatus:
        owns_connection = connection is None
        active = connection or self._connect()
        try:
            self._ensure_schema(active)
            document_count = active.execute("SELECT count(*) FROM knowledge_documents").fetchone()[0]
            chunk_count = active.execute("SELECT count(*) FROM knowledge_chunks").fetchone()[0]
            debug_lesson_count = active.execute("SELECT count(*) FROM debug_lessons").fetchone()[0]
            return KnowledgeIndexStatus(
                document_count=document_count,
                chunk_count=chunk_count,
                debug_lesson_count=debug_lesson_count,
                embedding_provider=self.embedding_provider.provider_id,
                database_url=self.database_url,
            )
        finally:
            if owns_connection:
                active.close()

    def _upsert_chunk(
        self,
        connection: sqlite3.Connection,
        *,
        document_id: str,
        chunk: KnowledgeChunk,
    ) -> None:
        embedding = self.embedding_provider.embed(_embedding_text(chunk))
        connection.execute(
            """
            INSERT OR REPLACE INTO knowledge_chunks (
                chunk_id, document_id, source_type, source_uri, source, title, content,
                tags_json, metadata_json, embedding_json, embedding_provider, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                chunk.chunk_id,
                document_id,
                chunk.source_type,
                chunk.source_uri or chunk.source,
                chunk.source,
                chunk.title,
                chunk.content,
                json.dumps(list(chunk.tags), ensure_ascii=False),
                json.dumps(chunk.metadata, ensure_ascii=False),
                json.dumps(embedding, separators=(",", ":")),
                self.embedding_provider.provider_id,
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        database_path = _sqlite_path_from_url(self.database_url)
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                document_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_uri TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_uri TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                tags_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                embedding_json TEXT NOT NULL DEFAULT '[]',
                embedding_provider TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS debug_lessons (
                lesson_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL DEFAULT '',
                case_id TEXT NOT NULL DEFAULT '',
                failure_summary TEXT NOT NULL DEFAULT '',
                root_cause TEXT NOT NULL DEFAULT '',
                confidence TEXT NOT NULL DEFAULT '',
                debug_loop_decision TEXT NOT NULL DEFAULT '',
                evidence_boundary TEXT NOT NULL DEFAULT '',
                recommended_action TEXT NOT NULL DEFAULT '',
                source_uri TEXT NOT NULL DEFAULT '',
                approved INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_source_type ON knowledge_chunks(source_type)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_debug_lessons_job ON debug_lessons(job_id)"
        )


class ProjectKnowledgeBase:
    def __init__(
        self,
        chunks: list[KnowledgeChunk],
        *,
        vector_store: SQLiteKnowledgeVectorStore | None = None,
    ) -> None:
        self._chunks = chunks
        self._vector_store = vector_store
        self._index_status: KnowledgeIndexStatus | None = None
        if self._vector_store is not None:
            self._index_status = self._vector_store.rebuild(chunks)

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        *,
        database_url: str | None = None,
        vector_store: SQLiteKnowledgeVectorStore | None = None,
    ) -> "ProjectKnowledgeBase":
        chunks: list[KnowledgeChunk] = []
        if not directory.exists():
            return cls([], vector_store=vector_store)
        for path in sorted(directory.glob("*.md")):
            chunks.extend(_chunks_from_markdown(path))
        resolved_store = vector_store
        if resolved_store is None and database_url:
            resolved_store = SQLiteKnowledgeVectorStore(database_url)
        return cls(chunks, vector_store=resolved_store)

    def search(self, query: str, *, limit: int = 5) -> list[KnowledgeChunk]:
        if self._vector_store is not None:
            results = self._vector_store.search(query, limit=limit)
            if results:
                return results
        query_terms = _terms(query)
        if not query_terms:
            return self._chunks[:limit]
        scored: list[tuple[int, KnowledgeChunk]] = []
        for chunk in self._chunks:
            haystack = " ".join([chunk.title, chunk.content, " ".join(chunk.tags)])
            chunk_terms = _terms(haystack)
            score = len(query_terms & chunk_terms)
            for term in query_terms:
                if term in haystack.lower():
                    score += 1
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].source, item[1].chunk_id))
        return [chunk for _, chunk in scored[:limit]]

    def index_status(self) -> KnowledgeIndexStatus:
        if self._vector_store is not None:
            self._index_status = self._vector_store.status()
            return self._index_status
        return KnowledgeIndexStatus(
            document_count=len({chunk.source for chunk in self._chunks}),
            chunk_count=len(self._chunks),
            debug_lesson_count=0,
            embedding_provider="in-memory-keyword",
        )

    def add_debug_lesson(self, lesson: DebugLesson) -> KnowledgeChunk:
        chunk = debug_lesson_to_chunk(lesson)
        self._chunks.append(chunk)
        if self._vector_store is not None:
            return self._vector_store.upsert_debug_lesson(lesson)
        return chunk


def default_knowledge_base(database_url: str | None = None) -> ProjectKnowledgeBase:
    return ProjectKnowledgeBase.from_directory(
        Path(__file__).resolve().parent / "knowledge",
        database_url=database_url,
    )


def debug_lesson_to_chunk(lesson: DebugLesson) -> KnowledgeChunk:
    content = "\n".join(
        [
            f"失败现象：{lesson.failure_summary}",
            f"根因：{lesson.root_cause} / {lesson.confidence}",
            f"循环结论：{lesson.debug_loop_decision}",
            f"证据边界：{lesson.evidence_boundary}",
            f"推荐动作：{lesson.recommended_action}",
            "使用规则：只有 approved=true 或报告证据完整时，才能作为正向经验；否则只能作为风险提示。",
        ]
    )
    return KnowledgeChunk(
        chunk_id=f"debug_lesson:{lesson.lesson_id}",
        title=f"历史 Debug 经验：{lesson.failure_summary[:48]}",
        content=content,
        source=f"debug_lesson:{lesson.lesson_id}",
        source_type="debug_lesson",
        source_uri=lesson.source_uri,
        tags=("debug_lesson", lesson.root_cause, lesson.debug_loop_decision),
        metadata={
            "job_id": lesson.job_id,
            "case_id": lesson.case_id,
            "approved": lesson.approved,
            "confidence": lesson.confidence,
        },
    )


def _chunks_from_markdown(path: Path) -> list[KnowledgeChunk]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^##\s+", text)
    chunks: list[KnowledgeChunk] = []
    document_title = path.stem
    for index, section in enumerate(sections):
        stripped = section.strip()
        if not stripped:
            continue
        lines = stripped.splitlines()
        if index == 0 and lines[0].startswith("# "):
            title = lines[0].removeprefix("# ").strip()
            document_title = title
            content = "\n".join(lines[1:]).strip()
        else:
            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()
        if content:
            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"{path.stem}:{len(chunks) + 1}",
                    title=title,
                    content=content,
                    source=path.name,
                    tags=tuple(_terms(title)),
                    source_type="manual",
                    source_uri=path.as_posix(),
                    metadata={"path": path.as_posix(), "document_title": document_title},
                )
            )
    return chunks


def _terms(text: str) -> set[str]:
    normalized = text.lower()
    latin_terms = set(re.findall(r"[a-z0-9_:-]{2,}", normalized))
    cjk_terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", normalized))
    cjk_windows: set[str] = set()
    for term in cjk_terms:
        cjk_windows.update(term[start : start + 2] for start in range(max(1, len(term) - 1)))
        cjk_windows.update(term[start : start + 3] for start in range(max(1, len(term) - 2)))
    return latin_terms | cjk_terms | cjk_windows


def _embedding_text(chunk: KnowledgeChunk) -> str:
    metadata_text = " ".join(str(value) for value in chunk.metadata.values())
    return " ".join([chunk.title, chunk.content, " ".join(chunk.tags), metadata_text])


def _normalize_vector(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude <= 0:
        return vector
    return [round(value / magnitude, 8) for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    limit = min(len(left), len(right))
    return max(0.0, sum(left[index] * right[index] for index in range(limit)))


def _term_score(query_terms: set[str], chunk: KnowledgeChunk) -> float:
    if not query_terms:
        return 0.0
    haystack = " ".join([chunk.title, chunk.content, " ".join(chunk.tags)]).lower()
    chunk_terms = _terms(haystack)
    overlap = len(query_terms & chunk_terms) / max(1, len(query_terms))
    substring_hits = sum(1 for term in query_terms if term in haystack) / max(1, len(query_terms))
    return min(1.0, overlap * 0.65 + substring_hits * 0.35)


def _title_score(query_terms: set[str], chunk: KnowledgeChunk) -> float:
    if not query_terms:
        return 0.0
    document_title = str(chunk.metadata.get("document_title", "")).lower()
    title = f"{chunk.title} {document_title}".lower()
    source = chunk.source.lower()
    hits = sum(1 for term in query_terms if term in title or term in source)
    return min(1.0, hits / max(1, len(query_terms)))


def _chunk_from_row(row: sqlite3.Row) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=str(row["chunk_id"]),
        title=str(row["title"]),
        content=str(row["content"]),
        source=str(row["source"]),
        source_type=str(row["source_type"]),
        source_uri=str(row["source_uri"]),
        tags=tuple(_loads_string_list(str(row["tags_json"]))),
        metadata=_loads_dict(str(row["metadata_json"])),
    )


def _loads_float_list(value: str) -> list[float]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [float(item) for item in data if isinstance(item, int | float)]


def _loads_string_list(value: str) -> list[str]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if str(item)]


def _loads_dict(value: str) -> dict[str, object]:
    try:
        data = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _sqlite_path_from_url(database_url: str) -> str:
    if database_url in {"sqlite:///:memory:", "sqlite+pysqlite:///:memory:"}:
        return ":memory:"
    if database_url.startswith("sqlite+pysqlite:///"):
        raw_path = database_url.removeprefix("sqlite+pysqlite:///")
        return raw_path[1:] if len(raw_path) >= 3 and raw_path[0] == "/" and raw_path[2] == ":" else raw_path
    if database_url.startswith("sqlite:///"):
        raw_path = database_url.removeprefix("sqlite:///")
        return raw_path[1:] if len(raw_path) >= 3 and raw_path[0] == "/" and raw_path[2] == ":" else raw_path
    parsed = urlparse(database_url)
    if parsed.scheme in {"sqlite", "sqlite+pysqlite"}:
        path_text = unquote(parsed.path)
        if len(path_text) >= 3 and path_text[0] == "/" and path_text[2] == ":":
            return path_text[1:]
        return path_text
    raise ValueError(f"Only sqlite knowledge vector stores are supported locally: {database_url}")
