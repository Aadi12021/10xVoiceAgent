#!/usr/bin/env python3
"""One-shot script to create the Vapi assistant. Run once, save the returned ID to .env."""
import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.environ["VAPI_API_KEY"]
BASE_URL = "https://api.vapi.ai"


def create_assistant() -> dict:
    with open("vapi/agent_config.json") as f:
        config = json.load(f)
    resp = httpx.post(
        f"{BASE_URL}/assistant",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        json=config,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def claim_phone_number(assistant_id: str) -> dict:
    resp = httpx.post(
        f"{BASE_URL}/phone-number",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        json={
            "provider": "vapi",
            "assistantId": assistant_id,
            "name": "10X AI Studio Main Line",
            "numberDesiredAreaCode": "929",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print("Creating Vapi assistant...")
    assistant = create_assistant()
    assistant_id = assistant["id"]
    print(f"Assistant created: {assistant_id}")
    print(f"Add to .env:  VAPI_ASSISTANT_ID={assistant_id}")

    if input("\nClaim a US phone number now? (y/n): ").strip().lower() == "y":
        phone = claim_phone_number(assistant_id)
        print(f"Phone number: {phone.get('number', phone)}")
        print("Note: serverUrl is still a placeholder. Run vapi/update_agent.py after Task 9 deploy.")
