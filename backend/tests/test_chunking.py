"""Unit tests for the pure chunking module — no I/O, no network."""

import pytest

from app.core.chunking import Chunk, chunk_pages, split_text
from app.core.parsing import Page


def test_empty_and_whitespace_input_yield_no_chunks():
    assert split_text("", 100, 10) == []
    assert split_text("   \n\n \t ", 100, 10) == []


def test_short_text_is_a_single_chunk():
    assert split_text("hello world", 100, 10) == ["hello world"]


def test_invalid_parameters_raise():
    with pytest.raises(ValueError):
        split_text("text", 0, 0)
    with pytest.raises(ValueError):
        split_text("text", 100, 100)
    with pytest.raises(ValueError):
        split_text("text", 100, -1)


def test_no_chunk_exceeds_chunk_size():
    paragraphs = [f"Paragraph {i}. " + "word " * 60 for i in range(20)]
    text = "\n\n".join(paragraphs)
    for size in (200, 500, 1200):
        for chunk in split_text(text, size, 50):
            assert 0 < len(chunk) <= size


def test_paragraphs_are_preferred_and_kept_intact():
    a, b, c = "A" * 500, "B" * 500, "C" * 500
    chunks = split_text(f"{a}\n\n{b}\n\n{c}", 1200, 200)
    assert chunks == [f"{a}\n\n{b}", c]


def test_sentence_fallback_ends_chunks_at_sentence_boundaries():
    sentences = [f"This is sentence number {i} and it keeps going for a while." for i in range(40)]
    text = " ".join(sentences)  # one huge paragraph, no \n\n anywhere
    chunks = split_text(text, 300, 60)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.endswith(".")
        assert len(chunk) <= 300


def test_overlap_carries_context_between_chunks():
    sentences = [f"Sentence {i} is here." for i in range(50)]
    chunks = split_text(" ".join(sentences), 200, 80)
    assert len(chunks) > 2
    for previous, current in zip(chunks, chunks[1:], strict=False):
        # The carried tail of the previous chunk must open the next chunk.
        assert current.split(".")[0] + "." in previous


def test_hard_cut_overlap_is_exact():
    text = "".join(str(i % 10) for i in range(3000))  # no paragraph or sentence breaks
    size, overlap = 1000, 200
    chunks = split_text(text, size, overlap)
    assert all(len(chunk) <= size for chunk in chunks)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous[-overlap:] == current[:overlap]
    # Removing each chunk's leading overlap reconstructs the original text.
    rebuilt = chunks[0] + "".join(chunk[overlap:] for chunk in chunks[1:])
    assert rebuilt == text


def test_control_characters_are_stripped():
    chunks = split_text("hello\x00wor\x07ld", 100, 10)
    assert chunks == ["helloworld"]


def test_turkish_text_survives_chunking():
    paragraphs = [
        "Türkiye'nin başkenti Ankara'dır. İstanbul ise en kalabalık şehirdir.",
        "Öğrenciler sınavda ğ, ü, ş, ı, ö ve ç harflerini doğru kullanmalıdır.",
        "Çekoslovakyalılaştıramadıklarımızdan mısınız? " * 10,
    ]
    text = "\n\n".join(paragraphs)
    chunks = split_text(text, 150, 30)
    assert chunks
    joined = " ".join(chunks)
    for special in "ğüşıöçİ":
        assert special in joined
    for chunk in chunks:
        assert chunk.strip()
        assert len(chunk) <= 150


def test_chunk_pages_metadata_integrity():
    pages = [
        Page(text="First page. " + "alpha " * 100, page_number=1),
        Page(text="", page_number=2),  # empty pages contribute no chunks
        Page(text="Third page. " + "beta " * 100, page_number=3),
    ]
    chunks = chunk_pages(
        pages, doc_id="doc-1", filename="report.pdf", chunk_size=200, chunk_overlap=40
    )
    assert chunks
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.doc_id == "doc-1" and c.filename == "report.pdf" for c in chunks)
    pages_seen = {c.page for c in chunks}
    assert pages_seen == {1, 3}
    # Page order is preserved: all page-1 chunks come before page-3 chunks.
    page_sequence = [c.page for c in chunks]
    assert page_sequence == sorted(page_sequence)
