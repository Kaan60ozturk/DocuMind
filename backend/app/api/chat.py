"""SSE chat endpoint: POST a question, receive a grounded, cited token stream."""

import json
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.rag import answer_events
from app.schemas import MAX_HISTORY_TURNS, ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


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
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx et al.)
        },
    )
