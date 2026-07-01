"""Pure text chunking: pages -> chunks with metadata.

Character-based recursive splitting. When a text exceeds the chunk size the
split preference is: paragraph boundaries -> sentence boundaries -> hard cut.
Consecutive chunks share up to ``chunk_overlap`` characters of context so
retrieval never loses meaning at a boundary. Empty or whitespace-only chunks
are never emitted; ASCII control characters are stripped.
"""

import re
from dataclasses import dataclass

from app.core.parsing import Page

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# (split pattern, joiner used when merging parts back into chunks)
_LEVELS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\n{2,}"), "\n\n"),  # paragraphs
    (re.compile(r"(?<=[.!?…])\s+"), " "),  # sentences
]


@dataclass(frozen=True)
class Chunk:
    text: str
    doc_id: str
    filename: str
    page: int
    chunk_index: int


def chunk_pages(
    pages: list[Page],
    *,
    doc_id: str,
    filename: str,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Split every page and attach metadata. chunk_index runs across pages."""
    chunks: list[Chunk] = []
    for page in pages:
        for text in split_text(page.text, chunk_size, chunk_overlap):
            chunks.append(
                Chunk(
                    text=text,
                    doc_id=doc_id,
                    filename=filename,
                    page=page.page_number,
                    chunk_index=len(chunks),
                )
            )
    return chunks


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split raw text into chunks of at most ``chunk_size`` characters."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must satisfy 0 <= overlap < chunk_size")

    cleaned = _CONTROL_CHARS.sub("", text).strip()
    if not cleaned:
        return []
    pieces = _split_recursive(cleaned, chunk_size, chunk_overlap, level=0)
    return [piece.strip() for piece in pieces if piece.strip()]


def _split_recursive(text: str, size: int, overlap: int, level: int) -> list[str]:
    if len(text) <= size:
        return [text]
    if level >= len(_LEVELS):
        return _hard_cut(text, size, overlap)

    pattern, joiner = _LEVELS[level]
    parts = [part for part in pattern.split(text) if part.strip()]
    if len(parts) <= 1:
        return _split_recursive(text, size, overlap, level + 1)

    pieces: list[str] = []
    for part in parts:
        if len(part) > size:
            pieces.extend(_split_recursive(part, size, overlap, level + 1))
        else:
            pieces.append(part)
    return _merge(pieces, size, overlap, joiner)


def _merge(pieces: list[str], size: int, overlap: int, joiner: str) -> list[str]:
    """Greedily pack pieces into chunks, carrying overlap into each new chunk."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for piece in pieces:
        joiner_len = len(joiner) if current else 0
        if current and current_len + joiner_len + len(piece) > size:
            chunks.append(joiner.join(current))
            current, current_len = _carry_tail(current, joiner, overlap)
            # Drop the carried context if it would push this chunk over size.
            if current and current_len + len(joiner) + len(piece) > size:
                current, current_len = [], 0
        current.append(piece)
        current_len += len(piece) + (len(joiner) if len(current) > 1 else 0)

    if current:
        chunks.append(joiner.join(current))
    return chunks


def _carry_tail(items: list[str], joiner: str, overlap: int) -> tuple[list[str], int]:
    """Trailing items of a flushed chunk, at most ``overlap`` characters total."""
    carry: list[str] = []
    carry_len = 0
    for item in reversed(items):
        extra = len(item) + (len(joiner) if carry else 0)
        if carry_len + extra > overlap:
            break
        carry.insert(0, item)
        carry_len += extra
    return carry, carry_len


def _hard_cut(text: str, size: int, overlap: int) -> list[str]:
    """Fixed-size windows sharing exactly ``overlap`` characters."""
    pieces: list[str] = []
    start = 0
    while True:
        end = min(start + size, len(text))
        pieces.append(text[start:end])
        if end == len(text):
            return pieces
        start = end - overlap
