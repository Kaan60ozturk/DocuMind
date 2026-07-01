"""Prompt building and streaming generation for grounded, cited answers."""

import logging
from collections.abc import Iterator
from typing import Any

from app.config import Settings
from app.core.retrieval import retrieve
from app.db.vectorstore import RetrievedChunk, VectorStore
from app.providers.base import EmbeddingProvider, LLMProvider, ProviderError
from app.schemas import ChatTurn

logger = logging.getLogger(__name__)

SNIPPET_LENGTH = 300

NO_DOCUMENTS_MESSAGE = (
    "You haven't uploaded any documents yet. "
    "Upload a PDF, DOCX, TXT or Markdown file in the sidebar, then ask your question again."
)

RAG_PROMPT = """You are DocuMind, an assistant that answers strictly from the provided document excerpts.

Rules:
- Use ONLY the numbered excerpts below. If the answer is not in them, say plainly that you could not find it in the uploaded documents and suggest rephrasing or uploading a relevant document. Never use outside knowledge, never invent content.
- Cite sources inline as [1], [2] matching excerpt numbers. Every factual claim needs at least one citation.
- Answer in the same language as the user's question.
- Be concise. Short paragraphs. No preamble.

Excerpts:
{context}

Conversation so far (may be empty):
{history}

Question: {question}"""


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = [
        f"[{number}] ({chunk.filename}, p.{chunk.page})\n{chunk.text}"
        for number, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(blocks)


def format_history(history: list[ChatTurn]) -> str:
    labels = {"user": "User", "assistant": "Assistant"}
    return "\n".join(f"{labels[turn.role]}: {turn.content}" for turn in history)


def build_prompt(question: str, history: list[ChatTurn], chunks: list[RetrievedChunk]) -> str:
    return RAG_PROMPT.format(
        context=format_context(chunks),
        history=format_history(history),
        question=question,
    )


def _sources_payload(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    return [
        {
            "n": number,
            "doc_id": chunk.doc_id,
            "filename": chunk.filename,
            "page": chunk.page,
            "snippet": chunk.text[:SNIPPET_LENGTH],
            "score": round(chunk.similarity, 4),
        }
        for number, chunk in enumerate(chunks, start=1)
    ]


def answer_events(
    question: str,
    history: list[ChatTurn],
    *,
    settings: Settings,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    vectorstore: VectorStore,
) -> Iterator[dict[str, Any]]:
    """Yield the chat event stream: sources -> token* -> done (or error).

    Every failure becomes a single ``error`` event with a user-safe message;
    internals only ever go to the server log.
    """
    if vectorstore.count() == 0:
        yield {"type": "sources", "sources": []}
        yield {"type": "token", "text": NO_DOCUMENTS_MESSAGE}
        yield {"type": "done"}
        return

    try:
        chunks = retrieve(
            question, embedder=embedder, vectorstore=vectorstore, top_k=settings.top_k
        )
    except ProviderError as exc:
        yield {"type": "error", "message": str(exc)}
        return

    if chunks and chunks[0].similarity < settings.min_similarity:
        logger.info(
            "Low best similarity %.3f for question %r — answering anyway, prompt enforces honesty",
            chunks[0].similarity,
            question[:80],
        )

    yield {"type": "sources", "sources": _sources_payload(chunks)}

    prompt = build_prompt(question, history, chunks)
    try:
        for token in llm.stream(prompt):
            yield {"type": "token", "text": token}
    except ProviderError as exc:
        yield {"type": "error", "message": str(exc)}
        return

    yield {"type": "done"}
