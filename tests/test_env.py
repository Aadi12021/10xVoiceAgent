import os
import pytest
from dotenv import load_dotenv


def test_required_env_vars_present():
    load_dotenv(".env")
    required = [
        "VAPI_API_KEY",
        "VAPI_PUBLIC_KEY",
        "ANTHROPIC_API_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_NUMBER",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
        "GOOGLE_SHEET_ID",
        "GMAIL_USER",
        "GMAIL_APP_PASSWORD",
        "BOOKING_URL",
        "WEBHOOK_SECRET",
    ]
    missing = [v for v in required if not os.getenv(v)]
    assert missing == [], f"Missing env vars: {missing}"
