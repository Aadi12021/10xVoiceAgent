import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from webhook.models import VapiMessage

logger = logging.getLogger(__name__)

sendgrid_client = SendGridAPIClient(api_key=os.environ.get("SENDGRID_API_KEY", ""))

_NOTIFY_EMAIL = "hello@10xaistudio.com"
_FROM_EMAIL = "hello@10xaistudio.com"


def _build_body(msg: VapiMessage, qualification: dict) -> str:
    phone = call_date = ""
    if msg.call:
        call_date = msg.call.startedAt or ""
        if msg.call.customer:
            phone = msg.call.customer.number or ""

    signals = ", ".join(qualification.get("qualification_signals", [])) or "none detected"
    return (
        f"A warm lead call just completed on the 10X AI Studio voice agent.\n\n"
        f"Phone: {phone or 'Not captured'}\n"
        f"Call Date: {call_date}\n"
        f"Segment: {qualification.get('segment', 'unknown')}\n"
        f"Qualification Signals: {signals}\n\n"
        f"Summary:\n{msg.summary or 'No summary available.'}\n\n"
        f"Recording: {msg.recordingUrl or 'Not available'}\n\n"
        f"Reply to this email or call {phone} to follow up.\n"
        f"— Alex (10X AI Studio Voice Agent)"
    )


async def notify_warm_lead(msg: VapiMessage, qualification: dict) -> None:
    phone = ""
    if msg.call and msg.call.customer:
        phone = msg.call.customer.number or ""

    subject = f"Warm Lead: {phone or 'Unknown'} — Strategy Call Opportunity"
    body = _build_body(msg, qualification)
    email = Mail(
        from_email=_FROM_EMAIL,
        to_emails=To(_NOTIFY_EMAIL),
        subject=subject,
        plain_text_content=body,
    )
    try:
        resp = sendgrid_client.send(email)
        logger.info("Lead notification sent (status %s) for %s", resp.status_code, phone)
    except Exception as e:
        logger.error("Failed to send lead notification for %s: %s", phone, e)
