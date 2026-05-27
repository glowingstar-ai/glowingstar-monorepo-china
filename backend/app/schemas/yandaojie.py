"""Schemas for the Yandaojie (研道街) defense workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class YandaojieReflectionEntry(BaseModel):
    """One reflection entry per learning objective."""

    objective_index: int = Field(..., ge=0)
    learned: str = ""
    questions: str = ""


class YandaojieDefenseTurn(BaseModel):
    """One completed defense turn."""

    round_index: int = Field(..., ge=0, le=4)
    question: str = Field(..., min_length=1)
    answer_text: str = ""
    answered_at: datetime | None = None


class YandaojieSessionStartRequest(BaseModel):
    """Create a Yandaojie defense session."""

    student_id: str = Field(..., min_length=1)


class YandaojieSessionStartResponse(BaseModel):
    """Result returned after creating a Yandaojie defense session."""

    session_id: str
    started_at: datetime
    persistence_enabled: bool


class YandaojieSessionSnapshotRequest(BaseModel):
    """Persist the latest recoverable Yandaojie workflow state."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    stage: str = Field(..., min_length=1)
    subject_id: str | None = None
    subject_label: str | None = None
    subject_topic: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    reflections: list[YandaojieReflectionEntry] = Field(default_factory=list)
    current_round_index: int = Field(default=0, ge=0, le=4)
    completed_round_count: int = Field(default=0, ge=0, le=5)
    defense_turns: list[YandaojieDefenseTurn] = Field(default_factory=list)
    completed_at: datetime | None = None


class YandaojieSessionSnapshotResponse(BaseModel):
    """Acknowledgement for Yandaojie snapshot persistence."""

    saved_at: datetime
    persistence_enabled: bool


class YandaojieEventRequest(BaseModel):
    """Append a Yandaojie workflow event."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    stage: str | None = None
    round_index: int | None = Field(default=None, ge=0, le=4)
    client_timestamp: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class YandaojieEventResponse(BaseModel):
    """Acknowledgement for Yandaojie event ingestion."""

    event_id: str
    recorded_at: datetime
    persistence_enabled: bool


class YandaojieDefenseQuestionRequest(BaseModel):
    """Generate one Yandaojie defense question."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    round_index: int = Field(..., ge=0, le=4)
    subject_id: str = Field(..., min_length=1)
    subject_label: str = Field(..., min_length=1)
    subject_topic: str = Field(..., min_length=1)
    learning_objectives: list[str] = Field(default_factory=list)
    reflections: list[YandaojieReflectionEntry] = Field(default_factory=list)
    previous_turns: list[YandaojieDefenseTurn] = Field(default_factory=list)


class YandaojieDefenseQuestionResponse(BaseModel):
    """One generated defense question."""

    model: str
    round_index: int
    question: str
    generated_at: datetime
    persistence_enabled: bool


class YandaojieDefenseTurnRequest(YandaojieDefenseTurn):
    """Persist a completed Yandaojie defense turn."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    subject_id: str = Field(..., min_length=1)


class YandaojieDefenseTurnResponse(BaseModel):
    """Acknowledgement for defense-turn persistence."""

    saved_at: datetime
    persistence_enabled: bool
    completed_round_count: int = Field(..., ge=0, le=5)


class YandaojieErrorRecord(BaseModel):
    """Structured Yandaojie error payload."""

    session_id: str = Field(..., min_length=1)
    student_id: str | None = None
    stage: str = Field(..., min_length=1)
    error_scope: str = Field(..., min_length=1)
    error_message: str = Field(..., min_length=1)
    raw_error: str | None = None
    round_index: int | None = Field(default=None, ge=0, le=4)
    metadata: dict[str, Any] = Field(default_factory=dict)
