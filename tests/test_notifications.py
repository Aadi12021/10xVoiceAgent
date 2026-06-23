import pytest
from unittest.mock import patch, MagicMock
from webhook.models import VapiMessage, CallInfo, Customer

SAMPLE_MSG = VapiMessage(
    type="end-of-call-report",
    call=CallInfo(
        id="call-xyz",
        customer=Customer(number="+15559876543"),
        startedAt="2026-06-23T15:00:00Z",
    ),
    summary="Corporate team lead wants AI workflow automation to save 10 hours/week.",
    endedReason="customer-ended-call",
)

SAMPLE_Q = {
    "is_warm_lead": True,
    "is_newsletter": False,
    "qualification_signals": ["decision_maker", "timeline"],
    "segment": "corporate",
}


async def test_notify_warm_lead_calls_sendgrid():
    with patch("webhook.notifications.sendgrid_client") as mock_sg:
        mock_sg.send.return_value = MagicMock(status_code=202)
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)
    mock_sg.send.assert_called_once()
    mail = mock_sg.send.call_args.args[0]
    # SendGrid wraps subject and content in helper types — unwrap for assertions
    assert "Warm Lead" in str(mail.subject)
    assert "+15559876543" in mail.contents[0].content


async def test_notify_handles_sendgrid_error_without_raising(caplog):
    with patch("webhook.notifications.sendgrid_client") as mock_sg:
        mock_sg.send.side_effect = Exception("SendGrid down")
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)
    assert "Failed to send" in caplog.text


async def test_notify_includes_qualification_signals():
    with patch("webhook.notifications.sendgrid_client") as mock_sg:
        mock_sg.send.return_value = MagicMock(status_code=202)
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)
    mail = mock_sg.send.call_args.args[0]
    body = mail.contents[0].content
    assert "decision_maker" in body
    assert "timeline" in body
