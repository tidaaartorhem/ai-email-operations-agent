"""Action engine: one recommended next action per thread, with confidence.

Nothing sends anything — every action is a recommendation for a human.
The engine picks from a small fixed vocabulary:

    reply    thread needs a first response; a draft is attached
    escalate silent breach or P1 at risk — a senior should own it
    merge    probable duplicate of another open thread
    close    dead-air auto-close candidate
    monitor  awaiting customer; nothing to do yet

Priority of checks matters: duplicates and silent breaches outrank a plain
reply, because double-handling and waiting-customer breaches are the expensive
failure modes. Confidence is deterministic from intent confidence and SLA
state — never from a model temperature.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Action:
    kind: str  # reply | escalate | merge | close | monitor
    confidence: float  # 0-1, deterministic
    reason: str
    merge_with: str | None = None
    merge_similarity: float | None = None


def recommend(
    score,  # SlaScore
    intent_confidence: float,
    duplicate_of: dict | None,
) -> Action:
    if duplicate_of is not None and duplicate_of["same_intent"]:
        return Action(
            kind="merge",
            confidence=round(0.5 + 0.5 * duplicate_of["similarity"], 3),
            reason=(
                f"Intake text is {duplicate_of['similarity']:.0%} similar to open "
                f"thread {duplicate_of['other_id']} (same intent). Reply once, "
                "merge the pair, avoid double-handling."
            ),
            merge_with=duplicate_of["other_id"],
            merge_similarity=duplicate_of["similarity"],
        )
    if score.silent_breach:
        return Action(
            kind="escalate",
            confidence=round(min(0.99, 0.7 + score.breach_risk * 0.3), 3),
            reason=(
                "Customer is still waiting past the resolution SLA. "
                "The first reply didn't land — escalate to a senior owner."
            ),
        )
    if score.risk_bucket == "breached" and score.priority == "P1":
        return Action(
            kind="escalate",
            confidence=round(min(0.99, 0.6 + score.breach_risk * 0.35), 3),
            reason=(
                f"P1 thread breached its {score.fr_target:.0f}-minute first-response "
                "target. Money or access is on the line — escalate."
            ),
        )
    if score.close_candidate:
        return Action(
            kind="close",
            confidence=round(min(0.95, 0.6 + intent_confidence * 0.3), 3),
            reason=(
                "Brand replied and the customer never came back. "
                "Dead air — safe to auto-close with a courtesy note."
            ),
        )
    if score.state == "needs_response":
        return Action(
            kind="reply",
            confidence=round(min(0.99, 0.55 + intent_confidence * 0.35), 3),
            reason=(
                "Customer is waiting for a first response. "
                "Draft below is ready for a human to review and send."
            ),
        )
    return Action(
        kind="monitor",
        confidence=0.8,
        reason="Brand replied; waiting on the customer. No action until the dead-air window.",
    )
