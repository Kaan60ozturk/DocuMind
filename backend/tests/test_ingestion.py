"""End-to-end ingestion tests over real (tiny) files, with fake embeddings."""

import pytest

from app.core.ingestion import EmptyDocumentError, ingest_file

TXT_FIXTURE = (
    "DocuMind is a retrieval-augmented generation assistant. "
    "It answers questions strictly from uploaded documents.\n\n"
    "Citations point to the exact source page. " * 5
)

MD_FIXTURE = (
    "# Project Notes\n\n"
    "## Architecture\n\n"
    "The backend is FastAPI and the vector store is Chroma. "
    * 5
    + "\n\n## Testing\n\nAll tests run offline with fake providers."
)


def _ingest(path, name, settings, fake_embedder, vectorstore, registry):
    return ingest_file(
        path,
        name,
        settings=settings,
        embedder=fake_embedder,
        vectorstore=vectorstore,
        registry=registry,
    )


def test_ingest_txt_end_to_end(settings, fake_embedder, vectorstore, registry, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text(TXT_FIXTURE, encoding="utf-8")

    record = _ingest(source, "notes.txt", settings, fake_embedder, vectorstore, registry)

    assert record.status == "ready"
    assert record.pages == 1
    assert record.chunks > 0
    assert record.size_bytes == source.stat().st_size
    assert registry.get(record.id) == record
    assert vectorstore.count() == record.chunks
    # One embedding vector was produced per chunk.
    assert sum(len(call) for call in fake_embedder.calls) == record.chunks


def test_ingest_md_end_to_end(settings, fake_embedder, vectorstore, registry, tmp_path):
    source = tmp_path / "readme.md"
    source.write_text(MD_FIXTURE, encoding="utf-8")

    record = _ingest(source, "readme.md", settings, fake_embedder, vectorstore, registry)

    assert record.chunks > 0
    assert registry.get(record.id) is not None
    assert vectorstore.count() == record.chunks


def test_ingest_empty_file_raises(settings, fake_embedder, vectorstore, registry, tmp_path):
    source = tmp_path / "empty.txt"
    source.write_text("   \n\n  ", encoding="utf-8")

    with pytest.raises(EmptyDocumentError):
        _ingest(source, "empty.txt", settings, fake_embedder, vectorstore, registry)

    assert vectorstore.count() == 0
    assert registry.list() == []


def test_delete_document_removes_vectors(settings, fake_embedder, vectorstore, registry, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text(TXT_FIXTURE, encoding="utf-8")
    record = _ingest(source, "notes.txt", settings, fake_embedder, vectorstore, registry)

    assert vectorstore.count() > 0
    vectorstore.delete_document(record.id)
    assert vectorstore.count() == 0
    assert registry.delete(record.id) is True
    assert registry.list() == []
