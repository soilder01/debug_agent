# CSV Column Aliases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Allow CSV case import to accept real table-style column names, including common Chinese labels, while preserving the existing internal CSV contract.

**Architecture:** Add a small canonicalization layer inside the backend CSV mapper. `csv.DictReader` rows will be normalized from aliases to canonical `DebugCase` fields before validation; API and frontend request/response shapes remain unchanged.

**Tech Stack:** Python 3.11, stdlib `csv`, pytest, Pydantic v2, FastAPI.

---

## File Structure

- Modify `backend/src/debug_agent/imports/csv_cases.py`: add column alias constants, row normalization, and duplicate canonical column protection.
- Modify `backend/tests/imports/test_csv_cases.py`: add focused tests for Chinese/real-table aliases and alias conflict rejection.
- Modify `backend/tests/api/test_csv_import.py`: add API-level regression for alias CSV import creating runnable jobs.
- Create `docs/superpowers/plans/2026-06-10-csv-column-aliases.md`: this plan.

## Alias Contract

Canonical fields still supported:
- `case_id`
- `image_uri`
- `prompt`
- `golden_answer_json`
- `scoring_standard`
- `predictions_json`
- `avg_score`
- `debug_status`
- `root_cause`

Additional aliases:
- `case_id`: `case id`, `样本ID`, `样本 ID`, `样本编号`
- `image_uri`: `image_url`, `image url`, `图片`, `图片链接`, `图片URL`
- `prompt`: `提示词`, `模型输入`, `题目prompt`
- `golden_answer_json`: `标答JSON`, `标准答案JSON`, `golden answer json`
- `scoring_standard`: `评分标准`, `打分标准`, `scoring standard`
- `predictions_json`: `预测JSON`, `模型预测JSON`, `模型输出JSON`, `predictions json`
- `avg_score`: `平均分`, `avg score`
- `debug_status`: `debug状态`, `debug status`, `状态`
- `root_cause`: `错误原因`, `根因`, `root cause`

Duplicate aliases that normalize to the same canonical field must reject the row, because silently choosing one value can corrupt case data.

## Task 1: Mapper Alias Support

**Files:**
- Modify: `backend/tests/imports/test_csv_cases.py`
- Modify: `backend/src/debug_agent/imports/csv_cases.py`

- [x] **Step 1: Write failing alias mapper tests**

Append these tests to `backend/tests/imports/test_csv_cases.py`:

```python
def test_parse_csv_cases_accepts_table_column_aliases() -> None:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "84"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "样本ID",
            "图片链接",
            "提示词",
            "标答JSON",
            "评分标准",
            "模型预测JSON",
            "平均分",
            "debug状态",
            "错误原因",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "样本ID": "alias-csv-1",
            "图片链接": "file://alias.png",
            "提示词": "Read the handwritten answer",
            "标答JSON": json.dumps(golden_answer),
            "评分标准": "exact match",
            "模型预测JSON": json.dumps(predictions),
            "平均分": "1.0",
            "debug状态": "pending",
            "错误原因": "visual_recognition_failure",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.rejected_rows == []
    assert len(result.cases) == 1
    case = result.cases[0]
    assert case.case_id == "alias-csv-1"
    assert case.image_uri == "file://alias.png"
    assert case.golden_answer.answers[0].student_answer == "84"
    assert case.predictions[0].raw_output == raw_output
    assert case.human_notes.debug_status == "pending"
    assert case.human_notes.root_cause == "visual_recognition_failure"


def test_parse_csv_cases_rejects_duplicate_alias_columns() -> None:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "case_id",
            "样本ID",
            "image_uri",
            "prompt",
            "golden_answer_json",
            "scoring_standard",
            "predictions_json",
            "avg_score",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "case_id": "canonical-id",
            "样本ID": "alias-id",
            "image_uri": "file://image.png",
            "prompt": "Read the answer",
            "golden_answer_json": json.dumps({"answers": [{"box_id": 1, "student_answer": "42"}]}),
            "scoring_standard": "exact match",
            "predictions_json": "[]",
            "avg_score": "0.0",
        }
    )

    result = parse_csv_cases(output.getvalue())

    assert result.cases == []
    assert len(result.rejected_rows) == 1
    assert result.rejected_rows[0].row_number == 2
    assert "Duplicate CSV columns for case_id" in result.rejected_rows[0].error_message
```

- [x] **Step 2: Run mapper tests to verify failure**

Run:

```powershell
python -m pytest tests/imports/test_csv_cases.py -q
```

Expected: FAIL because alias columns are not normalized yet.

- [x] **Step 3: Implement row normalization**

In `backend/src/debug_agent/imports/csv_cases.py`, add this alias map after the imports:

```python
COLUMN_ALIASES: dict[str, str] = {
    "case_id": "case_id",
    "case id": "case_id",
    "样本ID": "case_id",
    "样本 ID": "case_id",
    "样本编号": "case_id",
    "image_uri": "image_uri",
    "image_url": "image_uri",
    "image url": "image_uri",
    "图片": "image_uri",
    "图片链接": "image_uri",
    "图片URL": "image_uri",
    "prompt": "prompt",
    "提示词": "prompt",
    "模型输入": "prompt",
    "题目prompt": "prompt",
    "golden_answer_json": "golden_answer_json",
    "golden answer json": "golden_answer_json",
    "标答JSON": "golden_answer_json",
    "标准答案JSON": "golden_answer_json",
    "scoring_standard": "scoring_standard",
    "scoring standard": "scoring_standard",
    "评分标准": "scoring_standard",
    "打分标准": "scoring_standard",
    "predictions_json": "predictions_json",
    "predictions json": "predictions_json",
    "预测JSON": "predictions_json",
    "模型预测JSON": "predictions_json",
    "模型输出JSON": "predictions_json",
    "avg_score": "avg_score",
    "avg score": "avg_score",
    "平均分": "avg_score",
    "debug_status": "debug_status",
    "debug status": "debug_status",
    "debug状态": "debug_status",
    "状态": "debug_status",
    "root_cause": "root_cause",
    "root cause": "root_cause",
    "错误原因": "root_cause",
    "根因": "root_cause",
}
```

Add helper functions:

```python
def _canonical_column_name(column_name: str) -> str:
    stripped = column_name.strip()
    return COLUMN_ALIASES.get(stripped, stripped)


def _normalize_row_columns(row: dict[str, str | None]) -> dict[str, str | None]:
    normalized: dict[str, str | None] = {}
    source_columns: dict[str, str] = {}
    for column_name, value in row.items():
        canonical_name = _canonical_column_name(column_name)
        if canonical_name in normalized:
            previous_column = source_columns[canonical_name]
            raise ValueError(
                f"Duplicate CSV columns for {canonical_name}: {previous_column}, {column_name}"
            )
        normalized[canonical_name] = value
        source_columns[canonical_name] = column_name
    return normalized
```

Then change `parse_csv_cases` from:

```python
cases.append(_row_to_case(row))
```

to:

```python
cases.append(_row_to_case(_normalize_row_columns(row)))
```

- [x] **Step 4: Run mapper tests**

Run:

```powershell
python -m pytest tests/imports/test_csv_cases.py -q
```

Expected: PASS.

## Task 2: API Alias Regression

**Files:**
- Modify: `backend/tests/api/test_csv_import.py`

- [x] **Step 1: Write failing API alias test**

Append this helper and test to `backend/tests/api/test_csv_import.py`:

```python
def alias_csv_text() -> str:
    golden_answer = {"answers": [{"box_id": 1, "student_answer": "84"}]}
    raw_output = json.dumps(golden_answer)
    predictions = [{"trial": 1, "raw_output": raw_output, "score": 1}]
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "样本ID",
            "图片链接",
            "提示词",
            "标答JSON",
            "评分标准",
            "模型预测JSON",
            "平均分",
            "debug状态",
            "错误原因",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "样本ID": "csv-alias-import-1",
            "图片链接": "file://alias.png",
            "提示词": "Read the answer",
            "标答JSON": json.dumps(golden_answer),
            "评分标准": "exact match",
            "模型预测JSON": json.dumps(predictions),
            "平均分": "1.0",
            "debug状态": "pending",
            "错误原因": "visual_recognition_failure",
        }
    )
    return output.getvalue()


def test_csv_import_accepts_alias_columns_and_creates_jobs() -> None:
    client = TestClient(app)

    response = client.post("/imports/csv", json={"csv_text": alias_csv_text(), "create_jobs": True})

    assert response.status_code == 202
    body = response.json()
    assert body["imported_case_ids"] == ["csv-alias-import-1"]
    assert body["rejected_rows"] == []
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["case_id"] == "csv-alias-import-1"

    job_id = body["jobs"][0]["job_id"]
    worker_response = client.post("/jobs/run-next")
    assert worker_response.status_code == 200
    assert worker_response.json()["job_id"] == job_id
    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "completed"
    assert len(status["evidence_ids"]) == 6
```

- [x] **Step 2: Run API test**

Run:

```powershell
python -m pytest tests/api/test_csv_import.py -q
```

Expected: PASS after Task 1 normalization.

## Task 3: Full Verification And Commit

**Files:**
- Modify: `backend/src/debug_agent/imports/csv_cases.py`
- Modify: `backend/tests/imports/test_csv_cases.py`
- Modify: `backend/tests/api/test_csv_import.py`
- Create: `docs/superpowers/plans/2026-06-10-csv-column-aliases.md`

- [x] **Step 1: Run full verification**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify.ps1 -Target all
```

Expected: backend tests, frontend tests, lint, and typecheck all pass.

- [x] **Step 2: Run diagnostics**

Run diagnostics for edited backend files.

Expected: no diagnostics.

- [x] **Step 3: Secret scan**

Run:

```powershell
Select-String -Path backend/src/debug_agent/imports/csv_cases.py,backend/tests/imports/test_csv_cases.py,backend/tests/api/test_csv_import.py,docs/superpowers/plans/2026-06-10-csv-column-aliases.md -Pattern 'ark-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
```

Expected: no output.

- [x] **Step 4: Commit**

Run:

```powershell
git add backend/src/debug_agent/imports/csv_cases.py backend/tests/imports/test_csv_cases.py backend/tests/api/test_csv_import.py docs/superpowers/plans/2026-06-10-csv-column-aliases.md
git commit -m "feat(imports): support csv column aliases"
```

Expected: one commit containing only Phase 24 CSV alias mapping changes and plan.

## Self-Review

- Spec coverage: The plan adds aliases for real table-style column names, preserves canonical names, rejects duplicate aliases, and verifies API import compatibility.
- Placeholder scan: No TBD, TODO, or vague implementation steps remain.
- Type consistency: All tests call existing `parse_csv_cases` and `/imports/csv`; response field names stay unchanged.
