# Triage Radar — the shared-inbox SLA radar

**The problem.** Small teams run support on a shared queue — support@, ops@, a
shared Slack channel. The queue is answered by *reading*, not by math: nobody
knows which open thread will miss its first-response SLA next, which threads
are the same request filed twice, or how much of the queue is dead air where
the team replied and the customer never came back. CI-style dashboards show
ticket counts; none of them show *time running out*.

Triage Radar scores every open thread against its first-response and
resolution SLA clocks, deterministically, from speakers + timestamps. It
recommends one next action per thread (draft reply, escalate, merge, close,
monitor), attaches a review-ready first-response draft where a reply is due,
and surfaces the three failure modes shared queues actually have: **silent
breaches** (customer still waiting past the resolution SLA), **dead air**
(brand replied, nobody came back — auto-close candidates), and **duplicates**
(same request, two threads, about to be double-handled).

Nothing sends anything. Every draft and action is a recommendation for a
human.

## Live demo

https://ai-email-operations-agent.web.app

The demo replays the queue **as it stood on the morning of 2017-11-20** —
only turns at or before that timestamp are visible to the pipeline. From
3,084 real threads: 465 open, 9 breached, 148 dead-air close candidates,
19 duplicate pairs, 11 ticking first-response clocks.

## How it works

```
data/raw/spotify_threads.jsonl
        │  threads.py — channel-agnostic thread model + replay-as-of filter
        ▼
intents.py — keyword seed rules (authoritative) + TF-IDF/MultinomialNB
             for the long tail → intent + confidence
        ▼
sla.py — per-thread SLA scoring:
         • needs_response → first-response clock is ticking; breach risk
           = fraction of SLA budget consumed (FR weighted 0.7, resolution 0.3)
         • awaiting_customer → no response clock; risk is dead air
             (5-day auto-close window)
        ▼
duplicates.py — TF-IDF cosine over intake texts of open threads (≥ 0.55)
actions.py    — one recommended action per thread, deterministic confidence
drafts.py     — template first-response drafts citing the intake message,
                always behind a human gate
        ▼
web/public/*.json → React triage radar (risk board, thread detail,
duplicates, analytics, triage lab)
```

Deterministic end to end: no LLM calls, no network, no randomness. The same
corpus always produces the same queue.

## Real data

`data/raw/spotify_threads.jsonl` — 4,000 real @SpotifyCares support threads
with per-turn speaker labels and timestamps, from the public **Customer
Support on Twitter** corpus (Kaggle), reconstructed by
[pandarudra/csa](https://github.com/pandarudra/csa). See
`data/README-data.md`. No synthetic rows.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m services.main        # → web/public/*.json
pytest services/tests          # 17 tests

cd web && npm install
npm test                       # vitest
npm run build                  # → web/dist
```

## Project structure

- `services/` — Python pipeline (threads, intents, sla, duplicates, actions, drafts, main)
- `services/tests/` — pytest suite
- `web/src/` — React + TypeScript triage radar (light mode)
- `data/` — real corpus + provenance
