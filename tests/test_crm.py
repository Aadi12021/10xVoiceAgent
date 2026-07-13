import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from webhook.models import VapiMessage, CallInfo, Customer

SAMPLE_MSG = VapiMessage(
    type="end-of-call-report",
    call=CallInfo(
        id="call-abc-123",
        customer=Customer(number="+15551234567"),
        startedAt="2026-06-23T14:00:00Z",
        endedAt="2026-06-23T14:03:30Z",
    ),
    transcript="Alex: Hi...\nCaller: I need help with sales.",
    summary="B2B startup founder seeking AI-powered sales automation.",
    recordingUrl="https://storage.vapi.ai/recording.mp3",
    endedReason="customer-ended-call",
)

SAMPLE_Q = {
    "is_warm_lead": True,
    "is_newsletter": False,
    "qualification_signals": ["decision_maker", "pain_point"],
    "segment": "business",
}


def _mock_worksheet():
    ws = MagicMock()
    ws.append_row = MagicMock()
    ws.find = MagicMock()
    ws.update_cell = MagicMock()
    return ws


async def test_log_call_appends_row_to_sheet():
    ws = _mock_worksheet()
    with patch("webhook.crm._get_worksheet", return_value=ws):
        from webhook.crm import log_call_to_sheets
        await log_call_to_sheets(SAMPLE_MSG, SAMPLE_Q)

    ws.append_row.assert_called_once()
    row = ws.append_row.call_args.args[0]
    assert row[0] == "call-abc-123"       # Call ID
    assert row[4] == "Warm Lead"           # Qualification
    assert row[5] == "business"            # Segment
    assert row[2] == "+15551234567"        # Phone


async def test_log_call_handles_sheets_error_without_raising(caplog):
    with patch("webhook.crm._get_worksheet", side_effect=Exception("Sheets down")):
        from webhook.crm import log_call_to_sheets
        await log_call_to_sheets(SAMPLE_MSG, SAMPLE_Q)
    assert "Failed to log call" in caplog.text


async def test_transcript_truncated_to_max_chars():
    long_transcript = "word " * 1200  # 6000 chars
    msg = VapiMessage(
        type="end-of-call-report",
        call=CallInfo(id="call-long"),
        transcript=long_transcript,
        summary="Long call.",
    )
    ws = _mock_worksheet()
    with patch("webhook.crm._get_worksheet", return_value=ws):
        from webhook.crm import log_call_to_sheets
        await log_call_to_sheets(msg, SAMPLE_Q)

    row = ws.append_row.call_args.args[0]
    transcript_cell = row[7]  # Transcript column
    assert len(transcript_cell) <= 5000


async def test_log_email_capture_updates_existing_row():
    ws = _mock_worksheet()
    cell = MagicMock()
    cell.row = 3
    ws.find.return_value = cell

    with patch("webhook.crm._get_worksheet", return_value=ws):
        from webhook.crm import log_email_capture
        await log_email_capture("call-abc-123", "test@example.com", "newsletter")

    ws.find.assert_called_once_with("call-abc-123", in_column=1)
    ws.update_cell.assert_called_once_with(3, 4, "test@example.com")


async def test_log_email_capture_retries_until_row_exists():
    """Race condition: email capture fires before end-of-call-report writes the row."""
    call_count = {"n": 0}
    cell = MagicMock()
    cell.row = 5

    def mock_find(value, in_column):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise Exception("CellNotFound")
        return cell

    ws = _mock_worksheet()
    ws.find.side_effect = mock_find

    with patch("webhook.crm._get_worksheet", return_value=ws), \
         patch("asyncio.sleep", new=AsyncMock()):
        from webhook.crm import log_email_capture
        await log_email_capture("call-race", "retry@example.com", "newsletter")

    ws.update_cell.assert_called_once_with(5, 4, "retry@example.com")
    assert call_count["n"] == 2


async def test_log_email_capture_retries_on_sheets_api_error(caplog):
    """Transient API error must not silently drop the email — must continue retrying."""
    call_count = {"n": 0}
    cell = MagicMock()
    cell.row = 7

    def mock_find(value, in_column):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise Exception("503 Service Unavailable")
        return cell

    ws = _mock_worksheet()
    ws.find.side_effect = mock_find

    with patch("webhook.crm._get_worksheet", return_value=ws), \
         patch("asyncio.sleep", new=AsyncMock()):
        from webhook.crm import log_email_capture
        await log_email_capture("call-transient", "transient@example.com", "newsletter")

    ws.update_cell.assert_called_once_with(7, 4, "transient@example.com")
    assert call_count["n"] == 2
