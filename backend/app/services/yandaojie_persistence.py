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
        reasoning_content: str | None = None,
        targeted_objectives: list[dict] | None = None,
        diagnoses: dict | None = None,
    ) -> datetime:
        if not self._enabled or self._db is None:
            return generated_at

        try:
            doc = {
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
                "reasoning_content": reasoning_content,
                "targeted_objectives": targeted_objectives,
                "diagnoses": diagnoses,
                "created_at": generated_at,
            }
            await self._db.defense_questions.insert_one(doc)
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

    async def get_research_overview(self, limit: int | None = None) -> dict[str, Any]:
        """Return all sessions grouped by student for internal research."""
        if not self._enabled or self._db is None:
            return {"persistence_enabled": False, "generated_at": datetime.now(timezone.utc).isoformat(), "session_count": 0, "students": []}

        sessions_cursor = self._db.sessions.find().sort("started_at", -1)
        if limit:
            sessions_cursor = sessions_cursor.limit(limit)
        sessions = await sessions_cursor.to_list(length=limit or 1000)

        students_map: dict[str, dict[str, Any]] = {}
        for s in sessions:
            sid = s.get("student_id", "unknown")
            if sid not in students_map:
                students_map[sid] = {"student_id": sid, "session_count": 0, "last_seen_at": None, "sessions": []}
            students_map[sid]["session_count"] += 1
            last_seen = s.get("last_seen_at") or s.get("started_at")
            if last_seen and (not students_map[sid]["last_seen_at"] or str(last_seen) > str(students_map[sid]["last_seen_at"])):
                students_map[sid]["last_seen_at"] = last_seen

            event_count = await self._db.events.count_documents({"session_id": s["session_id"]})
            error_count = await self._db.errors.count_documents({"session_id": s["session_id"]})
            question_count = await self._db.defense_questions.count_documents({"session_id": s["session_id"]})
            turn_count = await self._db.defense_turns.count_documents({"session_id": s["session_id"]})

            students_map[sid]["sessions"].append({
                "session_id": s["session_id"],
                "student_id": s.get("student_id"),
                "stage": s.get("stage"),
                "subject_id": s.get("subject_id"),
                "subject_label": s.get("subject_label"),
                "subject_topic": s.get("subject_topic"),
                "learning_objectives": s.get("learning_objectives", []),
                "reflections": s.get("reflections", []),
                "current_round_index": s.get("current_round_index", 0),
                "completed_round_count": s.get("completed_round_count", 0),
                "defense_turns": s.get("defense_turns", []),
                "event_count": event_count,
                "error_count": error_count,
                "question_count": question_count,
                "defense_turn_count": turn_count,
                "started_at": s.get("started_at"),
                "last_seen_at": s.get("last_seen_at"),
                "completed_at": s.get("completed_at"),
            })

        return {
            "persistence_enabled": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session_count": len(sessions),
            "students": list(students_map.values()),
        }

    async def get_session_research_detail(self, session_id: str) -> dict[str, Any]:
        """Return full details for a single session."""
        if not self._enabled or self._db is None:
            return {"persistence_enabled": False, "generated_at": datetime.now(timezone.utc).isoformat(), "session": None, "events": [], "errors": [], "defense_turns": [], "generated_questions": []}

        session = await self._db.sessions.find_one({"session_id": session_id})
        events = await self._db.events.find({"session_id": session_id}).sort("recorded_at", 1).to_list(500)
        errors = await self._db.errors.find({"session_id": session_id}).sort("recorded_at", 1).to_list(500)
        questions = await self._db.defense_questions.find({"session_id": session_id}).sort("round_index", 1).to_list(500)
        turns = await self._db.defense_turns.find({"session_id": session_id}).sort("round_index", 1).to_list(500)

        def serialize(doc: dict) -> dict:
            d = {k: v for k, v in doc.items() if k != "_id"}
            for k, v in d.items():
                if isinstance(v, datetime):
                    d[k] = v.isoformat()
            return d

        return {
            "persistence_enabled": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "session": serialize(session) if session else None,
            "events": [serialize(e) for e in events],
            "errors": [serialize(e) for e in errors],
            "defense_turns": [serialize(t) for t in turns],
            "generated_questions": [serialize(q) for q in questions],
        }

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
