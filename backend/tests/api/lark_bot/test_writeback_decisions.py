# ruff: noqa: F403,F405
from tests.api.lark_bot.common import *


def test_lark_bot_completion_notification_writeback_link_confirms_and_writes(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    _mark_auto_closure_completed(job_id)
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-1",
        sheet_id="sheet-1",
        row_id="row-42",
        case_id="handwrite233",
        job_id=job_id,
    )
    unique = uuid4().hex
    draft = routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这个表格",
        input_source="https://example.com/a.png",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="把 8 识别成 3",
        attachments=[
            {
                "type": "link_context",
                "link_type": "lark_sheet",
                "token": "spreadsheet-1",
                "sheet_id": "sheet-1",
                "selected_row": "row-42",
            }
        ],
        submitted_case_id="handwrite233",
        submitted_job_id=job_id,
    )

    notification_response = client.get("/api/lark/bot/badcase-drafts/completion-notifications")

    assert notification_response.status_code == 200
    notifications = notification_response.json()["notifications"]
    notification = next(
        item for item in notifications if item["draft"]["draft_id"] == draft.draft_id
    )
    markdown = notification["payload"]["markdown"]
    assert "表格写回：待确认" in markdown
    writeback_url = markdown.split("写回确认：", 1)[1].splitlines()[0]
    parsed = urlparse(writeback_url)
    query = parse_qs(parsed.query)

    page = client.get(parsed.path, params={key: values[0] for key, values in query.items()})
    assert page.status_code == 200
    assert "确认写回原表格" in page.text

    written = client.post(parsed.path, params={key: values[0] for key, values in query.items()})
    assert written.status_code == 200
    assert "已写回原表格" in written.text
    assert writeback_client.update_count == 1
    assert writeback_client.spreadsheet_id == "spreadsheet-1"
    assert writeback_client.sheet_id == "sheet-1"
    assert writeback_client.row_id == "row-42"
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"


def test_lark_bot_writeback_link_configures_client_from_saved_sheet_mapping(monkeypatch) -> None:
    client = TestClient(app)
    writeback_client = RecordingWritebackClient()
    configured: list[tuple[str, str]] = []

    def fake_configure(settings) -> None:
        assert settings.reference is not None
        configured.append((settings.reference.spreadsheet_id, settings.reference.sheet_id))
        monkeypatch.setattr(routes, "spreadsheet_writeback_client", writeback_client, raising=False)

    monkeypatch.setattr(routes, "spreadsheet_writeback_client", None, raising=False)
    monkeypatch.setattr(routes, "configure_spreadsheet_clients", fake_configure)
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    routes.job_repository.save_spreadsheet_row_mapping(
        spreadsheet_id="spreadsheet-from-draft",
        sheet_id="sheet-from-draft",
        row_id="43",
        case_id="handwrite233",
        job_id=job_id,
    )
    unique = uuid4().hex
    draft = routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这个表格",
        input_source="https://example.com/a.png",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="把 8 识别成 3",
        attachments=[
            {
                "type": "link_context",
                "link_type": "lark_sheet",
                "token": "spreadsheet-from-draft",
                "sheet_id": "sheet-from-draft",
                "selected_row": "43",
            }
        ],
        submitted_case_id="handwrite233",
        submitted_job_id=job_id,
    )
    payload = routes._lark_bot_completion_notification_for_draft(
        draft=draft,
        job=routes.job_repository.get_job(job_id),
    ).payload
    writeback_url = payload.markdown.split("写回确认：", 1)[1].splitlines()[0]
    parsed = urlparse(writeback_url)
    query = parse_qs(parsed.query)

    written = client.post(parsed.path, params={key: values[0] for key, values in query.items()})

    assert written.status_code == 200
    assert configured == [("spreadsheet-from-draft", "sheet-from-draft")]
    assert writeback_client.update_count == 1
    assert writeback_client.spreadsheet_id == "spreadsheet-from-draft"
    assert writeback_client.sheet_id == "sheet-from-draft"
    assert writeback_client.row_id == "43"


def test_lark_bot_base_writeback_requires_confirmation_and_calls_connector(monkeypatch) -> None:
    client = TestClient(app)
    base_connector = RecordingBaseConnector()
    monkeypatch.setattr(
        routes, "_lark_bot_base_write_connector", lambda actor: base_connector, raising=False
    )
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    report_url = f"https://debug-agent.example/jobs/{job_id}/report"
    unique = uuid4().hex
    routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这条 Base 记录",
        input_source="https://example.com/a.png",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="把 8 识别成 3",
        attachments=[
            {
                "type": "link_context",
                "link_type": "lark_base",
                "token": "base-1",
                "table_id": "tbl-1",
                "selected_record": "rec-42",
            }
        ],
        submitted_case_id="handwrite233",
        submitted_job_id=job_id,
    )

    blocked = client.post(
        f"/api/jobs/{job_id}/base-writeback",
        json={"report_url": report_url, "require_confirmation": True, "actor": f"ou_{unique}"},
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["type"] == "lark_write_confirmation_required"
    confirmation_response = client.post(
        f"/api/jobs/{job_id}/base-writeback/confirmation",
        json={"report_url": report_url, "actor": f"ou_{unique}"},
    )
    assert confirmation_response.status_code == 200
    confirmation = confirmation_response.json()
    assert confirmation["service"] == "base"
    assert confirmation["operation"] == "+record-upsert"
    assert confirmation["required_scopes"] == ["bitable:app"]
    confirm_response = client.post(
        f"/api/lark/write-confirmations/{confirmation['confirmation_id']}/confirm",
        json={"actor": f"ou_{unique}"},
    )
    assert confirm_response.status_code == 200

    written = client.post(
        f"/api/jobs/{job_id}/base-writeback",
        json={
            "report_url": report_url,
            "require_confirmation": True,
            "confirmation_id": confirmation["confirmation_id"],
            "actor": f"ou_{unique}",
        },
    )

    assert written.status_code == 200
    body = written.json()
    assert body["base_token"] == "base-1"
    assert body["table_id"] == "tbl-1"
    assert body["record_id"] == "rec-42"
    assert base_connector.run_count == 1
    assert base_connector.args[:2] == ["base", "+record-upsert"]
    assert base_connector.args[base_connector.args.index("--base-token") + 1] == "base-1"
    assert base_connector.args[base_connector.args.index("--table-id") + 1] == "tbl-1"
    assert base_connector.args[base_connector.args.index("--record-id") + 1] == "rec-42"
    assert base_connector.payload["分析报告链接"] == report_url
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "rec-42"


def test_lark_bot_completion_notification_base_writeback_link_confirms_and_writes(
    monkeypatch,
) -> None:
    client = TestClient(app)
    base_connector = RecordingBaseConnector()
    monkeypatch.setattr(
        routes, "_lark_bot_base_write_connector", lambda actor: base_connector, raising=False
    )
    submit_response = client.post("/cases/handwrite233/debug-jobs?auto_run=true&baseline_trials=5")
    assert submit_response.status_code == 202
    job_id = submit_response.json()["job_id"]
    _mark_auto_closure_completed(job_id)
    unique = uuid4().hex
    draft = routes.job_repository.save_lark_bot_badcase_draft(
        draft_id=str(uuid4()),
        actor=f"ou_{unique}",
        open_id=f"ou_{unique}",
        chat_id=f"oc_{unique}",
        message_id=f"om_{unique}",
        status="submitted",
        source_text="小D，帮我调试这条 Base 记录",
        input_source="https://example.com/a.png",
        model_output='{"answer":"3"}',
        expected_output='{"answer":"8"}',
        issue_summary="把 8 识别成 3",
        attachments=[
            {
                "type": "link_context",
                "link_type": "lark_base",
                "token": "base-1",
                "table_id": "tbl-1",
                "selected_record": "rec-42",
            }
        ],
        submitted_case_id="handwrite233",
        submitted_job_id=job_id,
    )

    notification_response = client.get("/api/lark/bot/badcase-drafts/completion-notifications")

    assert notification_response.status_code == 200
    notifications = notification_response.json()["notifications"]
    notification = next(
        item for item in notifications if item["draft"]["draft_id"] == draft.draft_id
    )
    markdown = notification["payload"]["markdown"]
    assert "Base 写回：待确认" in markdown
    writeback_url = markdown.split("Base 写回确认：", 1)[1].splitlines()[0]
    parsed = urlparse(writeback_url)
    query = parse_qs(parsed.query)

    page = client.get(parsed.path, params={key: values[0] for key, values in query.items()})
    assert page.status_code == 200
    assert "确认写回 Base 记录" in page.text

    written = client.post(parsed.path, params={key: values[0] for key, values in query.items()})
    assert written.status_code == 200
    assert "已写回 Base 记录" in written.text
    assert base_connector.run_count == 1
    assert base_connector.args[:2] == ["base", "+record-upsert"]
    assert base_connector.args[base_connector.args.index("--record-id") + 1] == "rec-42"
    assert base_connector.payload["分析报告链接"].endswith(f"/jobs/{job_id}/report")
    audit = routes.job_repository.get_spreadsheet_writeback_audit(job_id)
    assert audit is not None
    assert audit.status == "succeeded"
    assert audit.row_id == "rec-42"
