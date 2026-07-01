"""Shared fixtures: fake providers, tmp data dir, wired test app. Zero network."""

import hashlib
import math
import re
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.documents import DocumentRegistry
from app.db.vectorstore import VectorStore
from app.main import create_app


class FakeEmbeddingProvider:
    """Deterministic bag-of-words hashing embeddings.

    Texts sharing vocabulary get genuinely higher cosine similarity, so
    retrieval tests can assert real ranking behaviour — still no network
    and fully stable across runs.
    """

    dim = 64

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for word in re.findall(r"\w+", text.lower(), flags=re.UNICODE):
            digest = hashlib.md5(word.encode("utf-8")).hexdigest()
            vector[int(digest, 16) % self.dim] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            vector[0] = 1.0
            norm = 1.0
        return [value / norm for value in vector]


class FakeLLMProvider:
    """Yields a fixed token stream and records every prompt it receives."""

    def __init__(self, tokens: tuple[str, ...] = ("This ", "is ", "the ", "answer ", "[1].")):
        self.tokens = tokens
        self.prompts: list[str] = []

    def stream(self, prompt: str) -> Iterator[str]:
        self.prompts.append(prompt)
        yield from self.tokens


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        gemini_api_key="test-key-never-used",
        data_dir=tmp_path / "data",
        chunk_size=300,
        chunk_overlap=50,
        top_k=5,
        max_file_mb=1,
    )


@pytest.fixture
def fake_embedder() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider()


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def app(settings, fake_embedder, fake_llm):
    return create_app(settings, embedder=fake_embedder, llm=fake_llm)


@pytest.fixture
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def registry(settings) -> DocumentRegistry:
    settings.ensure_dirs()
    return DocumentRegistry(settings.sqlite_path)


@pytest.fixture
def vectorstore(settings) -> VectorStore:
    settings.ensure_dirs()
    return VectorStore(settings.chroma_dir)
