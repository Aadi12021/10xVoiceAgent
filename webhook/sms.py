import os
import re
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

twilio_client = Client(
    os.environ.get("TWILIO_ACCOUNT_SID", ""),
    os.environ.get("TWILIO_AUTH_TOKEN", ""),
)


def _normalize_phone(phone: str) -> str:
    """Normalize to E.164. Returns empty string if the number is not recognizably valid."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if phone.startswith("+") and 7 <= len(digits) <= 15:
        return f"+{digits}"  # international — pass through if plausibly valid
    return ""


def send_booking_sms(phone_number: str) -> bool:
    normalized = _normalize_phone(phone_number)
    if not normalized:
        logger.warning("Skipping SMS — invalid or empty phone number: %r", phone_number)
        return False
    booking_url = os.environ.get("CALENDLY_BOOKING_URL", "")
    from_number = os.environ.get("TWILIO_FROM_NUMBER", "")  # read at call time
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
