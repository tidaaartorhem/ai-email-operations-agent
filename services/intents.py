"""Intent triage: classify the intake message of each thread.

Approach is deliberately leashed and deterministic. Keyword seed rules label
the training slice (the intake turns of the real corpus), then a TF-IDF +
MultinomialNB classifier is trained on those labels. New messages — e.g. a
pasted-in email in the demo UI — get a predicted intent plus a confidence
score. No LLM, no network calls, reproducible on every run.

Intents:
    billing          charges, payments, refunds, invoices
    account_access   login, password, hacked, can't get in
    technical        playback, app crash, sync, quality, downloads
    cancellation     cancel subscription, stop charging
    feature_request  wishlist, "you should add"
    dm_handoff       brand routed to DM / asked for private account details
    general          everything else
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

INTENTS = [
    "billing",
    "account_access",
    "technical",
    "cancellation",
    "feature_request",
    "dm_handoff",
    "promo",
    "general",
]

# Keyword seed rules. Order matters — first match wins, so specific rules
# (cancellation, dm_handoff) sit before their broader parents.
SEED_RULES: list[tuple[str, re.Pattern]] = [
    (
        "promo",
        re.compile(
            r"\b(join premium|premium is just|don'?t let ads interrupt|"
            r"\d+ months? of premium|try premium free)\b",
            re.I,
        ),
    ),
    (
        "cancellation",
        re.compile(
            r"\b(cancel(?:l?ed|ling)?|stop (?:my |the )?subscription|"
            r"stop charging|end my (?:subscription|plan|membership))\b",
            re.I,
        ),
    ),
    (
        "billing",
        re.compile(
            r"\b(charged?|charge|payment|billing|refund|invoice|price|"
            r"\$ ?\d|premium|student (?:offer|discount)|overcharged|"
            r"didn'?t authorize|unauthorized)\b",
            re.I,
        ),
    ),
    (
        "account_access",
        re.compile(
            r"\b(log ?in|login|password|sign in|cant access|can'?t access|"
            r"hacked|locked out|reset|verify (?:my )?account|email address)\b",
            re.I,
        ),
    ),
    (
        "technical",
        re.compile(
            r"\b(not working|doesn'?t work|won'?t (?:play|load|sync)|"
            r"crash(?:ing|es)?|freeze|buffer|skip|offline|download|update|bug|"
            r"error|quality|sound|playlist)\b",
            re.I,
        ),
    ),
    (
        "feature_request",
        re.compile(
            r"\b(should add|wish (?:you|spotify)|feature|suggestion|"
            r"would be (?:great|nice|cool) if|add (?:a |an )?(?:option|feature|"
            r"button)|why (?:can|could)n'?t (?:we|i|you))\b",
            re.I,
        ),
    ),
    (
        "dm_handoff",
        re.compile(r"\b(dm us|check your dm|backstage|send us (?:a )?dm)\b", re.I),
    ),
]


def seed_label(text: str) -> str:
    for intent, pattern in SEED_RULES:
        if pattern.search(text):
            return intent
    return "general"


@dataclass
class IntentClassifier:
    pipeline: Pipeline
    train_size: int

    def predict(self, text: str) -> tuple[str, float]:
        """(intent, confidence) for one message."""
        probs = self.pipeline.predict_proba([text])[0]
        idx = int(probs.argmax())
        return self.pipeline.classes_[idx], float(probs[idx])

    def batch(self, texts: list[str]) -> list[tuple[str, float]]:
        probs = self.pipeline.predict_proba(texts)
        return [
            (self.pipeline.classes_[int(row.argmax())], float(row.max()))
            for row in probs
        ]


def clean(text: str) -> str:
    text = re.sub(r"^(@\w+\s*)+", "", text)  # strip leading handles
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def train(intake_texts: list[str]) -> IntentClassifier:
    """Train the classifier on seed-labeled intake turns.

    Threads whose intake seeds to 'general' are excluded from training so the
    model learns the discriminative intents, not the long tail.
    """
    labels = [seed_label(t) for t in intake_texts]
    train_texts = [clean(t) for t, l in zip(intake_texts, labels) if l != "general"]
    train_labels = [l for l in labels if l != "general"]
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(max_features=4000, ngram_range=(1, 2),
                                      stop_words="english")),
            ("nb", MultinomialNB()),
        ]
    )
    pipeline.fit(train_texts, train_labels)
    return IntentClassifier(pipeline=pipeline, train_size=len(train_texts))


def classify(classifier: IntentClassifier, text: str) -> tuple[str, float]:
    """Classify one message.

    Keyword seed rules are authoritative for the patterns they match (they
    are denylists and certain phrases, not fuzzy guesses); the trained model
    handles everything else.
    """
    seed = seed_label(text)
    if seed != "general":
        return seed, 0.95
    return classifier.predict(text)
