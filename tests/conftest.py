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
    monkeypatch.setenv("CALENDLY_BOOKING_URL", "https://calendly.com/test/strategy-call")
    monkeypatch.setenv("NOTION_TOKEN", "secret_testtoken")
    monkeypatch.setenv("NOTION_DATABASE_ID", "test-db-id-00000000")
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.testkey123")
