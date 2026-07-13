import pytest
from unittest.mock import patch, MagicMock
from webhook.sms import send_booking_sms


def test_send_returns_true_on_success():
    mock_msg = MagicMock()
    mock_msg.sid = "SM123"
    with patch("webhook.sms.twilio_client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        result = send_booking_sms("+15551234567")
    assert result is True
    # Verify the body uses the env var value set in conftest.py
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert "https://calendar.google.com/test/booking" in call_kwargs["body"]
    assert call_kwargs["to"] == "+15551234567"
    assert call_kwargs["from_"] == "+15550001111"


def test_send_returns_false_on_twilio_error():
    with patch("webhook.sms.twilio_client") as mock_client:
        mock_client.messages.create.side_effect = Exception("Twilio error")
        result = send_booking_sms("+15551234567")
    assert result is False


def test_send_returns_false_for_empty_number():
    result = send_booking_sms("")
    assert result is False


def test_sms_body_reads_env_var_at_call_time(monkeypatch):
    """If BOOKING_URL changes between imports and calls, the SMS uses the current value."""
    monkeypatch.setenv("BOOKING_URL", "https://calendar.google.com/override/link")
    mock_msg = MagicMock()
    mock_msg.sid = "SM999"
    with patch("webhook.sms.twilio_client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        send_booking_sms("+15550000000")
    body = mock_client.messages.create.call_args.kwargs["body"]
    assert "https://calendar.google.com/override/link" in body


def test_10_digit_number_normalized_to_e164():
    mock_msg = MagicMock()
    mock_msg.sid = "SM_NORM"
    with patch("webhook.sms.twilio_client") as mock_client:
        mock_client.messages.create.return_value = mock_msg
        result = send_booking_sms("5551234567")  # 10-digit US number without country code
    assert result is True
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["to"] == "+15551234567"


def test_invalid_phone_number_returns_false_without_calling_twilio():
    with patch("webhook.sms.twilio_client") as mock_client:
        result = send_booking_sms("not-a-phone-number")
    assert result is False
    mock_client.messages.create.assert_not_called()


def test_sms_retries_once_on_transient_failure():
    """First Twilio attempt fails; second attempt succeeds. Returns True."""
    mock_msg = MagicMock()
    mock_msg.sid = "SM_RETRY"
    call_count = {"n": 0}

    def side_effect(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("temporary network error")
        return mock_msg

    with patch("webhook.sms.twilio_client") as mock_client:
        mock_client.messages.create.side_effect = side_effect
        result = send_booking_sms("+15551234567")
    assert result is True
    assert call_count["n"] == 2
