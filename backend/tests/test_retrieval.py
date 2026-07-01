"""Retrieval tests: ranking over two tiny ingested documents."""

from app.core.ingestion import ingest_file
from app.core.retrieval import retrieve

CATS_TEXT = (
    "Cats are small domestic felines. Kittens love to play with yarn. "
    "A cat purrs when it is happy. Felines sleep for many hours every day. " * 3
)

SPACE_TEXT = (
    "Rockets launch satellites into orbit. The spacecraft traveled to Mars. "
    "Astronauts float in microgravity aboard the station. " * 3
)


def _ingest_two_docs(settings, fake_embedder, vectorstore, registry, tmp_path):
    for name, text in (("cats.txt", CATS_TEXT), ("space.txt", SPACE_TEXT)):
        path = tmp_path / name
        path.write_text(text, encoding="utf-8")
        ingest_file(
            path,
            name,
            settings=settings,
            embedder=fake_embedder,
            vectorstore=vectorstore,
            registry=registry,
        )


def test_empty_store_returns_no_chunks(settings, fake_embedder, vectorstore):
    result = retrieve("anything at all", embedder=fake_embedder, vectorstore=vectorstore, top_k=5)
    assert result == []
    # Short-circuit means the question is never embedded.
    assert fake_embedder.calls == []


def test_query_returns_scored_sorted_chunks(
    settings, fake_embedder, vectorstore, registry, tmp_path
):
    _ingest_two_docs(settings, fake_embedder, vectorstore, registry, tmp_path)

    results = retrieve(
        "Why do kittens play and cats purr?",
        embedder=fake_embedder,
        vectorstore=vectorstore,
        top_k=4,
    )

    assert 0 < len(results) <= 4
    scores = [chunk.similarity for chunk in results]
    assert scores == sorted(scores, reverse=True)
    # Vocabulary overlap must rank the cat document first.
    assert results[0].filename == "cats.txt"
    assert results[0].page == 1
    assert results[0].text


def test_top_k_caps_result_count(settings, fake_embedder, vectorstore, registry, tmp_path):
    _ingest_two_docs(settings, fake_embedder, vectorstore, registry, tmp_path)
    results = retrieve("rockets in orbit", embedder=fake_embedder, vectorstore=vectorstore, top_k=1)
    assert len(results) == 1
    assert results[0].filename == "space.txt"
