"""SSE chat endpoint: POST a question, receive a grounded, cited token stream."""

import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.rag import answer_events
from app.schemas import MAX_HISTORY_TURNS, ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _frame(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("")
def chat(request: Request, payload: ChatRequest) -> StreamingResponse:
    state = request.app.state
    # Never trust the client with limits: truncate history server-side too.
    history = payload.history[-MAX_HISTORY_TURNS:]

    def sse_stream() -> Iterator[str]:
        events = answer_events(
            payload.question,
            history,
            settings=state.settings,
            embedder=state.embedder,
            llm=state.llm,
            vectorstore=state.vectorstore,
        )
        # The contract promises a terminal event on every path. Provider
        # failures already arrive as 'error' events; this catch-all covers
        # everything else (vector store faults, bugs) once headers are sent.
        try:
            for event in events:
                yield _frame(event)
        except Exception:
            logger.exception("Chat stream failed unexpectedly")
            yield _frame(
                {
                    "type": "error",
                    "message": "Something went wrong while answering. Please try again.",
                }
            )

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx et al.)
        },
    )
