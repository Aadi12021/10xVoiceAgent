import json
import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock

from webhook.main import app

client = TestClient(app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_webhook_rejects_wrong_secret():
    resp = client.post(
        "/webhook",
        json={"message": {"type": "end-of-call-report"}},
        headers={"x-vapi-secret": "wrong"},
    )
    assert resp.status_code == 401


def test_webhook_rejects_stale_timestamp():
    old_ts = str(time.time() - 400)  # 400 seconds ago — outside 5-minute replay window
    resp = client.post(
        "/webhook",
        json={"message": {"type": "status-update", "status": "in-progress"}},
        headers={"x-vapi-secret": "testsecret", "x-vapi-timestamp": old_ts},
    )
    assert resp.status_code == 401


def test_webhook_accepts_status_update_with_correct_secret():
    resp = client.post(
        "/webhook",
        json={"message": {"type": "status-update", "status": "in-progress"}},
        headers={"x-vapi-secret": "testsecret"},
    )
    assert resp.status_code == 200


def test_function_call_event_sends_sms_and_returns_result():
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "send_booking_link",
                "parameters": json.dumps({"phone_number": "+15551234567"}),
            },
            "call": {
                "id": "call-fn-test",
                "customer": {"number": "+15551234567"},
            },
        }
    }
    with patch("webhook.sms.twilio_client") as mock_twilio:
        mock_twilio.messages.create.return_value = MagicMock(sid="SM123")
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    assert resp.status_code == 200
    assert "sent you a text" in resp.json()["result"].lower()


def test_function_call_parameters_as_dict_also_works():
    """Vapi may send parameters as a parsed dict rather than a JSON string."""
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "send_booking_link",
                "parameters": {"phone_number": "+15559998888"},
            },
            "call": {
                "id": "call-dict-params",
                "customer": {"number": "+15559998888"},
            },
        }
    }
    with patch("webhook.sms.twilio_client") as mock_twilio:
        mock_twilio.messages.create.return_value = MagicMock(sid="SM456")
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    assert resp.status_code == 200
    assert "sent you a text" in resp.json()["result"].lower()


def test_capture_email_newsletter_handler():
    """capture_email with purpose=newsletter returns the 10X Briefs confirmation."""
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "capture_email",
                "parameters": {"email": "user@example.com", "purpose": "newsletter"},
            },
            "call": {"id": "call-email-test"},
        }
    }
    mock_ws = MagicMock()
    cell = MagicMock()
    cell.row = 2
    mock_ws.find.return_value = cell
    with patch("webhook.crm._get_worksheet", return_value=mock_ws):
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    assert resp.status_code == 200
    assert "10x briefs" in resp.json()["result"].lower()


def test_send_booking_link_no_phone_returns_escalation():
    """send_booking_link with no phone in params AND no call.customer returns graceful fallback."""
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "send_booking_link",
                "parameters": {},  # no phone_number key
            },
            # no customer number
            "call": {"id": "call-no-phone"},
        }
    }
    resp = client.post(
        "/webhook",
        json=payload,
        headers={"x-vapi-secret": "testsecret"},
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert "hello" in result.lower() or "team" in result.lower()


def test_malformed_json_parameters_handled_gracefully():
    """Vapi sending malformed JSON in parameters must not cause a 500 error."""
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "send_booking_link",
                "parameters": "{bad json}",
            },
            "call": {"id": "call-bad-params", "customer": {"number": "+15550000001"}},
        }
    }
    with patch("webhook.sms.twilio_client") as mock_twilio:
        mock_twilio.messages.create.return_value = MagicMock(sid="SM_BAD")
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    # Falls back to call.customer.number — should still send SMS successfully
    assert resp.status_code == 200
    assert "sent you a text" in resp.json()["result"].lower()


def test_unknown_function_name_returns_unknown():
    payload = {
        "message": {
            "type": "function-call",
            "functionCall": {
                "name": "not_a_real_function",
                "parameters": {},
            },
        }
    }
    resp = client.post(
        "/webhook",
        json=payload,
        headers={"x-vapi-secret": "testsecret"},
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == "Unknown function."


def test_end_of_call_warm_lead_accepted():
    payload = {
        "message": {
            "type": "end-of-call-report",
            "endedReason": "customer-ended-call",
            "call": {
                "id": "call-end-warm",
                "customer": {"number": "+15557778888"},
                "startedAt": "2026-06-23T14:00:00Z",
            },
            "transcript": "Alex: Hi...\nCaller: I'm a startup founder and I have a real problem with manual sales.",
            "summary": "Startup founder with manual sales process, wants AI automation.",
        }
    }
    mock_ws = MagicMock()
    mock_ws.append_row = MagicMock()
    with patch("webhook.crm._get_worksheet", return_value=mock_ws), \
         patch("smtplib.SMTP_SSL") as mock_ssl:
        mock_ssl.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ssl.return_value.__exit__ = MagicMock(return_value=False)
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
