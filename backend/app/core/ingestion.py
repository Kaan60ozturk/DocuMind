"""Ingestion pipeline: parse -> chunk -> embed -> index -> register."""

import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.core.chunking import chunk_pages
from app.core.parsing import parse_file
from app.db.documents import DocumentRecord, DocumentRegistry
from app.db.vectorstore import VectorStore
from app.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class EmptyDocumentError(ValueError):
    """The file parsed successfully but contains no extractable text."""


def ingest_file(
    stored_path: Path,
    display_name: str,
    *,
    settings: Settings,
    embedder: EmbeddingProvider,
    vectorstore: VectorStore,
    registry: DocumentRegistry,
    doc_id: str | None = None,
) -> DocumentRecord:
    """Run the full pipeline for one stored file and return its registry record."""
    doc_id = doc_id or str(uuid.uuid4())
    started = time.perf_counter()

    pages = parse_file(stored_path)
    chunks = chunk_pages(
        pages,
        doc_id=doc_id,
        filename=display_name,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    if not chunks:
        raise EmptyDocumentError(
            "No extractable text was found in the document. "
            "Scanned/image-only PDFs are not supported yet."
        )

    embeddings = embedder.embed_texts([chunk.text for chunk in chunks])
    vectorstore.add(chunks, embeddings)

    record = DocumentRecord(
        id=doc_id,
        filename=display_name,
        pages=len(pages),
        chunks=len(chunks),
        size_bytes=stored_path.stat().st_size,
        status="ready",
        created_at=datetime.now(UTC).isoformat(),
    )
    registry.add(record)

    logger.info(
        "Ingested %r: %d pages, %d chunks in %.2fs",
        display_name,
        len(pages),
        len(chunks),
        time.perf_counter() - started,
    )
    return record
