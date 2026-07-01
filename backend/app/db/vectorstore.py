"""Thin ChromaDB wrapper: add / query / delete vectors by document.

Embeddings are always passed in explicitly — Chroma's built-in embedder is
never used, so the embedding model stays a single, swappable choice.
"""

from dataclasses import dataclass
from pathlib import Path

import chromadb

from app.core.chunking import Chunk

_COLLECTION_NAME = "docmind"


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    doc_id: str
    filename: str
    page: int
    chunk_index: int
    similarity: float


class VectorStore:
    def __init__(self, persist_dir: Path) -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        self._collection.add(
            ids=[f"{chunk.doc_id}:{chunk.chunk_index}" for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "doc_id": chunk.doc_id,
                    "filename": chunk.filename,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
        )

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        total = self.count()
        if total == 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, total),
            include=["documents", "metadatas", "distances"],
        )
        retrieved = [
            RetrievedChunk(
                text=text,
                doc_id=str(meta["doc_id"]),
                filename=str(meta["filename"]),
                page=int(meta["page"]),
                chunk_index=int(meta["chunk_index"]),
                # Chroma returns cosine distance; similarity = 1 - distance.
                similarity=1.0 - float(distance),
            )
            for text, meta, distance in zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
                strict=True,
            )
        ]
        return sorted(retrieved, key=lambda chunk: chunk.similarity, reverse=True)

    def delete_document(self, doc_id: str) -> None:
        self._collection.delete(where={"doc_id": doc_id})

    def count(self) -> int:
        return self._collection.count()
