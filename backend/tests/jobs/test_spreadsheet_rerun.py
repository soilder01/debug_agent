import pytest

from debug_agent.jobs.service import DebugJobService
from debug_agent.jobs.spreadsheet_rerun import rerun_spreadsheet_rows
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow
from debug_agent.storage.database import (
    create_sqlite_memory_session_factory,
    ensure_database_schema,
)
from debug_agent.storage.repository import DebugJobRepository


class RecordingSpreadsheetClient:
    def __init__(self) -> None:
        self.rows = [
            SpreadsheetSourceRow(row_id="2", values=_jszn_row("JSZN-131", "JSZN-131.mp4")),
            SpreadsheetSourceRow(row_id="3", values=_jszn_row("JSZN-096", "JSZN-096.mp4")),
        ]

    def list_rows(self, spreadsheet_id: str, sheet_id: str) -> list[SpreadsheetSourceRow]:
        assert spreadsheet_id == "spreadsheet-1"
        assert sheet_id == "sheet-1"
        return self.rows


@pytest.mark.asyncio
async def test_rerun_spreadsheet_rows_filters_rows_and_runs_debug_jobs() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    job_service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(
            outputs=[
                (
                    '{"video_action_segments":[{"subtask_label":"The right arm picks up the crab clamp and adjusts its position",'
                    '"start_s":0.0,"end_s":23.0}]}'
                )
            ]
        ),
    )

    result = await rerun_spreadsheet_rows(
        client=RecordingSpreadsheetClient(),
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        repository=repository,
        job_service=job_service,
        row_ids=["2"],
        baseline_trials=1,
        auto_run=True,
    )

    assert result.imported_case_ids == ["JSZN-131"]
    assert result.skipped_row_ids == ["3"]
    assert len(result.jobs) == 1
    assert result.jobs[0].case_id == "JSZN-131"
    assert result.jobs[0].status == "completed"
    assert result.jobs[0].artifact_group_id.startswith("sheet-rerun-")
    assert len(result.jobs[0].artifact_group_id) <= 40
    batch = repository.get_batch(result.jobs[0].artifact_group_id)
    assert batch is not None
    assert batch.total_jobs == 1
    assert batch.retry_policy["source"] == "spreadsheet_rerun"
    assert batch.retry_policy["row_ids"] == ["2"]
    assert repository.get_job(result.jobs[0].job_id).status == "completed"
    assert repository.get_spreadsheet_row_mapping_by_job_id(result.jobs[0].job_id).row_id == "2"


@pytest.mark.asyncio
async def test_rerun_spreadsheet_rows_filters_case_ids_and_creates_batch() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    job_service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(
            outputs=[
                (
                    '{"video_action_segments":[{"subtask_label":"The right arm picks up the crab clamp and adjusts its position",'
                    '"start_s":0.0,"end_s":23.0}]}'
                )
            ]
        ),
    )

    result = await rerun_spreadsheet_rows(
        client=RecordingSpreadsheetClient(),
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        repository=repository,
        job_service=job_service,
        row_ids=[],
        case_ids=["JSZN-096"],
        baseline_trials=1,
        auto_run=False,
    )

    assert result.imported_case_ids == ["JSZN-096"]
    assert result.skipped_row_ids == ["2"]
    assert len(result.jobs) == 1
    assert result.jobs[0].case_id == "JSZN-096"
    assert result.jobs[0].status == "created"
    assert repository.get_spreadsheet_row_mapping_by_job_id(result.jobs[0].job_id).row_id == "3"
    batch = repository.get_batch(result.jobs[0].artifact_group_id)
    assert batch is not None
    assert batch.retry_policy["case_ids"] == ["JSZN-096"]


@pytest.mark.asyncio
async def test_rerun_spreadsheet_rows_uses_media_resolver_before_import() -> None:
    session_factory, engine = create_sqlite_memory_session_factory()
    ensure_database_schema(engine)
    repository = DebugJobRepository(session_factory)
    job_service = DebugJobService(
        repository,
        model_provider=lambda _: FakeModelAdapter(outputs=["{}"]),
    )
    downloaded_uri = "file:///downloaded/JSZN-131.mp4"

    def resolve_media(row: SpreadsheetSourceRow) -> SpreadsheetSourceRow:
        values = dict(row.values)
        if values.get("video") == "JSZN-131.mp4":
            values["video"] = downloaded_uri
        return SpreadsheetSourceRow(row_id=row.row_id, values=values)

    result = await rerun_spreadsheet_rows(
        client=RecordingSpreadsheetClient(),
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        repository=repository,
        job_service=job_service,
        row_ids=["2"],
        baseline_trials=1,
        auto_run=False,
        row_media_resolver=resolve_media,
    )

    assert result.imported_case_ids == ["JSZN-131"]
    assert result.imported_rows[0].case.image_uri == downloaded_uri
    saved_case = repository.get_case("JSZN-131")
    assert saved_case is not None
    assert saved_case.image_uri == downloaded_uri


def _jszn_row(case_id: str, video: str) -> dict[str, object]:
    return {
        "id": case_id,
        "user prompt": "Segment the video and return video_action_segments JSON.",
        "参考答案": """
        {
          "video_action_segments": [
            {
              "subtask_label": "The right arm picks up the crab clamp and adjusts its position",
              "start_s": 0.1,
              "end_s": 23.1
            }
          ]
        }
        """,
        "predict": [
            """
            {
              "video_action_segments": [
                {
                  "subtask_label": "The right arm picks up the crab clamp and adjusts its position",
                  "start_s": 0.0,
                  "end_s": 34.0
                }
              ]
            }
            """
        ],
        "score": "[0]",
        "video": video,
        "chains_alpha": """
        [
          {
            "op_name": "check_timestamp",
            "format": "float",
            "in_key": "video_action_segments",
            "grids": [
              {
                "start_s": {"type": "range", "min": 0.0, "max": 1.0},
                "end_s": {"type": "range", "min": 22.0, "max": 24.0}
              }
            ]
          }
        ]
        """,
    }
