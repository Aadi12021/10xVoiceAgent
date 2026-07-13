import asyncio
import json
import os
import logging
from webhook.models import VapiMessage

logger = logging.getLogger(__name__)

# Lazy init — avoids credential error at import time before env vars are injected in tests
_sheets_client = None

_HEADERS = [
    "Call ID", "Call Date", "Phone", "Email",
    "Qualification", "Segment", "Summary",
    "Transcript", "Recording URL", "Ended Reason",
]
_COL_CALL_ID = 1   # A
_COL_EMAIL   = 4   # D  (must match _HEADERS order above)

_MAX_TRANSCRIPT_CHARS = 5000  # Google Sheets cell limit is ~50k chars, but keep it readable


def _init_client():
    global _sheets_client
    if _sheets_client is None:
        import gspread
        from google.oauth2.service_account import Credentials
        creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
        creds = Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _sheets_client = gspread.authorize(creds)


def _get_worksheet():
    _init_client()
    sheet = _sheets_client.open_by_key(os.environ.get("GOOGLE_SHEET_ID", ""))
    return sheet.sheet1


def _qualification_label(q: dict) -> str:
    if q["is_warm_lead"]:
        return "Warm Lead"
    if q["is_newsletter"]:
        return "Newsletter"
    return "Unqualified"


def _append_row_sync(msg: VapiMessage, qualification: dict) -> None:
    phone = call_id = call_date = ""
    if msg.call:
        call_id = msg.call.id or ""
        call_date = msg.call.startedAt or ""
        if msg.call.customer:
            phone = msg.call.customer.number or ""

    row = [
        call_id,
        call_date,
        phone,
        "",  # Email — populated later by log_email_capture
        _qualification_label(qualification),
        qualification.get("segment", "unknown"),
        (msg.summary or "")[:500],
        (msg.transcript or "")[:_MAX_TRANSCRIPT_CHARS],
        msg.recordingUrl or "",
        msg.endedReason or "",
    ]
    ws = _get_worksheet()
    ws.append_row(row, value_input_option="USER_ENTERED")


def _find_and_update_email_sync(call_id: str, email: str) -> bool:
    """Find the row with this call_id and write the email. Returns True if found.

    gspread v6: find() returns None when not found (does not raise CellNotFound).
    """
    ws = _get_worksheet()
    cell = ws.find(call_id, in_column=_COL_CALL_ID)
    if cell is None:
        return False
    ws.update_cell(cell.row, _COL_EMAIL, email)
    return True


async def log_call_to_sheets(msg: VapiMessage, qualification: dict) -> None:
    try:
        await asyncio.to_thread(_append_row_sync, msg, qualification)
        logger.info("Call %s logged to Google Sheets", msg.call.id if msg.call else "unknown")
    except Exception as e:
        logger.error("Failed to log call to Google Sheets: %s", e)


async def log_email_capture(call_id: str, email: str, purpose: str) -> None:
    """Write the caller's email into the row for this call_id.

    Retries up to 4 times with linear backoff because capture_email fires during the call
    while the row isn't written until end-of-call-report fires after hang-up.
    """
    if not email:
        return
    if not call_id:
        logger.warning("Cannot store email %s — call_id is empty (web widget session?)", email)
        return
    for attempt in range(4):
        try:
            found = await asyncio.to_thread(_find_and_update_email_sync, call_id, email)
            if found:
                logger.info("Email %s captured for call %s (purpose: %s)", email, call_id, purpose)
                return
            if attempt < 3:
                wait = 3 * (attempt + 1)
                logger.debug(
                    "Row not found for call %s — retrying in %ds (attempt %d/4)",
                    call_id, wait, attempt + 1,
                )
                await asyncio.sleep(wait)
        except Exception as e:
            logger.error("Failed to log email for call %s (attempt %d/4): %s", call_id, attempt + 1, e)
            if attempt < 3:
                await asyncio.sleep(3 * (attempt + 1))
            continue
    logger.warning(
        "Email %s for call %s was not stored after 4 attempts — row may not exist yet.",
        email, call_id,
    )
