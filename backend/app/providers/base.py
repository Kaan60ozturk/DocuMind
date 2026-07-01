"""Provider protocols. RAG code depends on these, never on a vendor SDK.

Swapping in another provider (OpenAI, Anthropic, a local model) means
implementing these two protocols and wiring the new class in ``create_app``.
"""

from collections.abc import Iterator
from typing import Protocol


class ProviderError(RuntimeError):
    """An upstream AI provider failed after retries.

    The message is always safe to show to end users — no stack traces,
    no API keys, no vendor internals.
    """


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; returns one vector per input text."""
        ...


class LLMProvider(Protocol):
    def stream(self, prompt: str) -> Iterator[str]:
        """Yield the answer to ``prompt`` incrementally, as text fragments."""
        ...
