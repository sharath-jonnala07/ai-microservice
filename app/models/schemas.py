from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class Citation(BaseModel):
    title: str
    url: AnyHttpUrl
    publisher: str
    document_type: str
    updated_at: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=600)
    conversation_id: str | None = Field(default=None, max_length=100)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ChatResponse(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["answer", "refusal", "insufficient_data", "error"]
    answer: str
    citation: Citation | None = None
    last_updated_from_sources: str = "Unavailable"
    refusal_reason: str | None = None
    error_code: str | None = None
    latency_ms: int | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    environment: str
    indexed_sources: int
    groq_configured: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SourceRecord(BaseModel):
    source_id: str
    title: str
    url: AnyHttpUrl
    authority: Literal["groww", "amfi", "sebi"]
    document_type: str
    enabled: bool = True
    allow_for_answers: bool = True
    tags: list[str] = Field(default_factory=list)
    scheme_names: list[str] = Field(default_factory=list)
    priority: int = 50
    published_at: str | None = None
    notes: str | None = None


class ChunkRecord(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str
    source_url: AnyHttpUrl
    authority: str
    document_type: str
    published_at: str | None = None
    chunk_index: int
    text: str
    tags: list[str] = Field(default_factory=list)
    scheme_names: list[str] = Field(default_factory=list)
