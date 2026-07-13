import os
import re
import logging

logger = logging.getLogger(__name__)

twilio_client = None  # lazy init — avoids credential check at import time


def _init_client():
    global twilio_client
    if twilio_client is None:
        from twilio.rest import Client
        twilio_client = Client(
            os.environ.get("TWILIO_ACCOUNT_SID", ""),
            os.environ.get("TWILIO_AUTH_TOKEN", ""),
        )


def _normalize_phone(phone: str) -> str:
    """Normalize to E.164. Returns empty string if the number is not recognizably valid."""
    if not phone:
        return ""
    # Check for explicit + prefix first — must not be overridden by the digit-count checks below.
    # e.g. +9876543210 strips to 10 digits and would incorrectly hit the 10-digit → +1 branch.
    if phone.startswith("+"):
        digits = re.sub(r"\D", "", phone)
        return f"+{digits}" if 7 <= len(digits) <= 15 else ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return ""


def send_booking_sms(phone_number: str) -> bool:
    normalized = _normalize_phone(phone_number)
    if not normalized:
        logger.warning("Skipping SMS — invalid or empty phone number: %r", phone_number)
        return False

    booking_url = os.environ.get("BOOKING_URL", "")
    if not booking_url:
        logger.error("BOOKING_URL is not set — SMS would contain no link. Aborting.")
        return False

    _init_client()

    from_number = os.environ.get("TWILIO_FROM_NUMBER", "")
    sms_body = (
        f"Hi! Here's your link to book a free 30-minute strategy call with "
        f"10X AI Studio: {booking_url} — We look forward to talking with you."
    )
    for attempt in range(2):
        try:
            message = twilio_client.messages.create(
                to=normalized,
                from_=from_number,
                body=sms_body,
            )
            logger.info("Booking SMS sent: %s to %s", message.sid, normalized)
            return True
        except Exception as e:
            if attempt == 0:
                logger.warning("SMS attempt 1 failed for %s: %s — retrying", normalized, e)
            else:
                logger.error("Failed to send booking SMS to %s after 2 attempts: %s", normalized, e)
    return False
