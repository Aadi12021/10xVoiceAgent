#!/usr/bin/env python3
"""Update an existing Vapi assistant's serverUrl. Run after Railway deploy."""
import os
import sys
import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.environ["VAPI_API_KEY"]
VAPI_ASSISTANT_ID = os.environ.get("VAPI_ASSISTANT_ID", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
BASE_URL = "https://api.vapi.ai"


def update_server_url(assistant_id: str, server_url: str) -> None:
    resp = httpx.patch(
        f"{BASE_URL}/assistant/{assistant_id}",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        json={
            "serverUrl": server_url,
            "serverUrlSecret": WEBHOOK_SECRET,
        },
        timeout=30,
    )
    resp.raise_for_status()
    print(f"Updated assistant {assistant_id}")
    print(f"  serverUrl: {server_url}")
    print(f"  serverUrlSecret: {'set' if WEBHOOK_SECRET else 'NOT SET — check .env'}")


if __name__ == "__main__":
    if not VAPI_ASSISTANT_ID:
        print("ERROR: VAPI_ASSISTANT_ID not set in .env — run vapi/create_agent.py first")
        sys.exit(1)

    railway_url = input("Enter your Railway app URL (e.g. https://voice-agent.railway.app): ").strip()
    if not railway_url:
        print("Aborted.")
        sys.exit(1)

    server_url = f"{railway_url.rstrip('/')}/webhook"
    update_server_url(VAPI_ASSISTANT_ID, server_url)
