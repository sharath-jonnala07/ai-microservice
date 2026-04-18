from __future__ import annotations

from prometheus_client import Counter, Histogram


CHAT_REQUESTS = Counter(
    "fundintel_chat_requests_total",
    "Count of chat requests handled by the service.",
    ["status"],
)

CHAT_LATENCY_SECONDS = Histogram(
    "fundintel_chat_latency_seconds",
    "End-to-end latency for chat requests.",
    buckets=(0.2, 0.5, 1, 2, 3, 5, 10, 20),
)

RETRIEVAL_MISSES = Counter(
    "fundintel_retrieval_misses_total",
    "Count of retrieval misses when no reliable source was found.",
)
