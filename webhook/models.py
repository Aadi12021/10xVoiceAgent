from pydantic import BaseModel
from typing import Optional, Any


class Customer(BaseModel):
    number: Optional[str] = None
    name: Optional[str] = None


class CallInfo(BaseModel):
    id: Optional[str] = None
    customer: Optional[Customer] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None


class FunctionCallDetails(BaseModel):
    name: str
    parameters: Any  # str (JSON) or dict — Vapi format varies by version


class VapiMessage(BaseModel):
    type: str
    call: Optional[CallInfo] = None
    functionCall: Optional[FunctionCallDetails] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    recordingUrl: Optional[str] = None
    endedReason: Optional[str] = None


class VapiWebhookPayload(BaseModel):
    message: VapiMessage


class FunctionCallResult(BaseModel):
    result: str
