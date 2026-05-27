"""MongoDB persistence for the Yandaojie defense workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.schemas.yandaojie import (
    YandaojieDefenseQuestionRequest,
    YandaojieDefenseTurnRequest,
    YandaojieErrorRecord,
    YandaojieEventRequest,
    YandaojieSessionSnapshotRequest,
    YandaojieSessionStartRequest,
)


class YandaojiePersistenceError(RuntimeError):
    """Raised when Yandaojie persistence operations fail."""


@dataclass
class YandaojieSessionCreated:
    """Created session metadata."""

    session_id: str
    started_at: datetime


class YandaojiePersistenceService:
    """Persist Yandaojie sessions, events, defense artifacts, and errors to MongoDB."""

    def __init__(self, *, mongodb_uri: str | None, database_name: str = "yandaojie") -> None:
        self._enabled = bool(mongodb_uri)
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None

        if mongodb_uri:
            self._client = AsyncIOMotorClient(mongodb_uri)
            self._db = self._client[database_name]

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def create_session(
        self, payload: YandaojieSessionStartRequest
    ) -> YandaojieSessionCreated:
        session_id = uuid4().hex
        started_at = datetime.now(timezone.utc)

        if not self._enabled or self._db is None:
            return YandaojieSessionCreated(session_id=session_id, started_at=started_at)

        try:
            await self._db.sessions.insert_one({
                "session_id": session_id,
                "student_id": payload.student_id,
                "stage": "student-id",
                "started_at": started_at,
                "last_seen_at": started_at,
                "current_round_index": 0,
                "completed_round_count": 0,
            })
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to create Yandaojie session in MongoDB"
            ) from exc

        return YandaojieSessionCreated(session_id=session_id, started_at=started_at)

    async def save_snapshot(self, payload: YandaojieSessionSnapshotRequest) -> datetime:
        saved_at = datetime.now(timezone.utc)
        if not self._enabled or self._db is None:
            return saved_at

        try:
            await self._db.sessions.update_one(
                {"session_id": payload.session_id},
                {
                    "$set": {
                        "student_id": payload.student_id,
                        "stage": payload.stage,
                        "subject_id": payload.subject_id,
                        "subject_label": payload.subject_label,
                        "subject_topic": payload.subject_topic,
                        "learning_objectives": payload.learning_objectives,
                        "reflections": [
                            r.model_dump(mode="json") for r in payload.reflections
                        ],
                        "current_round_index": payload.current_round_index,
                        "completed_round_count": payload.completed_round_count,
                        "defense_turns": [
                            turn.model_dump(mode="json")
                            for turn in payload.defense_turns
                        ],
                        "last_seen_at": saved_at,
                        "completed_at": payload.completed_at,
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to save Yandaojie snapshot to MongoDB"
            ) from exc

        return saved_at

    async def append_event(self, payload: YandaojieEventRequest) -> tuple[str, datetime]:
        event_id = uuid4().hex
        recorded_at = datetime.now(timezone.utc)
        if not self._enabled or self._db is None:
            return event_id, recorded_at

        try:
            await self._db.events.insert_one({
                "event_id": event_id,
                "session_id": payload.session_id,
                "student_id": payload.student_id,
                "event_type": payload.event_type,
                "stage": payload.stage,
                "round_index": payload.round_index,
                "client_timestamp": payload.client_timestamp,
                "recorded_at": recorded_at,
                "payload": payload.payload,
            })
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to append Yandaojie event to MongoDB"
            ) from exc

        return event_id, recorded_at

    async def persist_generated_question(
        self,
        *,
        payload: YandaojieDefenseQuestionRequest,
        question: str,
        model: str,
        prompt: str,
        generated_at: datetime,
    ) -> datetime:
        if not self._enabled or self._db is None:
            return generated_at

        try:
            await self._db.defense_questions.insert_one({
                "session_id": payload.session_id,
                "student_id": payload.student_id,
                "round_index": payload.round_index,
                "subject_id": payload.subject_id,
                "subject_label": payload.subject_label,
                "subject_topic": payload.subject_topic,
                "learning_objectives": payload.learning_objectives,
                "reflections": [
                    r.model_dump(mode="json") for r in payload.reflections
                ],
                "previous_turns": [
                    turn.model_dump(mode="json") for turn in payload.previous_turns
                ],
                "model": model,
                "prompt": prompt,
                "question": question,
                "created_at": generated_at,
            })
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to persist Yandaojie defense question to MongoDB"
            ) from exc

        return generated_at

    async def persist_defense_turn(
        self, payload: YandaojieDefenseTurnRequest
    ) -> tuple[datetime, int]:
        saved_at = datetime.now(timezone.utc)
        completed_round_count = payload.round_index + 1
        if not self._enabled or self._db is None:
            return saved_at, completed_round_count

        try:
            await self._db.defense_turns.insert_one({
                "session_id": payload.session_id,
                "student_id": payload.student_id,
                "subject_id": payload.subject_id,
                "round_index": payload.round_index,
                "question": payload.question,
                "answer_text": payload.answer_text,
                "answered_at": payload.answered_at or saved_at,
                "created_at": saved_at,
            })
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to persist Yandaojie defense turn to MongoDB"
            ) from exc

        return saved_at, completed_round_count

    async def record_error(self, payload: YandaojieErrorRecord) -> tuple[str, datetime]:
        error_id = uuid4().hex
        recorded_at = datetime.now(timezone.utc)
        if not self._enabled or self._db is None:
            return error_id, recorded_at

        try:
            await self._db.errors.insert_one({
                "error_id": error_id,
                "session_id": payload.session_id,
                "student_id": payload.student_id,
                "stage": payload.stage,
                "error_scope": payload.error_scope,
                "error_message": payload.error_message,
                "raw_error": payload.raw_error,
                "round_index": payload.round_index,
                "metadata": payload.metadata,
                "recorded_at": recorded_at,
            })
        except Exception as exc:
            raise YandaojiePersistenceError(
                "Failed to record Yandaojie error to MongoDB"
            ) from exc

        return error_id, recorded_at
