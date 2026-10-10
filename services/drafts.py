"""Draft generator: first-response drafts from intent templates + thread context.

The drafts are template-based with the thread's own wording quoted back, so
the customer feels heard. Every draft cites what it was built from (intent,
confidence, the intake turn). The human gate is a design rule, not a
suggestion: drafts are output, never sent.
"""

from __future__ import annotations

TEMPLATES = {
    "billing": (
        "Thanks for flagging this — I can see the charge you're referring to. "
        "I'm pulling up your billing history now and will confirm the exact "
        "amount and date. If it turns out to be an error, I'll process the "
        "correction from my side."
    ),
    "account_access": (
        "Let's get you back in. Can you confirm the email address on the "
        "account? Once I have that, I'll check the sign-in activity and send "
        "a secure reset link."
    ),
    "technical": (
        "Sorry you're hitting this — let's narrow it down. What device and app "
        "version are you on, and does it happen every time or intermittently? "
        "Those two details usually point straight at the cause."
    ),
    "cancellation": (
        "Understood — happy to sort this out. Before I process the "
        "cancellation, can you confirm the account email? I'll make sure no "
        "further charges go through after today."
    ),
    "feature_request": (
        "Good idea — I can see how that would help. I'm logging this as a "
        "feature request for the product team with your exact use case "
        "attached. No timeline I can promise, but it's now on their radar."
    ),
    "dm_handoff": (
        "Got it — this needs a couple of private details, so I'll continue "
        "with you over DM. Please reply there with your account email and "
        "I'll take it from here."
    ),
    "general": (
        "Thanks for reaching out — I've got your message and I'm looking into "
        "it now. I'll follow up here with next steps shortly."
    ),
}


def draft(intent: str, first_customer: str, confidence: float) -> dict:
    """Build a review-ready first-response draft for one thread."""
    body = TEMPLATES.get(intent, TEMPLATES["general"])
    return {
        "body": body,
        "intent": intent,
        "confidence": round(confidence, 3),
        "cited_from": first_customer[:180],
        "human_gate": True,  # drafts are output only; a person sends them
    }
