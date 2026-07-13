import asyncio
import json
import os
import logging
from webhook.models import VapiMessage

logger = logging.getLogger(__name__)

_sheets_client = None   # lazy init — avoids credential error at import time
_worksheet = None       # cached worksheet reference — avoids open_by_key() on every call

_HEADERS = [
    "Call ID", "Call Date", "Phone", "Email",
    "Qualification", "Segment", "Summary",
    "Transcript", "Recording URL", "Ended Reason",
]
# Derived from _HEADERS so they stay correct if columns are reordered.
_COL_CALL_ID = _HEADERS.index("Call ID") + 1   # 1-indexed for gspread
_COL_EMAIL   = _HEADERS.index("Email") + 1

_MAX_TRANSCRIPT_CHARS = 5000


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
    global _worksheet
    if _worksheet is None:
        _init_client()
        sheet = _sheets_client.open_by_key(os.environ.get("GOOGLE_SHEET_ID", ""))
        _worksheet = sheet.sheet1
    return _worksheet


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
    # RAW prevents Google Sheets from interpreting cell values as formulas,
    # which would execute arbitrary code if a caller dictates "=IMPORTDATA(...)".
    ws.append_row(row, value_input_option="RAW")


def _find_and_update_email_sync(call_id: str, email: str) -> bool:
    """Find the row for this call_id and write the email. Returns True if found.

    gspread v6: find() returns None when not found (does not raise).
    Uses RAW input to prevent formula injection.
    """
    ws = _get_worksheet()
    cell = ws.find(call_id, in_column=_COL_CALL_ID)
    if cell is None:
        return False
    # update() with RAW prevents formula injection from caller-provided email values
    col_letter = chr(ord("A") + _COL_EMAIL - 1)
    ws.update(f"{col_letter}{cell.row}", [[email]], value_input_option="RAW")
    return True


async def log_call_to_sheets(msg: VapiMessage, qualification: dict) -> None:
    for attempt in range(3):
        try:
            await asyncio.to_thread(_append_row_sync, msg, qualification)
            logger.info("Call %s logged to Google Sheets", msg.call.id if msg.call else "unknown")
            return
        except Exception as e:
            if attempt < 2:
                wait = 2 ** attempt * 2  # 2s, 4s
                logger.warning("Sheets write failed (attempt %d/3): %s — retrying in %ds", attempt + 1, e, wait)
                await asyncio.sleep(wait)
            else:
                logger.error("Failed to log call to Google Sheets after 3 attempts: %s", e)


async def log_email_capture(call_id: str, email: str, purpose: str) -> None:
    """Write the caller's email into the row for this call_id.

    Must run as a background task — the row is written by end-of-call-report
    which fires after hang-up, while capture_email fires during the call.
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
