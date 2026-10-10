"""Thread ingestion: load a raw conversation corpus into the channel-agnostic
thread model used by every downstream module.

Thread model (one dict per thread):
    thread_id        str   stable id from the corpus
    created_at       datetime (tz-aware UTC)
    turns            list of {speaker: customer|brand, text, created_at}
    first_customer   str   text of the first customer turn (the intake message)
    first_response   datetime|None  timestamp of the first brand reply
    first_response_min float|None   minutes from intake to first brand reply
    last_turn        dict  the most recent turn
    last_speaker     customer|brand
    closed           bool  brand got the last word and the thread went quiet

Replay semantics: the loader takes an ``as_of`` timestamp and only sees turns
at or before it — the pipeline replays the queue exactly as it looked on that
morning. Threads started after ``as_of`` don't exist yet; threads whose first
brand reply comes after ``as_of`` still have a ticking first-response clock.

The raw corpus here is 4,000 real SpotifyCares customer-support threads
(reconstructed from the public 'Customer Support on Twitter' Kaggle corpus by
pandarudra/csa and committed to a public repo — see data/README-data.md).
The loader is deliberately channel-agnostic: email (mbox/EML), chat, and
social-support threads all map to the same model, because the SLA math below
only needs speakers and timestamps.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

# Threads whose last brand reply is older than this are treated as resolved.
CLOSED_AFTER = timedelta(days=7)


def parse_ts(value: str) -> datetime:
    dt = parsedate_to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_corpus(path: str | Path, as_of: datetime | None = None) -> tuple[list[dict], datetime]:
    """Load raw jsonl threads into the normalized thread model.

    With as_of=None, the full corpus is loaded and as_of defaults to the
    newest turn (the corpus "present").
    """
    threads: list[dict] = []
    corpus_max: datetime | None = None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            turns = [
                {
                    "speaker": t["speaker"],
                    "text": t["text"],
                    "created_at": parse_ts(t["created_at"]),
                }
                for t in raw["turns"]
            ]
            turns.sort(key=lambda t: t["created_at"])
            if corpus_max is None or turns[-1]["created_at"] > corpus_max:
                corpus_max = turns[-1]["created_at"]
            created = parse_ts(raw["created_at"])
            if as_of is not None and created > as_of:
                continue  # thread starts in the future — doesn't exist yet
            visible = [t for t in turns if t["created_at"] <= as_of] if as_of else turns
            if not visible:
                continue
            customer_turns = [t for t in visible if t["speaker"] == "customer"]
            brand_turns = [t for t in visible if t["speaker"] == "brand"]
            if not customer_turns:
                continue  # no intake message yet — nothing to triage
            intake = customer_turns[0]["created_at"]
            first_response = brand_turns[0]["created_at"] if brand_turns else None
            last = visible[-1]
            threads.append(
                {
                    "thread_id": str(raw["thread_id"]),
                    "created_at": intake,
                    "turns": visible,
                    "first_customer": customer_turns[0]["text"],
                    "first_response": first_response,
                    "first_response_min": (
                        (first_response - intake).total_seconds() / 60.0
                        if first_response
                        else None
                    ),
                    "last_turn": last,
                    "last_speaker": last["speaker"],
                    "turn_count": len(visible),
                }
            )
    assert corpus_max is not None
    if as_of is None:
        as_of = corpus_max
    for t in threads:
        last = t["last_turn"]
        t["closed"] = (
            t["last_speaker"] == "brand"
            and (as_of - last["created_at"]) >= CLOSED_AFTER
        )
    return threads, as_of


def open_threads(threads: list[dict]) -> list[dict]:
    """Threads that still need someone to do something."""
    return [t for t in threads if not t["closed"]]
