import pytest
from unittest.mock import AsyncMock, patch, MagicMock
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


async def test_log_call_creates_notion_page():
    with patch("webhook.crm.notion_client") as mock_notion:
        mock_notion.pages.create = AsyncMock(return_value={"id": "page-123"})
        from webhook.crm import log_call_to_notion
        await log_call_to_notion(SAMPLE_MSG, SAMPLE_Q)

    mock_notion.pages.create.assert_called_once()
    props = mock_notion.pages.create.call_args.kwargs["properties"]
    assert props["Qualification"]["select"]["name"] == "Warm Lead"
    assert props["Segment"]["select"]["name"] == "business"
    assert props["Call ID"]["rich_text"][0]["text"]["content"] == "call-abc-123"


async def test_log_call_handles_notion_error_without_raising(caplog):
    with patch("webhook.crm.notion_client") as mock_notion:
        mock_notion.pages.create = AsyncMock(side_effect=Exception("Notion down"))
        from webhook.crm import log_call_to_notion
        await log_call_to_notion(SAMPLE_MSG, SAMPLE_Q)
    assert "Failed to log call" in caplog.text


async def test_transcript_longer_than_2000_chars_is_chunked():
    long_transcript = "Caller: " + ("word " * 500)  # ~2500 chars
    msg = VapiMessage(
        type="end-of-call-report",
        call=CallInfo(id="call-long"),
        transcript=long_transcript,
        summary="Long call.",
    )
    with patch("webhook.crm.notion_client") as mock_notion:
        mock_notion.pages.create = AsyncMock(return_value={"id": "page-long"})
        from webhook.crm import log_call_to_notion
        await log_call_to_notion(msg, SAMPLE_Q)

    props = mock_notion.pages.create.call_args.kwargs["properties"]
    transcript_blocks = props["Transcript"]["rich_text"]
    assert len(transcript_blocks) > 1, "Long transcript should be split into multiple text blocks"
    full_text = "".join(b["text"]["content"] for b in transcript_blocks)
    assert len(full_text) == min(len(long_transcript), 6000)


async def test_log_email_capture_updates_existing_record():
    with patch("webhook.crm.notion_client") as mock_notion:
        mock_notion.databases.query = AsyncMock(return_value={
            "results": [{"id": "page-abc-123"}]
        })
        mock_notion.pages.update = AsyncMock(return_value={"id": "page-abc-123"})
        from webhook.crm import log_email_capture
        await log_email_capture("call-abc-123", "test@example.com", "newsletter")

    mock_notion.pages.update.assert_called_once()
    update_kwargs = mock_notion.pages.update.call_args.kwargs
    assert update_kwargs["properties"]["Email"]["email"] == "test@example.com"


async def test_log_email_capture_retries_until_page_exists():
    """Race condition: email capture fires during the call, before end-of-call-report creates the page.
    The function must retry rather than silently dropping the email."""
    call_count = {"n": 0}

    async def mock_query(**kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            return {"results": []}  # first attempt: page not yet created
        return {"results": [{"id": "page-race"}]}

    with patch("webhook.crm.notion_client") as mock_notion, \
         patch("asyncio.sleep", new=AsyncMock()):  # don't actually sleep in tests
        mock_notion.databases.query = AsyncMock(side_effect=mock_query)
        mock_notion.pages.update = AsyncMock(return_value={"id": "page-race"})
        from webhook.crm import log_email_capture
        await log_email_capture("call-race", "retry@example.com", "newsletter")

    mock_notion.pages.update.assert_called_once()
    update_kwargs = mock_notion.pages.update.call_args.kwargs
    assert update_kwargs["properties"]["Email"]["email"] == "retry@example.com"
    assert call_count["n"] == 2  # first attempt missed, second found the page
