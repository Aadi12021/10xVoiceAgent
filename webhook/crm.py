import asyncio
import os
import logging
from notion_client import AsyncClient
from webhook.models import VapiMessage

logger = logging.getLogger(__name__)

notion_client = AsyncClient(auth=os.environ.get("NOTION_TOKEN", ""))
_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

_MAX_TRANSCRIPT_CHARS = 6000   # 3 chunks × 2000 chars (Notion rich_text limit per block)
_CHUNK_SIZE = 2000


def _qualification_label(q: dict) -> str:
    if q["is_warm_lead"]:
        return "Warm Lead"
    if q["is_newsletter"]:
        return "Newsletter"
    return "Unqualified"


def _rich_text(value: str) -> list:
    """Split text into 2000-char blocks. Notion rejects text objects longer than 2000 chars."""
    value = (value or "")[:_MAX_TRANSCRIPT_CHARS]
    if not value:
        return [{"text": {"content": ""}}]
    return [
        {"text": {"content": value[i:i + _CHUNK_SIZE]}}
        for i in range(0, len(value), _CHUNK_SIZE)
    ]


def _short_text(value: str) -> list:
    """Single-block rich_text for short fields (summary, ended reason, call ID)."""
    return [{"text": {"content": (value or "")[:2000]}}]


async def log_call_to_notion(msg: VapiMessage, qualification: dict) -> None:
    phone = call_id = call_date = ""
    if msg.call:
        call_id = msg.call.id or ""
        call_date = msg.call.startedAt or ""
        if msg.call.customer:
            phone = msg.call.customer.number or ""

    properties = {
        "Name": {"title": _short_text(f"Call — {call_date or 'unknown'} — {phone or 'unknown'}")},
        "Phone": {"phone_number": phone or None},
        "Email": {"email": None},
        "Call Date": {"date": {"start": call_date}} if call_date else {"date": None},
        "Qualification": {"select": {"name": _qualification_label(qualification)}},
        "Segment": {"select": {"name": qualification.get("segment", "unknown")}},
        "Summary": {"rich_text": _short_text(msg.summary or "")},
        "Transcript": {"rich_text": _rich_text(msg.transcript or "")},
        "Recording URL": {"url": msg.recordingUrl or None},
        "Ended Reason": {"rich_text": _short_text(msg.endedReason or "")},
        "Call ID": {"rich_text": _short_text(call_id)},
    }

    try:
        await notion_client.pages.create(
            parent={"database_id": _DATABASE_ID},
            properties=properties,
        )
        logger.info("Call %s logged to Notion", call_id)
    except Exception as e:
        logger.error("Failed to log call %s to Notion: %s", call_id, e)


async def log_email_capture(call_id: str, email: str, purpose: str) -> None:
    """Find the Notion page for this call_id and add the email address to it.

    Retries up to 4 times with linear backoff (3s, 6s, 9s gaps) because this function
    fires during the call (from the capture_email function-call event), while the Notion
    page is not created until end-of-call-report fires after the call ends. Without retry,
    the page may not exist yet and the email is silently lost.
    """
    if not email:
        return
    for attempt in range(4):
        try:
            results = await notion_client.databases.query(
                database_id=_DATABASE_ID,
                filter={
                    "property": "Call ID",
                    "rich_text": {"equals": call_id},
                },
            )
            pages = results.get("results", [])
            if pages:
                page_id = pages[0]["id"]
                await notion_client.pages.update(
                    page_id=page_id,
                    properties={"Email": {"email": email}},
                )
                logger.info("Email %s captured for call %s (purpose: %s)", email, call_id, purpose)
                return
            if attempt < 3:
                wait = 3 * (attempt + 1)  # 3s, 6s, 9s
                logger.debug(
                    "Notion page not found for call %s — retrying in %ds (attempt %d/4)",
                    call_id, wait, attempt + 1,
                )
                await asyncio.sleep(wait)
        except Exception as e:
            logger.error("Failed to log email for call %s: %s", call_id, e)
            return
    logger.warning(
        "Email %s for call %s was not stored — Notion page not found after 4 attempts. "
        "Likely cause: end-of-call-report event never fired or failed to create the CRM record.",
        email, call_id,
    )
