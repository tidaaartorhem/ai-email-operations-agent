"""Duplicate detection: find open threads that are the same request twice.

Same customer, same problem, two threads — it happens constantly in shared
queues (customer retries when the first reply is slow). Merging them kills
double-handling and stops two agents replying to the same person.

Deterministic: TF-IDF vectors over intake turns of open needs_response
threads, cosine similarity over a fixed threshold. Pairs are ranked by
similarity and returned with the evidence (both intake texts).
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .intents import clean

SIMILARITY_THRESHOLD = 0.55
MAX_PAIRS = 40


def find_duplicates(threads: list[dict], intents: list[str]) -> list[dict]:
    """threads: open needs_response threads (parallel to intents)."""
    if len(threads) < 2:
        return []
    texts = [clean(t["first_customer"]) for t in threads]
    vec = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), stop_words="english")
    mat = vec.fit_transform(texts)
    sim = cosine_similarity(mat)
    pairs = []
    n = len(threads)
    for i in range(n):
        for j in range(i + 1, n):
            s = float(sim[i, j])
            if s >= SIMILARITY_THRESHOLD:
                same_intent = intents[i] == intents[j]
                pairs.append(
                    {
                        "thread_a": threads[i]["thread_id"],
                        "thread_b": threads[j]["thread_id"],
                        "similarity": round(s, 3),
                        "intent_a": intents[i],
                        "intent_b": intents[j],
                        "same_intent": same_intent,
                        "text_a": threads[i]["first_customer"][:160],
                        "text_b": threads[j]["first_customer"][:160],
                    }
                )
    # Same-intent pairs first — those are the real merge candidates.
    pairs.sort(key=lambda p: (not p["same_intent"], -p["similarity"]))
    return pairs[:MAX_PAIRS]
