# QA Test Scripts — Alex, 10X AI Studio Voice Agent

Call via the Vapi phone number OR the web widget on 10xaistudio.com.
Target: 12+ calls before launch. Complete all 12 scenarios.

---

## Scenario 1: Startup Founder → Warm Lead → SMS Booking Link

**Say:** "I run a B2B software startup. Just me and two others. I need help with AI for sales."
When asked: confirm you're the founder, say you want to start this quarter, say yes to SMS link.

**Pass criteria:**
- [ ] Agent greets as Alex without filler words
- [ ] Agent asks 1-2 discovery questions (not 5 at once)
- [ ] Agent offers strategy call within 2-3 turns
- [ ] Agent asks if you can receive a text before sending link
- [ ] SMS arrives on test phone within 30 seconds with Calendly URL
- [ ] Notion: Qualification = "Warm Lead", Segment = "business"
- [ ] hello@10xaistudio.com receives email alert with qualification signals

---

## Scenario 2: High School Student → Newsletter → Email Capture

**Say:** "I heard you have a summer AI program for high schoolers."
Say you're a student, not ready to buy, but want to stay in touch.

**Pass criteria:**
- [ ] Agent mentions July 11 start, 25 seats, $499, 5-6 weeks, no coding required
- [ ] Agent offers The 10X Briefs newsletter (not strategy call)
- [ ] Agent asks for email address to add you to the list
- [ ] Notion: Qualification = "Newsletter", Segment = "student", Email field populated

---

## Scenario 3: Parent Enrolling Child → Warm Lead

**Say:** "My daughter is interested in your summer AI program. How much is it and when does it start?"

**Pass criteria:**
- [ ] Agent describes program details correctly (July 11, $499, 5-6 weeks)
- [ ] Agent treats parent as a warm lead (not student) because they are asking about pricing
- [ ] Agent offers strategy call or direct contact to enroll
- [ ] Notion: Qualification = "Warm Lead"

---

## Scenario 4: Skeptical Caller → Pain Point → Warm Lead

**Say:** "I've tried ChatGPT and honestly it felt overhyped."
When probed: "It just gave generic answers, nothing specific to my business."
Then reveal: "I'm a COO. I need to fix our order processing — it takes forever."

**Pass criteria:**
- [ ] Agent validates concern without over-apologizing
- [ ] Agent references "experience compounds, hype does not"
- [ ] Agent recognizes COO + specific pain and offers strategy call
- [ ] Notion: Qualification = "Warm Lead", Segment = "corporate"

---

## Scenario 5: Out-of-Scope Question

**Say:** "Can you help me build a personal budgeting app?"

**Pass criteria:**
- [ ] Agent says "That's a bit outside what I cover here"
- [ ] Agent redirects to AI for business or learning
- [ ] Agent does NOT attempt to answer the off-topic question

---

## Scenario 6: Request to Speak to a Human

**Say:** "I'd like to speak to a real person please."

**Pass criteria:**
- [ ] Agent gives escalation response referencing hello@10xaistudio.com
- [ ] Agent says the phone number by spacing digits: "9 2 9, 5 2 5, 4 4 9 5"
- [ ] Agent does NOT read the email address letter-by-letter as a URL
- [ ] Agent confirms next steps before ending call

---

## Scenario 7: Silence After Opening Question

After Alex's opening question, stay completely silent for 8 seconds.

**Pass criteria:**
- [ ] Agent uses silence handler: "Happy to take this at whatever pace works for you..."
- [ ] Agent does NOT repeat the identical opening question

---

## Scenario 8: Enterprise / Complex Scenario → Escalation

**Say:** "We're a 5,000-person company with SOC2 compliance requirements. We need AI across 12 internal systems."

**Pass criteria:**
- [ ] Agent recognizes complexity and escalates
- [ ] Agent references hello@10xaistudio.com and gives the phone number spaced
- [ ] Notion: call logged (any qualification status acceptable)

---

## Scenario 9: Pricing Question → Strategy Call Routing

**Say:** "How much do your services cost? I want a ballpark."

**Pass criteria:**
- [ ] Agent does NOT quote specific prices
- [ ] Agent explains pricing is scoped to each business
- [ ] Agent offers strategy call to discuss

---

## Scenario 10: Web Widget Caller — No Phone Number for SMS

Use the web widget on 10xaistudio.com (not the phone number). Express interest in booking.
When agent asks if you can receive a text: say "No, I'm on a computer."

**Pass criteria:**
- [ ] Agent offers email follow-up as alternative to SMS
- [ ] Agent asks for email address and calls capture_email
- [ ] Notion: Email field populated, Qualification = "Warm Lead"
- [ ] No SMS attempt is made (no phone number provided)

---

## Scenario 11: Very Short Call — Caller Hangs Up Immediately

Call the Vapi phone number. Say "wrong number" or just hang up within 10 seconds.

**Pass criteria:**
- [ ] Notion: row created with Ended Reason populated (e.g. "customer-ended-call")
- [ ] Qualification = "Unqualified" (not warm lead, not newsletter)
- [ ] No SMS attempt
- [ ] No email alert sent (no warm lead trigger)
- [ ] No 500 error in Railway logs — server must handle empty/null transcript gracefully

---

## Scenario 12: Off-Topic Pressure / Repetitive Questions

Call and ask the same unrelated question 3 times in a row ("Can you help me build a budgeting app?"), then escalate rudely ("Just answer the question!").

**Pass criteria:**
- [ ] Agent redirects with "OUT OF SCOPE" response consistently, without making up an answer
- [ ] Agent does not claim to offer services it doesn't (no hallucinated capabilities)
- [ ] On the third redirect, agent proactively offers escalation to the human team
- [ ] Agent never starts a response with "Absolutely!" or "Great question!"
- [ ] Notion: call logged. No warm lead email sent.

---

## Results Log

| Call # | Scenario | Channel | Pass / Fail | Notes |
|--------|----------|---------|-------------|-------|
| 1      |          |         |             |       |
| 2      |          |         |             |       |
| 3      |          |         |             |       |
| 4      |          |         |             |       |
| 5      |          |         |             |       |
| 6      |          |         |             |       |
| 7      |          |         |             |       |
| 8      |          |         |             |       |
| 9      |          |         |             |       |
| 10     |          |         |             |       |
| 11     |          |         |             |       |
| 12     |          |         |             |       |

---

## Go-Live Sign-Off Checklist

- [ ] 12+ manual test calls completed covering all 12 scenarios
- [ ] Transcript accuracy visually checked on 5 calls (target: 95%+)
- [ ] SMS booking link delivery confirmed on real phone (Scenario 1)
- [ ] Email capture confirmed in Notion for newsletter caller (Scenario 2)
- [ ] Parent warm lead routing confirmed (Scenario 3)
- [ ] Notion CRM has a row for every test call
- [ ] Email alert received for every warm lead call at hello@10xaistudio.com
- [ ] Vapi web widget loads on 10xaistudio.com
- [ ] Web widget + email fallback confirmed (Scenario 10)
- [ ] Very short call handled gracefully — no 500 error, row logged (Scenario 11)
- [ ] Off-topic pressure handled without hallucination (Scenario 12)
- [ ] Phone number active and routes to Alex
- [ ] Average call duration 2-4 minutes (check Vapi dashboard)
- [ ] 10X team has reviewed 3+ real call transcripts and given sign-off
- [ ] First 20 live calls monitored; system prompt iterated if needed

**Sign-off:** ________________________  Date: ________________
