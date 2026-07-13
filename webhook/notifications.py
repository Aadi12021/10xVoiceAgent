import asyncio
import os
import logging
import smtplib
from email.mime.text import MIMEText
from webhook.models import VapiMessage

logger = logging.getLogger(__name__)

_NOTIFY_EMAIL = "hello@10xaistudio.com"


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
        f"--- Alex (10X AI Studio Voice Agent)"
    )


def _send_gmail_sync(subject: str, body: str) -> None:
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    # utf-8 charset handles em-dashes and any non-ASCII in transcripts/summaries.
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = _NOTIFY_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_password)
        smtp.send_message(msg)


async def notify_warm_lead(msg: VapiMessage, qualification: dict) -> None:
    phone = ""
    if msg.call and msg.call.customer:
        phone = msg.call.customer.number or ""

    subject = f"Warm Lead: {phone or 'Unknown'} — Strategy Call Opportunity"
    body = _build_body(msg, qualification)
    try:
        await asyncio.to_thread(_send_gmail_sync, subject, body)
        logger.info("Lead notification sent for %s", phone)
    except Exception as e:
        logger.error("Failed to send lead notification for %s: %s", phone, e)
