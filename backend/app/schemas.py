"""Pydantic request/response models for the public API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_QUESTION_LENGTH = 4000
MAX_HISTORY_TURNS = 6
MAX_HISTORY_ITEMS = 100  # parse guard; the chat endpoint keeps only the last 6


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    pages: int
    chunks: int
    size_bytes: int
    status: str
    created_at: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def _truncate_content(cls, value: str) -> str:
        # History is context, not input: silently clamp instead of rejecting,
        # so a long earlier answer never bricks the rest of the conversation.
        return value[:MAX_QUESTION_LENGTH]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_ITEMS)


class SourceOut(BaseModel):
    n: int
    doc_id: str
    filename: str
    page: int
    snippet: str
    score: float
