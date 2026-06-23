import re

_WARM_LEAD_PATTERNS = [
    (r"\b(founder|ceo|cto|coo|owner|executive|director|vp |vice president|team lead|manager)\b", "decision_maker"),
    (r"\b(pain point|problem|challenge|struggle|issue|bottleneck|inefficien|manual process|repetitive|slow)\b", "pain_point"),
    (r"\b(pricing|price|cost|how much|what do you charge|budget|what.s the investment|enroll|sign up for)\b", "pricing_inquiry"),
    (r"\b(get started|how to start|ready to|want to begin|move forward|next step|how do i join)\b", "ready_to_start"),
    (r"\b(q[1-4]|this quarter|this month|this year|this summer|next month|in \d+ weeks?|by (january|february|march|april|may|june|july|august|september|october|november|december))\b", "timeline"),
    (r"\b(specific (goal|problem|need|use case)|we need|my team needs|our company needs|trying to fix)\b", "specific_need"),
]

_NEWSLETTER_PATTERNS = [
    (r"\b(just learning|just starting|just exploring|early stage|not ready|not sure yet|doing research)\b", "early_researcher"),
    (r"\b(curious|exploring|looking around|just checking out|research phase|comparing options)\b", "researcher"),
]

# Agent-action patterns are high-confidence — they reflect what Alex actually did in the call,
# not what the caller said. Booking action → warm lead. Newsletter action → newsletter.
# These prevent drift between the agent's in-call routing and the backend qualifier.
_AGENT_ACTION_PATTERNS = [
    (r"\b(i can send you a link to book|sent you a text with the link|link to book a free 30.minute)\b", "agent_booked"),
    (r"\b(add you to the (list|10x briefs)|team adds you|the 10x briefs)\b", "agent_newslettered"),
]

_STUDENT_PATTERNS = [
    r"\b(student|high school|high schooler|college student|university student|grade \d+|grades? [0-9])\b",
]


def _has_negation_before(text: str, match: re.Match) -> bool:
    """Return True if a negation word appears in the 40 characters before the match start."""
    preceding = text[max(0, match.start() - 40):match.start()]
    return bool(re.search(r"\b(not|no|don't|doesn't|never|without|can't|won't|isn't|aren't|haven't)\b", preceding))


def _match_patterns(text: str, patterns: list) -> list:
    """Match patterns against lowercase text, skipping any match preceded by a negation word."""
    text_lower = text.lower()
    signals = []
    for pattern, label in patterns:
        m = re.search(pattern, text_lower)
        if m and not _has_negation_before(text_lower, m):
            signals.append(label)
    return signals


def _detect_segment(text: str) -> str:
    text_lower = text.lower()
    if any(re.search(p, text_lower) for p in _STUDENT_PATTERNS):
        return "student"
    if re.search(r"\b(startup|scaleup|small business|smb|sme|main street|my business|our business|company|firm|founder|ceo|cto|coo|owner|business owner)\b", text_lower):
        return "business"
    if re.search(r"\b(corporate|enterprise|large org|team of \d|employees|headcount)\b", text_lower):
        return "corporate"
    if re.search(r"\b(university|college|professor|learn|education|workshop|training)\b", text_lower):
        return "education"
    return "unknown"


def qualify_call(transcript: str, summary: str) -> dict:
    combined = f"{transcript} {summary}".strip()
    if not combined:
        return {
            "is_warm_lead": False,
            "is_newsletter": False,
            "qualification_signals": [],
            "segment": "unknown",
        }

    segment = _detect_segment(combined)

    # Check agent-action signals first — these are the most reliable indicators because they
    # reflect what Alex actually did in-call (booked vs. routed to newsletter), not what the
    # caller said. This eliminates drift between system-prompt routing logic and backend qualifier.
    agent_signals = _match_patterns(combined, _AGENT_ACTION_PATTERNS)
    if "agent_booked" in agent_signals:
        return {
            "is_warm_lead": True,
            "is_newsletter": False,
            "qualification_signals": agent_signals,
            "segment": segment,
        }

    warm_signals = _match_patterns(combined, _WARM_LEAD_PATTERNS)
    newsletter_signals = _match_patterns(combined, _NEWSLETTER_PATTERNS)

    is_warm_lead = len(warm_signals) > 0
    # Warm signals beat newsletter signals (a student who asks pricing → warm lead).
    # Agent newsletter action is also high-confidence even without other newsletter signals.
    is_newsletter = not is_warm_lead and (
        "agent_newslettered" in agent_signals
        or len(newsletter_signals) > 0
        or segment in ("student", "education")
    )

    return {
        "is_warm_lead": is_warm_lead,
        "is_newsletter": is_newsletter,
        "qualification_signals": warm_signals + agent_signals,
        "segment": segment,
    }
