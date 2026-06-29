# ruff: noqa: F401
import io
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import zipfile
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from pydantic import SecretStr

from debug_agent.api import routes
from debug_agent.jobs.service import DebugJobService
from debug_agent.main import app
from debug_agent.lark.bot import calculate_lark_bot_event_signature
from debug_agent.lark.connector import LarkConnectorStatus
from debug_agent.models.fake import FakeModelAdapter
from debug_agent.spreadsheets.lark import LarkSpreadsheetClient
from debug_agent.spreadsheets.sync import SpreadsheetSourceRow
from debug_agent.storage.models import (
    LarkBotPendingCommandRow,
    XiaoDExecutionRunRow,
    XiaoDPendingDecisionRow,
)
from debug_agent.xiaod.schemas import XiaoDTurnHandleRequest
from tests.api.lark_bot_helpers import (
    DummyModelResult,
    RecordingBaseConnector,
    RecordingDocsConnector,
    RecordingWritebackClient,
    RowsJsonSpreadsheetTransport,
    StaticSpreadsheetClient,
    completed_debug_report as _completed_debug_report,
    create_spreadsheet_rerun_writeback_decision_fixture as _create_spreadsheet_rerun_writeback_decision_fixture,
    encrypt_lark_event_payload as _encrypt_lark_event_payload,
    mark_auto_closure_completed as _mark_auto_closure_completed,
    spreadsheet_rerun_writeback_action_payload as _spreadsheet_rerun_writeback_action_payload,
    valid_spreadsheet_row_values as _valid_spreadsheet_row_values,
    wait_pending_command_status as _wait_pending_command_status,
)

__all__ = [name for name in globals() if not name.startswith("__")]
