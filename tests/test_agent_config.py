import json
import pytest


def test_agent_config_valid_json_with_required_fields():
    with open("vapi/agent_config.json") as f:
        config = json.load(f)
    assert config["model"]["provider"] == "anthropic"
    assert config["model"]["model"] == "claude-sonnet-4-6"
    assert config["model"]["maxTokens"] >= 200, "maxTokens too low — may truncate complex responses"
    assert config["voice"]["provider"] == "11labs"
    assert config["transcriber"]["provider"] == "deepgram"
    assert config["transcriber"]["model"] == "nova-2"
    assert len(config["model"]["systemPrompt"]) > 500


def test_agent_config_has_required_tools():
    with open("vapi/agent_config.json") as f:
        config = json.load(f)
    tool_names = [t["function"]["name"] for t in config.get("tools", [])]
    assert "send_booking_link" in tool_names
    assert "capture_email" in tool_names


def test_system_prompt_has_no_unfilled_brackets():
    with open("vapi/agent_config.json") as f:
        config = json.load(f)
    prompt = config["model"]["systemPrompt"]
    assert "[INSERT" not in prompt, "Unfilled placeholder in system prompt"
    assert "REPLACE_ME" not in prompt
    assert "9 2 9, 5 2 5, 4 4 9 5" in prompt, "Escalation phone number must be in system prompt (spaced for spoken delivery)"
    assert "UNCERTAINTY" in prompt, "Hallucination containment instruction missing"
    assert "80 words" in prompt, "Word limit should be 80 (raised from 60 for conversational depth)"
