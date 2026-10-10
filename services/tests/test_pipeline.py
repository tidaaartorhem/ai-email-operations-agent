"""Tests for the triage pipeline. All deterministic — no network, no randomness."""

from datetime import datetime, timedelta, timezone

import pytest

from services import threads as T
from services import intents, sla, duplicates, actions, drafts

NOW = datetime(2017, 11, 20, 12, 0, 0, tzinfo=timezone.utc)


def make_thread(thread_id="t1", intake_ago_h=2.0, last_speaker="customer",
                brand_reply_after_h=None):
    """Build a synthetic thread: intake, optional brand reply."""
    intake = NOW - timedelta(hours=intake_ago_h)
    turns = [{"speaker": "customer", "text": "I was charged twice", "created_at": intake}]
    first_response = None
    if brand_reply_after_h is not None:
        first_response = intake + timedelta(hours=brand_reply_after_h)
        turns.append({"speaker": "brand", "text": "looking into it",
                      "created_at": first_response})
    if last_speaker == "customer" and brand_reply_after_h is not None:
        # customer chased after the brand reply
        chase = first_response + timedelta(hours=1)
        turns.append({"speaker": "customer", "text": "still waiting",
                      "created_at": chase})
    last = turns[-1]
    return {
        "thread_id": thread_id,
        "created_at": intake,
        "turns": turns,
        "first_customer": turns[0]["text"],
        "first_response": first_response,
        "first_response_min": (
            (first_response - intake).total_seconds() / 60.0 if first_response else None
        ),
        "last_turn": last,
        "last_speaker": last["speaker"],
        "turn_count": len(turns),
        "closed": False,
    }


# --- intents -----------------------------------------------------------------

def test_seed_rules_cover_the_money_patterns():
    assert intents.seed_label("I was charged twice, refund please") == "billing"
    assert intents.seed_label("can't log in to my account") == "account_access"
    assert intents.seed_label("the app keeps crashing on playback") == "technical"
    assert intents.seed_label("cancel my subscription now") == "cancellation"
    assert intents.seed_label("it would be great if you added a sleep timer") == "feature_request"
    assert intents.seed_label("Join Premium for students, just $5.99") == "promo"
    assert intents.seed_label("hello, just saying thanks") == "general"


def test_classify_prefers_seed_rules_over_model():
    clf = intents.train([
        "I was charged twice on my card",
        "the app keeps crashing",
        "cancel my subscription please",
        "Join Premium for students just $5.99",
    ])
    intent, conf = intents.classify(clf, "Join Premium for students, just $5.99")
    assert intent == "promo" and conf == 0.95
    intent, conf = intents.classify(clf, "my bluetooth headphones won't pair")
    assert intent in intents.INTENTS and 0.0 <= conf <= 1.0


def test_classifier_is_deterministic():
    texts = ["I was charged twice"] * 3 + ["app keeps crashing"] * 3
    a = intents.train(texts)
    b = intents.train(texts)
    assert a.predict("charged twice")[0] == b.predict("charged twice")[0]


# --- sla ---------------------------------------------------------------------

def test_p1_needs_response_breach():
    t = make_thread(intake_ago_h=3.0)  # P1 billing, 3h wait, 60m target
    s = sla.score(t, "billing", NOW)
    assert s.priority == "P1"
    assert s.state == "needs_response"
    assert s.risk_bucket == "breached"
    assert s.breach_risk >= 0.7  # single-clock breach carries the 0.7 FR weight


def test_p3_on_track():
    t = make_thread(intake_ago_h=2.0)  # P3 feature request, 2h wait, 24h target
    s = sla.score(t, "feature_request", NOW)
    assert s.priority == "P3"
    assert s.risk_bucket == "on_track"


def test_at_risk_window():
    # 50 of 60 minutes consumed -> inside the 75% at-risk window
    t = make_thread(intake_ago_h=50 / 60)
    s = sla.score(t, "billing", NOW)
    assert s.risk_bucket == "at_risk"
    assert 0.5 < s.breach_risk < 1.0


def test_awaiting_customer_has_no_breach_clock():
    t = make_thread(intake_ago_h=72.0, last_speaker="brand", brand_reply_after_h=1.0)
    s = sla.score(t, "billing", NOW)
    assert s.state == "awaiting_customer"
    assert not s.fr_breached and not s.res_breached
    assert not s.silent_breach


def test_dead_air_close_candidate():
    t = make_thread(intake_ago_h=24 * 6, last_speaker="brand", brand_reply_after_h=1.0)
    s = sla.score(t, "billing", NOW)
    assert s.close_candidate
    assert s.risk_bucket == "at_risk"  # going cold, surfaced on the board


def test_silent_breach_when_customer_keeps_waiting():
    # intake 30h ago, brand replied at 1h, customer chased at 2h, still waiting
    t = make_thread(intake_ago_h=30.0, last_speaker="customer", brand_reply_after_h=1.0)
    s = sla.score(t, "billing", NOW)
    assert s.silent_breach
    assert s.risk_bucket == "breached"


# --- duplicates ----------------------------------------------------------------

def test_duplicates_find_near_identical_intakes():
    a = make_thread("a", 2.0); a["first_customer"] = "where is the iphone x update"
    b = make_thread("b", 3.0); b["first_customer"] = "why is there no iphone x update yet"
    c = make_thread("c", 4.0); c["first_customer"] = "my invoice shows the wrong tax amount"
    pairs = duplicates.find_duplicates([a, b, c], ["technical", "technical", "billing"])
    assert len(pairs) >= 1
    top = pairs[0]
    assert {top["thread_a"], top["thread_b"]} == {"a", "b"}
    assert top["similarity"] >= duplicates.SIMILARITY_THRESHOLD
    assert top["same_intent"]


def test_duplicates_empty_for_single_thread():
    assert duplicates.find_duplicates([make_thread("a", 2.0)], ["billing"]) == []


# --- actions -------------------------------------------------------------------

def test_action_priority_merge_over_reply():
    t = make_thread(intake_ago_h=2.0)
    s = sla.score(t, "billing", NOW)
    act = actions.recommend(s, 0.9, {"other_id": "t9", "similarity": 0.8,
                                     "same_intent": True})
    assert act.kind == "merge"
    assert act.merge_with == "t9"


def test_p1_breach_escalates():
    t = make_thread(intake_ago_h=3.0)
    s = sla.score(t, "billing", NOW)
    act = actions.recommend(s, 0.9, None)
    assert act.kind == "escalate"


def test_close_candidate_action():
    t = make_thread(intake_ago_h=24 * 6, last_speaker="brand", brand_reply_after_h=1.0)
    s = sla.score(t, "billing", NOW)
    act = actions.recommend(s, 0.9, None)
    assert act.kind == "close"


def test_reply_action_carries_reason():
    t = make_thread(intake_ago_h=0.5)
    s = sla.score(t, "billing", NOW)
    act = actions.recommend(s, 0.9, None)
    assert act.kind == "reply"
    assert act.reason  # a human needs to know why


# --- drafts --------------------------------------------------------------------

def test_draft_is_gated_and_cited():
    d = drafts.draft("billing", "I was charged twice on my card", 0.9)
    assert d["human_gate"] is True
    assert d["intent"] == "billing"
    assert "charged twice" in d["cited_from"]
    assert len(d["body"]) > 40


# --- corpus smoke test ----------------------------------------------------------

def test_corpus_loads_and_scores(tmp_path=None):
    pytest.importorskip("pandas")  # noqa
    corpus, as_of = T.load_corpus("data/raw/spotify_threads.jsonl",
                                  as_of=NOW)
    assert len(corpus) > 3000
    opened = T.open_threads(corpus)
    assert len(opened) > 100
    clf = intents.train([t["first_customer"] for t in corpus])
    for t in opened[:20]:
        intent, conf = intents.classify(clf, t["first_customer"])
        s = sla.score(t, intent, as_of)
        assert s.risk_bucket in ("breached", "at_risk", "on_track")
        assert 0.0 <= s.breach_risk <= 1.0
