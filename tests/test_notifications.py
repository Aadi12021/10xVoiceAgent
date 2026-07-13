import base64
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


def _smtp_mock():
    mock_smtp = MagicMock()
    mock_ssl = MagicMock()
    mock_ssl.return_value.__enter__ = MagicMock(return_value=mock_smtp)
    mock_ssl.return_value.__exit__ = MagicMock(return_value=False)
    return mock_ssl, mock_smtp


async def test_notify_warm_lead_sends_gmail():
    mock_ssl, mock_smtp = _smtp_mock()
    with patch("smtplib.SMTP_SSL", mock_ssl):
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)

    mock_smtp.login.assert_called_once_with("hello@10xaistudio.com", "test-app-password")
    mock_smtp.send_message.assert_called_once()
    sent_msg = mock_smtp.send_message.call_args.args[0]
    assert "Warm Lead" in sent_msg["Subject"]
    assert "+15559876543" in sent_msg["Subject"]


async def test_notify_handles_smtp_error_without_raising(caplog):
    with patch("smtplib.SMTP_SSL", side_effect=Exception("Connection refused")):
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)
    assert "Failed to send" in caplog.text


async def test_notify_includes_qualification_signals():
    mock_ssl, mock_smtp = _smtp_mock()
    with patch("smtplib.SMTP_SSL", mock_ssl):
        from webhook.notifications import notify_warm_lead
        await notify_warm_lead(SAMPLE_MSG, SAMPLE_Q)

    sent_msg = mock_smtp.send_message.call_args.args[0]
    raw = sent_msg.get_payload()
    try:
        body = base64.b64decode(raw).decode()
    except Exception:
        body = raw
    assert "decision_maker" in body
    assert "timeline" in body
