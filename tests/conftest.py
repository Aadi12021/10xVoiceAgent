import os
import pytest


@pytest.fixture(autouse=True)
def test_env_vars(monkeypatch):
    """Set all required env vars for every test. monkeypatch resets them after each test."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("VAPI_API_KEY", "test-vapi-key")
    monkeypatch.setenv("VAPI_PUBLIC_KEY", "test-vapi-public-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "ACtest123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "authtest456")
    monkeypatch.setenv("TWILIO_FROM_NUMBER", "+15550001111")
    monkeypatch.setenv("BOOKING_URL", "https://calendar.google.com/test/booking")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("GOOGLE_SHEET_ID", "test-sheet-id-000")
    monkeypatch.setenv("GMAIL_USER", "hello@10xaistudio.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-app-password")
