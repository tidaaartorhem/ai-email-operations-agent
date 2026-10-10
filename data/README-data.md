# Data provenance

`data/raw/spotify_threads.jsonl` — 4,000 real customer-support conversation
threads with the @SpotifyCares support account, with per-turn speaker labels
and timestamps.

Source: the public **Customer Support on Twitter** corpus (Kaggle,
`thoughtvector/customer-support-on-twitter`, ~2.8M tweets, 2008–2017),
reconstructed into threads by
[pandarudra/csa](https://github.com/pandarudra/csa) and committed to that
public repo as `data/processed/spotify_threads.jsonl` (a deterministic
4,000-thread sample). Downloaded 2026-10-10 and bundled here; no synthetic
rows, no edits — the pipeline only filters by timestamp for the replay.

The demo replays the queue **as of 2017-11-20 12:00 UTC**: only turns at or
before that timestamp are visible to the pipeline (see `services/threads.py`).
Everything the UI shows — open threads, SLA clocks, duplicates — is what the
triage agent would have seen that morning.

Derived artifacts (`web/public/*.json`) are regenerated deterministically by
`python -m services.main`.
