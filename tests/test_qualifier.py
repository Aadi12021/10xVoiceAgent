import pytest
from webhook.qualifier import qualify_call


def test_founder_with_pain_point_is_warm_lead():
    result = qualify_call(
        transcript="Caller: I'm a founder and I need help with my sales process. It's completely manual right now.",
        summary="Founder with manual sales process seeking AI automation."
    )
    assert result["is_warm_lead"] is True
    assert result["is_newsletter"] is False
    assert result["segment"] == "business"


def test_student_routes_to_newsletter():
    result = qualify_call(
        transcript="Caller: I'm a student just learning about AI. I'm in high school.",
        summary="High school student exploring AI."
    )
    assert result["is_warm_lead"] is False
    assert result["is_newsletter"] is True
    assert result["segment"] == "student"


def test_pricing_question_is_warm_lead():
    result = qualify_call(
        transcript="Caller: How much do your services cost? What's the pricing?",
        summary="Caller asked about pricing."
    )
    assert result["is_warm_lead"] is True
    assert "pricing_inquiry" in result["qualification_signals"]


def test_timeline_mention_is_warm_lead():
    result = qualify_call(
        transcript="Caller: I want to start in Q3, we're planning to deploy AI this summer.",
        summary="Business owner wanting to start in Q3."
    )
    assert result["is_warm_lead"] is True
    assert "timeline" in result["qualification_signals"]


def test_early_researcher_routes_to_newsletter():
    result = qualify_call(
        transcript="Caller: I'm just exploring, learning about AI, not sure yet.",
        summary="Early-stage researcher exploring AI options."
    )
    assert result["is_warm_lead"] is False
    assert result["is_newsletter"] is True


def test_empty_call_is_unqualified():
    result = qualify_call(transcript="", summary="")
    assert result["is_warm_lead"] is False
    assert result["is_newsletter"] is False
    assert result["segment"] == "unknown"


def test_warm_signal_beats_newsletter_signal():
    """Caller is a student (newsletter) but mentions a timeline (warm). Warm wins."""
    result = qualify_call(
        transcript="Caller: I'm a student but I want to start the program this quarter. I have a deadline.",
        summary="Student with a timeline and budget urgency."
    )
    assert result["is_warm_lead"] is True
    assert result["is_newsletter"] is False


def test_parent_enrolling_child_is_warm_lead():
    result = qualify_call(
        transcript="Caller: My daughter wants to do the summer AI program. How much is it and when can she start?",
        summary="Parent asking about summer 2026 program pricing and enrollment."
    )
    assert result["is_warm_lead"] is True
    assert "pricing_inquiry" in result["qualification_signals"]


def test_negation_prevents_false_positive_warm_signal():
    """'I don't have a budget' must not trigger pricing_inquiry warm signal."""
    result = qualify_call(
        transcript="Caller: I don't have a budget for this right now. No specific timeline either.",
        summary="Caller stated no budget and no timeline."
    )
    assert result["is_warm_lead"] is False


def test_agent_booking_action_forces_warm_lead():
    """If Alex sent a booking link in the transcript, classify as warm lead regardless of caller signals."""
    result = qualify_call(
        transcript="Alex: I can send you a link to book a free 30-minute strategy call.\nCaller: Yes please.",
        summary="Agent offered and sent a booking link."
    )
    assert result["is_warm_lead"] is True
    assert "agent_booked" in result["qualification_signals"]


def test_agent_newsletter_action_forces_newsletter():
    """If Alex routed to newsletter in the transcript, classify as newsletter even without other signals."""
    result = qualify_call(
        transcript="Alex: I'll make sure the team adds you to the 10X Briefs. What's your email?\nCaller: Sure.",
        summary="Agent added caller to newsletter."
    )
    assert result["is_newsletter"] is True
    assert result["is_warm_lead"] is False


def test_vp_at_end_of_sentence_is_decision_maker():
    """'VP' with no following word (end of sentence) must still trigger decision_maker signal.
    Regression test for trailing-space bug in the regex: 'vp ' (with space) missed end-of-string VP.
    """
    result = qualify_call(
        transcript="Caller: I am a VP. We need help automating our sales pipeline.",
        summary="VP looking for sales automation."
    )
    assert result["is_warm_lead"] is True
    assert "decision_maker" in result["qualification_signals"]
