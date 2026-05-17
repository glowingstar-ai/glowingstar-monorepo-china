"""Schemas for the USF defense workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UsfDefenseTurn(BaseModel):
    """One completed defense turn."""

    round_index: int = Field(..., ge=0, le=4)
    question: str = Field(..., min_length=1)
    answer_text: str = ""
    audio_transcript: str | None = None
    self_rating: int | None = Field(default=None, ge=1, le=10)
    answered_at: datetime | None = None


class UsfSessionStartRequest(BaseModel):
    """Create a USF defense session."""

    student_id: str = Field(..., min_length=1)


class UsfSessionStartResponse(BaseModel):
    """Result returned after creating a USF defense session."""

    session_id: str
    started_at: datetime
    persistence_enabled: bool


class UsfSessionSnapshotRequest(BaseModel):
    """Persist the latest recoverable USF workflow state."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    stage: str = Field(..., min_length=1)
    module_id: str | None = None
    module_number: int | None = Field(default=None, ge=1)
    module_topic: str | None = None
    module_week: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    learned_response: str | None = None
    remaining_questions_response: str | None = None
    current_round_index: int = Field(default=0, ge=0, le=4)
    completed_round_count: int = Field(default=0, ge=0, le=5)
    defense_turns: list[UsfDefenseTurn] = Field(default_factory=list)
    completed_at: datetime | None = None


class UsfSessionSnapshotResponse(BaseModel):
    """Acknowledgement for USF snapshot persistence."""

    saved_at: datetime
    persistence_enabled: bool


class UsfEventRequest(BaseModel):
    """Append a USF workflow event."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    stage: str | None = None
    round_index: int | None = Field(default=None, ge=0, le=4)
    client_timestamp: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class UsfEventResponse(BaseModel):
    """Acknowledgement for USF event ingestion."""

    event_id: str
    recorded_at: datetime
    persistence_enabled: bool


class UsfDefenseQuestionRequest(BaseModel):
    """Generate and save one USF defense question."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    round_index: int = Field(..., ge=0, le=4)
    module_id: str = Field(..., min_length=1)
    module_number: int = Field(..., ge=1)
    module_topic: str = Field(..., min_length=1)
    module_week: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    learned_response: str | None = None
    remaining_questions_response: str | None = None
    previous_turns: list[UsfDefenseTurn] = Field(default_factory=list)


class UsfDefenseQuestionResponse(BaseModel):
    """One generated defense question."""

    model: str
    round_index: int
    question: str
    generated_at: datetime
    persistence_enabled: bool


class UsfTranscriptionRequest(BaseModel):
    """Transcribe and persist browser-recorded audio."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    round_index: int = Field(..., ge=0, le=4)
    audio_base64: str = Field(..., min_length=1)
    audio_mime_type: str | None = None
    persist_audio: bool = True


class UsfTranscriptionResponse(BaseModel):
    """Text returned from a USF defense recording."""

    text: str
    saved_at: datetime
    persistence_enabled: bool
    audio_bucket: str | None = None
    audio_key: str | None = None
    audio_url: str | None = None
    audio_content_type: str | None = None
    audio_size_bytes: int | None = None


class UsfDefenseTurnRequest(UsfDefenseTurn):
    """Persist a completed USF defense turn."""

    session_id: str = Field(..., min_length=1)
    student_id: str = Field(..., min_length=1)
    module_id: str = Field(..., min_length=1)


class UsfDefenseTurnResponse(BaseModel):
    """Acknowledgement for defense-turn persistence."""

    saved_at: datetime
    persistence_enabled: bool
    completed_round_count: int = Field(..., ge=0, le=5)


class UsfErrorRecord(BaseModel):
    """Structured USF error payload."""

    session_id: str = Field(..., min_length=1)
    student_id: str | None = None
    stage: str = Field(..., min_length=1)
    error_scope: str = Field(..., min_length=1)
    error_message: str = Field(..., min_length=1)
    raw_error: str | None = None
    round_index: int | None = Field(default=None, ge=0, le=4)
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsfResearchSessionSummary(BaseModel):
    """Compact session summary for the internal USF dashboard."""

    session_id: str
    student_id: str | None = None
    stage: str | None = None
    module_id: str | None = None
    module_number: int | None = None
    module_topic: str | None = None
    module_week: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    learned_response: str | None = None
    remaining_questions_response: str | None = None
    current_round_index: int | None = None
    completed_round_count: int = Field(default=0, ge=0)
    defense_turns: list[UsfDefenseTurn] = Field(default_factory=list)
    question_count: int = Field(default=0, ge=0)
    transcript_count: int = Field(default=0, ge=0)
    defense_turn_count: int = Field(default=0, ge=0)
    event_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    last_seen_at: datetime | None = None
    completed_at: datetime | None = None


class UsfResearchStudentSummary(BaseModel):
    """Grouped USF student summary containing recent sessions."""

    student_id: str
    session_count: int = Field(default=0, ge=0)
    last_seen_at: datetime | None = None
    sessions: list[UsfResearchSessionSummary] = Field(default_factory=list)


class UsfResearchOverviewResponse(BaseModel):
    """Top-level USF activity index for internal review."""

    persistence_enabled: bool
    generated_at: datetime
    session_count: int = Field(default=0, ge=0)
    students: list[UsfResearchStudentSummary] = Field(default_factory=list)


class UsfResearchEventRecord(BaseModel):
    """One stored USF interaction event."""

    item_key: str
    event_id: str | None = None
    student_id: str | None = None
    event_type: str | None = None
    stage: str | None = None
    round_index: int | None = None
    client_timestamp: datetime | None = None
    recorded_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class UsfResearchErrorRecord(BaseModel):
    """One stored USF error entry."""

    item_key: str
    error_id: str | None = None
    student_id: str | None = None
    stage: str | None = None
    error_scope: str | None = None
    error_message: str | None = None
    raw_error: str | None = None
    round_index: int | None = None
    request_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime | None = None


class UsfResearchArtifactRecord(BaseModel):
    """One stored USF defense artifact."""

    item_key: str
    item_type: str
    student_id: str | None = None
    module_id: str | None = None
    module_number: int | None = None
    module_topic: str | None = None
    round_index: int | None = None
    question: str | None = None
    answer_text: str | None = None
    audio_transcript: str | None = None
    self_rating: int | None = None
    transcript: str | None = None
    audio_mime_type: str | None = None
    audio_bucket: str | None = None
    audio_key: str | None = None
    audio_url: str | None = None
    audio_content_type: str | None = None
    audio_size_bytes: int | None = None
    model: str | None = None
    prompt: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)
    learned_response: str | None = None
    remaining_questions_response: str | None = None
    previous_turns: list[dict[str, Any]] = Field(default_factory=list)
    answered_at: datetime | None = None
    created_at: datetime | None = None


class UsfResearchSessionDetailResponse(BaseModel):
    """Full activity drilldown for one USF defense session."""

    persistence_enabled: bool
    generated_at: datetime
    session: UsfResearchSessionSummary | None = None
    generated_questions: list[UsfResearchArtifactRecord] = Field(default_factory=list)
    transcripts: list[UsfResearchArtifactRecord] = Field(default_factory=list)
    defense_turns: list[UsfResearchArtifactRecord] = Field(default_factory=list)
    events: list[UsfResearchEventRecord] = Field(default_factory=list)
    errors: list[UsfResearchErrorRecord] = Field(default_factory=list)
