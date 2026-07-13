import os
import json
import logging
import time
from typing import Any
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from webhook.models import VapiWebhookPayload, VapiMessage, FunctionCallResult

load_dotenv()

logger = logging.getLogger(__name__)
app = FastAPI(title="10X AI Studio Voice Agent Webhook")


def _verify_secret(request: Request) -> None:
    # Read at request time so monkeypatched env vars work in tests
    secret = os.environ.get("WEBHOOK_SECRET", "")
    if request.headers.get("x-vapi-secret", "") != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    # Replay protection: reject requests with a timestamp older than 5 minutes.
    # Vapi sends x-vapi-timestamp (Unix epoch float). Skip check if header absent
    # (older Vapi versions may omit it) to avoid breaking existing integrations.
    ts_header = request.headers.get("x-vapi-timestamp", "")
    if ts_header:
        try:
            if abs(time.time() - float(ts_header)) > 300:
                raise HTTPException(status_code=401, detail="Webhook timestamp too old")
        except ValueError:
            pass  # unparseable timestamp — skip replay check rather than reject


def _parse_fn_params(raw: Any) -> dict:
    """Vapi sends function parameters as a JSON string or a parsed dict — handle both."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Malformed function parameters (not valid JSON): %r", raw)
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def handle_vapi_event(
    payload: VapiWebhookPayload,
    request: Request,
    background_tasks: BackgroundTasks,
):
    _verify_secret(request)
    msg = payload.message

    if msg.type == "function-call":
        return await _handle_function_call(msg)

    if msg.type == "end-of-call-report":
        background_tasks.add_task(_process_end_of_call, msg)
        return {"status": "accepted"}

    return {"status": "ok"}


async def _handle_function_call(msg: VapiMessage) -> dict:
    from webhook.sms import send_booking_sms
    from webhook.crm import log_email_capture

    fn = msg.functionCall
    if not fn:
        return FunctionCallResult(result="No function call data received.").model_dump()

    params = _parse_fn_params(fn.parameters)

    if fn.name == "send_booking_link":
        phone = params.get("phone_number") or (
            msg.call.customer.number
            if msg.call and msg.call.customer
            else None
        )
        if not phone:
            return FunctionCallResult(
                result="I wasn't able to get your phone number. I'll have the team reach out to you directly at hello at 10xaistudio dot com."
            ).model_dump()
        if send_booking_sms(phone):
            return FunctionCallResult(
                result="I've just sent you a text with the link to book your free 30-minute strategy call. It should arrive in the next few seconds."
            ).model_dump()
        return FunctionCallResult(
            result="I ran into a hiccup sending the link. The team will follow up at hello at 10xaistudio dot com to get you scheduled."
        ).model_dump()

    if fn.name == "capture_email":
        email = params.get("email", "")
        purpose = params.get("purpose", "newsletter")
        call_id = msg.call.id if msg.call else ""
        await log_email_capture(call_id=call_id, email=email, purpose=purpose)
        if purpose == "newsletter":
            return FunctionCallResult(
                result="Got it. The team will add you to The 10X Briefs. You will get your first issue within the next two weeks."
            ).model_dump()
        return FunctionCallResult(
            result="Got it. Someone from our team will reach out to you at that email to get your strategy call scheduled."
        ).model_dump()

    return FunctionCallResult(result="Unknown function.").model_dump()


async def _process_end_of_call(msg: VapiMessage) -> None:
    from webhook.qualifier import qualify_call
    from webhook.crm import log_call_to_sheets
    from webhook.notifications import notify_warm_lead

    qualification = qualify_call(
        transcript=msg.transcript or "",
        summary=msg.summary or "",
    )
    await log_call_to_sheets(msg, qualification)
    if qualification["is_warm_lead"]:
        await notify_warm_lead(msg, qualification)
