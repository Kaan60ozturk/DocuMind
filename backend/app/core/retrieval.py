"""Query-time retrieval: embed the question, rank stored chunks by similarity."""

from app.db.vectorstore import RetrievedChunk, VectorStore
from app.providers.base import EmbeddingProvider


def retrieve(
    question: str,
    *,
    embedder: EmbeddingProvider,
    vectorstore: VectorStore,
    top_k: int,
) -> list[RetrievedChunk]:
    """Return up to ``top_k`` chunks sorted by similarity (best first).

    Returns an empty list when the store holds no vectors — callers use that
    to short-circuit before ever talking to the LLM.
    """
    if vectorstore.count() == 0:
        return []
    [embedding] = embedder.embed_texts([question])
    return vectorstore.query(embedding, top_k)
