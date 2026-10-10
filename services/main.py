"""Pipeline: corpus -> triage, SLA scores, actions -> static JSON for the web UI.

Run:  python -m services.main
Reads:  data/raw/spotify_threads.jsonl
Writes: web/public/queue.json      top-N highest-risk open threads, full detail
        web/public/analytics.json  corpus-wide SLA/intent/volume analytics
        web/public/duplicates.json  merge candidates
        web/public/meta.json        run metadata (deterministic provenance)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from . import threads as T
from . import intents, sla, duplicates, actions, drafts

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "spotify_threads.jsonl"
OUT = ROOT / "web" / "public"

# The demo is a deterministic replay: the queue exactly as it stood on the
# morning of Nov 20, 2017 (mid-corpus, so the queue has real depth — a mix of
# ticking first-response clocks, awaiting-customer threads, and dead air).
AS_OF = datetime(2017, 11, 20, 12, 0, 0, tzinfo=timezone.utc)

# Demo surface: only the highest-risk open threads ship with full turns.
QUEUE_LIMIT = 250
# Paste-in demo: classify arbitrary pasted text with the trained model.
PASTE_SAMPLES = [
    "I was charged twice for premium this month, please refund the second charge.",
    "My app keeps crashing every time I try to play offline playlists.",
    "Can you please cancel my subscription effective immediately?",
    "It would be great if you added a sleep timer to the desktop app.",
]


def fmt_min(minutes: float | None) -> str | None:
    if minutes is None:
        return None
    if minutes < 60:
        return f"{minutes:.0f}m"
    if minutes < 1440:
        return f"{minutes / 60:.1f}h"
    return f"{minutes / 1440:.1f}d"


def run() -> dict:
    corpus, as_of = T.load_corpus(RAW, as_of=AS_OF)
    opened = T.open_threads(corpus)
    print(f"replay_as_of={as_of.isoformat()} corpus={len(corpus)} open={len(opened)}")

    classifier = intents.train([t["first_customer"] for t in corpus])
    print(f"classifier trained on {classifier.train_size} seed-labeled intake turns")

    # --- score every thread -------------------------------------------------
    enriched = []
    for t in corpus:
        intent, conf = intents.classify(classifier, t["first_customer"])
        s = sla.score(t, intent, as_of)
        enriched.append({"thread": t, "intent": intent, "conf": conf, "sla": s})

    # --- duplicates among open, non-promo threads --------------------------------
    dup_pool = [e for e in enriched
                if not e["thread"]["closed"] and e["intent"] != "promo"]
    dup_pairs = duplicates.find_duplicates(
        [e["thread"] for e in dup_pool], [e["intent"] for e in dup_pool]
    )
    dup_of: dict[str, dict] = {}
    for p in dup_pairs:
        dup_of.setdefault(p["thread_b"], {"other_id": p["thread_a"],
                                         "similarity": p["similarity"],
                                         "same_intent": p["same_intent"]})
    print(f"duplicate pairs={len(dup_pairs)}")

    # --- actions + drafts for open threads -----------------------------------
    queue_rows = []
    archived = 0
    for e in enriched:
        t, s = e["thread"], e["sla"]
        if t["closed"]:
            continue
        if e["intent"] == "promo":
            # Marketing broadcasts are not support work: auto-archive, counted
            # in analytics, kept out of the human queue.
            archived += 1
            continue
        dup = dup_of.get(t["thread_id"])
        act = actions.recommend(s, e["conf"], dup)
        row = {
            "thread_id": t["thread_id"],
            "intent": e["intent"],
            "intent_confidence": round(e["conf"], 3),
            "priority": s.priority,
            "state": s.state,
            "risk_bucket": s.risk_bucket,
            "breach_risk": s.breach_risk,
            "first_customer": t["first_customer"],
            "created_at": t["created_at"].isoformat(),
            "last_turn_at": t["last_turn"]["created_at"].isoformat(),
            "last_speaker": s.state,
            "turn_count": t["turn_count"],
            "first_response_min": (round(t["first_response_min"], 1)
                                   if t["first_response_min"] is not None else None),
            "first_response_human": fmt_min(t["first_response_min"]),
            "fr_target_min": s.fr_target,
            "res_target_min": s.res_target,
            "queue_age_min": round(s.resolution_clock_min, 1),
            "queue_age_human": fmt_min(s.resolution_clock_min),
            "response_clock_min": (round(s.response_clock_min, 1)
                                   if s.response_clock_min is not None else None),
            "dead_air_min": (round(s.dead_air_min, 1)
                             if s.dead_air_min is not None else None),
            "close_candidate": s.close_candidate,
            "silent_breach": s.silent_breach,
            "action": act.kind,
            "action_confidence": act.confidence,
            "action_reason": act.reason,
            "merge_with": act.merge_with,
            "merge_similarity": act.merge_similarity,
            "draft": drafts.draft(e["intent"], t["first_customer"], e["conf"])
            if act.kind == "reply" else None,
            "turns": [
                {
                    "speaker": x["speaker"],
                    "text": x["text"],
                    "created_at": x["created_at"].isoformat(),
                }
                for x in t["turns"]
            ],
        }
        queue_rows.append(row)

    # Risk board: breached first, then by breach risk.
    rank = {"breached": 0, "at_risk": 1, "on_track": 2}
    queue_rows.sort(key=lambda r: (rank[r["risk_bucket"]], -r["breach_risk"]))
    queue_top = queue_rows[:QUEUE_LIMIT]

    # --- analytics -----------------------------------------------------------
    by_intent = defaultdict(lambda: {"threads": 0, "fr": [], "breached": 0, "open": 0})
    for e in enriched:
        d = by_intent[e["intent"]]
        d["threads"] += 1
        if e["thread"]["first_response_min"] is not None:
            d["fr"].append(e["thread"]["first_response_min"])
        if not e["thread"]["closed"] and e["intent"] != "promo":
            d["open"] += 1
            if e["sla"].risk_bucket == "breached":
                d["breached"] += 1

    intent_rows = []
    for intent_name, d in sorted(by_intent.items(), key=lambda kv: -kv[1]["threads"]):
        fr_sorted = sorted(d["fr"])
        median_fr = fr_sorted[len(fr_sorted) // 2] if fr_sorted else None
        intent_rows.append({
            "intent": intent_name,
            "threads": d["threads"],
            "open": d["open"],
            "median_first_response_min": round(median_fr, 1) if median_fr else None,
            "median_first_response_human": fmt_min(median_fr),
            "breach_rate": round(d["breached"] / d["open"], 3) if d["open"] else 0,
            "priority": sla.PRIORITY_BY_INTENT[intent_name],
        })

    by_hour = Counter()
    for t in corpus:
        by_hour[t["created_at"].hour] += 1

    open_rows = [e for e in enriched
                 if not e["thread"]["closed"] and e["intent"] != "promo"]
    totals = {
        "threads": len(corpus),
        "open": len(open_rows),
        "closed": len(corpus) - len(open_rows),
        "breached": sum(1 for e in open_rows if e["sla"].risk_bucket == "breached"),
        "at_risk": sum(1 for e in open_rows if e["sla"].risk_bucket == "at_risk"),
        "on_track": sum(1 for e in open_rows if e["sla"].risk_bucket == "on_track"),
        "needs_response": sum(1 for e in open_rows if e["sla"].state == "needs_response"),
        "awaiting_customer": sum(1 for e in open_rows if e["sla"].state == "awaiting_customer"),
        "close_candidates": sum(1 for e in open_rows if e["sla"].close_candidate),
        "silent_breaches": sum(1 for e in open_rows if e["sla"].silent_breach),
        "duplicate_pairs": len(dup_pairs),
        "auto_archived_promo": archived,
        "actions": dict(Counter(
            actions.recommend(e["sla"], e["conf"], dup_of.get(e["thread"]["thread_id"])).kind
            for e in open_rows
        )),
    }

    analytics = {
        "totals": totals,
        "by_intent": intent_rows,
        "by_hour": [{"hour": h, "threads": by_hour.get(h, 0)} for h in range(24)],
    }

    # --- paste-in demo: what the classifier does with new text --------------
    paste_demo = [
        {"text": p, "intent": c, "confidence": round(cf, 3)}
        for p, (c, cf) in
        ((p, intents.classify(classifier, p)) for p in PASTE_SAMPLES)
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "queue.json").write_text(json.dumps(queue_top, indent=1))
    (OUT / "analytics.json").write_text(json.dumps(analytics, indent=1))
    (OUT / "duplicates.json").write_text(json.dumps(dup_pairs, indent=1))
    (OUT / "paste_demo.json").write_text(json.dumps(paste_demo, indent=1))
    (OUT / "meta.json").write_text(json.dumps({
        "project": "ai-email-operations-agent",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": "4000 real SpotifyCares support threads "
                  "(Customer Support on Twitter, Kaggle, via pandarudra/csa)",
        "corpus_as_of": as_of.isoformat(),
        "replay_note": "Queue state is a deterministic replay of the morning of "
                       "2017-11-20: only turns at or before that timestamp are "
                       "visible to the pipeline.",
        "classifier": f"TF-IDF + MultinomialNB, trained on {classifier.train_size} "
                      "deterministic keyword seed labels",
        "queue_limit": QUEUE_LIMIT,
        "deterministic": True,
    }, indent=1))
    print(f"wrote queue({len(queue_top)}), analytics, duplicates, paste_demo to {OUT}")
    return {"totals": totals, "intent_rows": intent_rows}


if __name__ == "__main__":
    run()
