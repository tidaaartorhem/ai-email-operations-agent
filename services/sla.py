"""SLA engine: per-thread first-response and resolution scoring.

This is the core of the product. A shared queue (support@, ops@) answers by
reading, not by math: nobody knows which open thread will miss its
first-response SLA next. The engine scores every thread deterministically from
speakers + timestamps:

- needs_response   last turn is the customer; the first-response clock is ticking
- awaiting_customer last turn is the brand; dead-air clock is ticking
- breached         a clock already passed its target
- at_risk          a clock will pass its target within the risk window
- on_track         clocks are healthy

Breach risk (0-1) = fraction of the relevant SLA budget already consumed,
clamped. A thread at 90% of its first-response budget is at higher risk than
a thread at 90% of its resolution budget, so first-response weight dominates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .intents import INTENTS  # noqa: F401  (documents the intent domain)

# Minutes. P1 = money or access issues, P2 = broken product, P3 = the rest.
PRIORITY_BY_INTENT = {
    "billing": "P1",
    "account_access": "P1",
    "cancellation": "P1",
    "technical": "P2",
    "dm_handoff": "P2",
    "promo": "P3",
    "feature_request": "P3",
    "general": "P3",
}

FIRST_RESPONSE_MIN = {"P1": 60.0, "P2": 240.0, "P3": 1440.0}
RESOLUTION_MIN = {"P1": 24 * 60.0, "P2": 72 * 60.0, "P3": 7 * 24 * 60.0}

# Threads within this fraction of a target count as at-risk.
AT_RISK_FRACTION = 0.75
# Brand's last word older than this (days) with no reply -> auto-close candidate.
DEAD_AIR_DAYS = 5


@dataclass
class SlaScore:
    priority: str
    state: str  # needs_response | awaiting_customer
    first_response_min: float | None  # actual, if brand already replied
    resolution_clock_min: float  # age since intake
    response_clock_min: float | None  # age since last customer turn (needs_response only)
    dead_air_min: float | None  # age since last brand turn (awaiting_customer only)
    fr_target: float
    res_target: float
    fr_breached: bool
    res_breached: bool
    risk_bucket: str  # breached | at_risk | on_track
    breach_risk: float  # 0-1
    close_candidate: bool
    silent_breach: bool  # customer waiting past resolution target


def _risk(consumed: float, target: float) -> float:
    return min(1.0, max(0.0, consumed / target))


def score(
    thread: dict,
    intent: str,
    as_of: datetime,
) -> SlaScore:
    priority = PRIORITY_BY_INTENT.get(intent, "P3")
    fr_target = FIRST_RESPONSE_MIN[priority]
    res_target = RESOLUTION_MIN[priority]
    intake_age = (as_of - thread["created_at"]).total_seconds() / 60.0
    first_response_min = thread["first_response_min"]

    close_candidate = False
    silent_breach = False

    if thread["last_speaker"] == "customer":
        state = "needs_response"
        response_clock = (as_of - thread["last_turn"]["created_at"]).total_seconds() / 60.0
        dead_air = None
        fr_actual = first_response_min if first_response_min is not None else response_clock
        fr_breached = fr_actual > fr_target
        res_breached = intake_age > res_target
        silent_breach = intake_age > res_target  # customer still waiting, clock blown
        risk = max(_risk(fr_actual, fr_target) * 0.7, _risk(intake_age, res_target) * 0.3)
        risk = min(1.0, risk + (0.25 if silent_breach else 0.0))
        bucket = "on_track"
        if fr_breached or res_breached:
            bucket = "breached"
        elif fr_actual >= fr_target * AT_RISK_FRACTION:
            bucket = "at_risk"
        elif intake_age >= res_target * AT_RISK_FRACTION:
            bucket = "at_risk"
    else:
        # The ball is in the customer's court. There is no ticking response
        # clock here — the operational risk is dead air, not breach.
        state = "awaiting_customer"
        response_clock = None
        dead_air = (as_of - thread["last_turn"]["created_at"]).total_seconds() / 60.0
        fr_breached = False  # historical fact, tracked in analytics, not a live risk
        res_breached = False
        close_candidate = dead_air / 1440.0 >= DEAD_AIR_DAYS
        # Going cold: brand replied, no customer follow-up, approaching the
        # dead-air window. Nudge it or close it.
        if close_candidate:
            bucket = "at_risk"
        elif dead_air / 1440.0 >= DEAD_AIR_DAYS * AT_RISK_FRACTION:
            bucket = "at_risk"
        else:
            bucket = "on_track"
        risk = _risk(dead_air / 1440.0, DEAD_AIR_DAYS) * 0.4

    return SlaScore(
        priority=priority,
        state=state,
        first_response_min=first_response_min,
        resolution_clock_min=intake_age,
        response_clock_min=response_clock,
        dead_air_min=dead_air,
        fr_target=fr_target,
        res_target=res_target,
        fr_breached=fr_breached,
        res_breached=res_breached,
        risk_bucket=bucket,
        breach_risk=round(risk, 4),
        close_candidate=close_candidate,
        silent_breach=silent_breach,
    )
