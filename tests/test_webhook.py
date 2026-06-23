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
    with patch("webhook.crm.notion_client") as mock_notion, \
         patch("webhook.notifications.sendgrid_client") as mock_sg:
        mock_notion.pages.create = AsyncMock(return_value={"id": "page-new"})
        mock_sg.send.return_value = MagicMock(status_code=202)
        resp = client.post(
            "/webhook",
            json=payload,
            headers={"x-vapi-secret": "testsecret"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"
