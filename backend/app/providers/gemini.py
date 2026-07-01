"""Gemini implementation of the provider protocols (official google-genai SDK)."""

import logging
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors

from app.config import Settings
from app.providers.base import ProviderError

logger = logging.getLogger(__name__)

_RETRYABLE_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_INITIAL_BACKOFF_SECONDS = 1.0
_EMBED_BATCH_SIZE = 100  # Gemini embedding API accepts at most 100 texts per call

_UNAVAILABLE_MESSAGE = (
    "The AI service is temporarily unavailable or rate-limited. Please try again in a moment."
)

T = TypeVar("T")


class GeminiProvider:
    """Implements both ``EmbeddingProvider`` and ``LLMProvider`` against Gemini."""

    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._chat_model = settings.gemini_chat_model
        self._embedding_model = settings.gemini_embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            response = self._with_retries(
                lambda batch=batch: self._client.models.embed_content(
                    model=self._embedding_model, contents=batch
                )
            )
            vectors.extend([list(embedding.values) for embedding in response.embeddings])
        return vectors

    def stream(self, prompt: str) -> Iterator[str]:
        # The SDK sends the request lazily, so pull the first chunk inside the
        # retry wrapper; connection/rate-limit failures then actually retry.
        def start() -> tuple[object | None, Iterator]:
            chunks = self._client.models.generate_content_stream(
                model=self._chat_model, contents=prompt
            )
            return next(chunks, None), chunks

        first, chunks = self._with_retries(start)
        try:
            if first is not None and getattr(first, "text", None):
                yield first.text
            for chunk in chunks:
                if chunk.text:
                    yield chunk.text
        except genai_errors.APIError as exc:
            logger.error("Gemini stream failed mid-response (HTTP %s)", exc.code)
            raise ProviderError(_UNAVAILABLE_MESSAGE) from exc

    def _with_retries(self, call: Callable[[], T]) -> T:
        delay = _INITIAL_BACKOFF_SECONDS
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return call()
            except genai_errors.APIError as exc:
                if exc.code not in _RETRYABLE_CODES or attempt == _MAX_ATTEMPTS:
                    logger.error("Gemini call failed (HTTP %s), giving up", exc.code)
                    raise ProviderError(_UNAVAILABLE_MESSAGE) from exc
                logger.warning(
                    "Gemini call failed (HTTP %s), retrying in %.1fs (attempt %d/%d)",
                    exc.code,
                    delay,
                    attempt,
                    _MAX_ATTEMPTS,
                )
                time.sleep(delay)
                delay *= 2
        raise AssertionError("unreachable")  # pragma: no cover
