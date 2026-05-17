"""DynamoDB persistence for the USF defense workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Attr, Key

from app.core.config import Settings
from app.services.transcription import _extension_for_content_type
from app.schemas.usf import (
    UsfDefenseQuestionRequest,
    UsfDefenseTurnRequest,
    UsfErrorRecord,
    UsfEventRequest,
    UsfSessionSnapshotRequest,
    UsfSessionStartRequest,
    UsfTranscriptionRequest,
)


class UsfPersistenceError(RuntimeError):
    """Raised when USF persistence operations fail."""


@dataclass
class UsfSessionCreated:
    """Created session metadata."""

    session_id: str
    started_at: datetime


@dataclass
class UsfRecordingUpload:
    """Metadata for an uploaded USF defense recording."""

    bucket: str
    key: str
    url: str
    content_type: str
    size_bytes: int


class UsfPersistenceService:
    """Persist USF sessions, events, defense artifacts, and errors."""

    def __init__(self, settings: Settings) -> None:
        session_kwargs: dict[str, str] = {}
        if settings.aws_region_name:
            session_kwargs["region_name"] = settings.aws_region_name
        if settings.aws_profile:
            session_kwargs["profile_name"] = settings.aws_profile
        elif settings.aws_access_key_id and settings.aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            session_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key

        self._sessions_table_name = settings.aws_usf_sessions_table
        self._events_table_name = settings.aws_usf_events_table
        self._errors_table_name = settings.aws_usf_errors_table
        self._recordings_bucket = settings.aws_usf_recordings_bucket
        self._region = settings.aws_region_name
        self._enabled = bool(
            self._sessions_table_name and self._events_table_name and self._errors_table_name
        )
        self._recordings_enabled = bool(self._recordings_bucket)

        session = boto3.session.Session(**session_kwargs)
        self._dynamodb = session.resource("dynamodb")
        self._s3_client = session.client("s3")
        self._sessions_table = (
            self._dynamodb.Table(self._sessions_table_name)
            if self._sessions_table_name
            else None
        )
        self._events_table = (
            self._dynamodb.Table(self._events_table_name)
            if self._events_table_name
            else None
        )
        self._errors_table = (
            self._dynamodb.Table(self._errors_table_name)
            if self._errors_table_name
            else None
        )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def recordings_enabled(self) -> bool:
        return self._recordings_enabled

    def get_research_overview(self, *, limit: int | None = None) -> dict[str, Any]:
        """Return grouped USF student/session summaries for internal review."""

        generated_at = datetime.now(timezone.utc)
        if not self._enabled:
            return {
                "persistence_enabled": False,
                "generated_at": generated_at,
                "session_count": 0,
                "students": [],
            }

        meta_items = self._scan_items(
            self._sessions_table,
            filter_expression=Attr("item_key").eq("SESSION#META"),
        )
        sessions: list[dict[str, Any]] = []
        for item in meta_items:
            session = self._session_summary_from_item(item)
            session_id = session.get("session_id")
            if session_id:
                session.update(self._session_activity_counts(str(session_id)))
            sessions.append(session)

        sessions.sort(
            key=lambda item: item.get("last_seen_at") or item.get("started_at") or "",
            reverse=True,
        )
        if limit is not None:
            sessions = sessions[:limit]

        students_by_id: dict[str, dict[str, Any]] = {}
        for session in sessions:
            student_id = session.get("student_id") or "Unknown student"
            student = students_by_id.setdefault(
                student_id,
                {
                    "student_id": student_id,
                    "session_count": 0,
                    "last_seen_at": None,
                    "sessions": [],
                },
            )
            student["session_count"] += 1
            student["sessions"].append(session)
            last_seen_at = session.get("last_seen_at") or session.get("started_at")
            if last_seen_at and (
                not student["last_seen_at"] or str(last_seen_at) > str(student["last_seen_at"])
            ):
                student["last_seen_at"] = last_seen_at

        students = list(students_by_id.values())
        students.sort(key=lambda item: item.get("last_seen_at") or "", reverse=True)

        return {
            "persistence_enabled": True,
            "generated_at": generated_at,
            "session_count": len(sessions),
            "students": students,
        }

    def get_session_research_detail(self, session_id: str) -> dict[str, Any]:
        """Return all stored USF activity for one session."""

        generated_at = datetime.now(timezone.utc)
        if not self._enabled:
            return {
                "persistence_enabled": False,
                "generated_at": generated_at,
                "session": None,
                "generated_questions": [],
                "transcripts": [],
                "defense_turns": [],
                "events": [],
                "errors": [],
            }

        session_items = self._query_items(
            self._sessions_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )
        event_items = self._query_items(
            self._events_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )
        error_items = self._query_items(
            self._errors_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )

        session_meta: dict[str, Any] | None = None
        generated_questions: list[dict[str, Any]] = []
        transcripts: list[dict[str, Any]] = []
        defense_turns: list[dict[str, Any]] = []

        for item in session_items:
            item_key = str(item.get("item_key") or "")
            if item_key == "SESSION#META":
                session_meta = self._session_summary_from_item(item)
            elif item_key.startswith("ARTIFACT#QUESTION#"):
                generated_questions.append(self._artifact_from_item(item))
            elif item_key.startswith("ARTIFACT#TRANSCRIPT#"):
                transcripts.append(self._artifact_from_item(item))
            elif item_key.startswith("ARTIFACT#DEFENSE_TURN#"):
                defense_turns.append(self._artifact_from_item(item))

        generated_questions.sort(key=lambda item: item.get("created_at") or "")
        transcripts.sort(key=lambda item: item.get("created_at") or "")
        defense_turns.sort(key=lambda item: item.get("created_at") or "")

        return {
            "persistence_enabled": True,
            "generated_at": generated_at,
            "session": session_meta,
            "generated_questions": generated_questions,
            "transcripts": transcripts,
            "defense_turns": defense_turns,
            "events": [self._event_from_item(item) for item in event_items],
            "errors": [self._error_from_item(item) for item in error_items],
        }

    def create_session(self, payload: UsfSessionStartRequest) -> UsfSessionCreated:
        session_id = uuid4().hex
        started_at = datetime.now(timezone.utc)

        if not self._enabled:
            return UsfSessionCreated(session_id=session_id, started_at=started_at)

        self._put_item(
            self._sessions_table,
            {
                "session_id": session_id,
                "item_key": "SESSION#META",
                "item_type": "session_meta",
                "student_id": payload.student_id,
                "stage": "student-id",
                "started_at": started_at.isoformat(),
                "last_seen_at": started_at.isoformat(),
                "current_round_index": 0,
                "completed_round_count": 0,
            },
        )
        return UsfSessionCreated(session_id=session_id, started_at=started_at)

    def save_snapshot(self, payload: UsfSessionSnapshotRequest) -> datetime:
        saved_at = datetime.now(timezone.utc)
        if not self._enabled:
            return saved_at

        existing_meta = self._get_item(
            self._sessions_table,
            {"session_id": payload.session_id, "item_key": "SESSION#META"},
        )
        self._put_item(
            self._sessions_table,
            {
                "session_id": payload.session_id,
                "item_key": "SESSION#META",
                "item_type": "session_meta",
                "student_id": payload.student_id,
                "stage": payload.stage,
                "module_id": payload.module_id,
                "module_number": payload.module_number,
                "module_topic": payload.module_topic,
                "module_week": payload.module_week,
                "learning_objectives": payload.learning_objectives,
                "learned_response": payload.learned_response,
                "remaining_questions_response": payload.remaining_questions_response,
                "current_round_index": payload.current_round_index,
                "completed_round_count": payload.completed_round_count,
                "defense_turns": [
                    turn.model_dump(mode="json") for turn in payload.defense_turns
                ],
                "started_at": existing_meta.get("started_at") if existing_meta else None,
                "last_seen_at": saved_at.isoformat(),
                "completed_at": payload.completed_at.isoformat()
                if payload.completed_at
                else None,
            },
        )
        return saved_at

    def append_event(self, payload: UsfEventRequest) -> tuple[str, datetime]:
        event_id = uuid4().hex
        recorded_at = datetime.now(timezone.utc)
        if not self._enabled:
            return event_id, recorded_at

        self._put_item(
            self._events_table,
            {
                "session_id": payload.session_id,
                "item_key": f"EVENT#{recorded_at.isoformat()}#{event_id}",
                "event_id": event_id,
                "student_id": payload.student_id,
                "event_type": payload.event_type,
                "stage": payload.stage,
                "round_index": payload.round_index,
                "client_timestamp": payload.client_timestamp.isoformat()
                if payload.client_timestamp
                else None,
                "recorded_at": recorded_at.isoformat(),
                "payload": payload.payload,
            },
        )
        return event_id, recorded_at

    def persist_generated_question(
        self,
        *,
        payload: UsfDefenseQuestionRequest,
        question: str,
        model: str,
        prompt: str,
        generated_at: datetime,
    ) -> datetime:
        if not self._enabled:
            return generated_at

        self._put_item(
            self._sessions_table,
            {
                "session_id": payload.session_id,
                "item_key": (
                    f"ARTIFACT#QUESTION#{payload.round_index}"
                    f"#{generated_at.isoformat()}#{uuid4().hex}"
                ),
                "item_type": "artifact_defense_question",
                "student_id": payload.student_id,
                "round_index": payload.round_index,
                "module_id": payload.module_id,
                "module_number": payload.module_number,
                "module_topic": payload.module_topic,
                "learning_objectives": payload.learning_objectives,
                "learned_response": payload.learned_response,
                "remaining_questions_response": payload.remaining_questions_response,
                "previous_turns": [
                    turn.model_dump(mode="json") for turn in payload.previous_turns
                ],
                "model": model,
                "prompt": prompt,
                "question": question,
                "created_at": generated_at.isoformat(),
            },
        )
        return generated_at

    def persist_transcription(
        self,
        *,
        payload: UsfTranscriptionRequest,
        transcript: str,
        recording: UsfRecordingUpload | None = None,
    ) -> datetime:
        saved_at = datetime.now(timezone.utc)
        if not self._enabled:
            return saved_at

        self._put_item(
            self._sessions_table,
            {
                "session_id": payload.session_id,
                "item_key": (
                    f"ARTIFACT#TRANSCRIPT#{payload.round_index}"
                    f"#{saved_at.isoformat()}#{uuid4().hex}"
                ),
                "item_type": "artifact_transcript",
                "student_id": payload.student_id,
                "round_index": payload.round_index,
                "audio_mime_type": payload.audio_mime_type,
                "audio_bucket": recording.bucket if recording else None,
                "audio_key": recording.key if recording else None,
                "audio_url": recording.url if recording else None,
                "audio_content_type": recording.content_type if recording else None,
                "audio_size_bytes": recording.size_bytes if recording else None,
                "transcript": transcript,
                "created_at": saved_at.isoformat(),
            },
        )
        return saved_at

    def upload_recording(
        self,
        *,
        payload: UsfTranscriptionRequest,
        audio_bytes: bytes,
    ) -> UsfRecordingUpload | None:
        """Upload the raw student recording to the USF recordings bucket."""

        if not self._recordings_enabled:
            return None

        content_type = payload.audio_mime_type or "audio/webm"
        extension = _extension_for_content_type(content_type)
        key = (
            f"usf/session_id={payload.session_id}/student_id={payload.student_id}"
            f"/round={payload.round_index}/recordings/{uuid4().hex}.{extension}"
        )

        try:
            self._s3_client.put_object(
                Bucket=self._recordings_bucket,
                Key=key,
                Body=audio_bytes,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except Exception as exc:  # pragma: no cover - boto3 raises many specific errors
            raise UsfPersistenceError("Failed to upload USF recording to S3") from exc

        if self._region:
            url = f"https://{self._recordings_bucket}.s3.{self._region}.amazonaws.com/{key}"
        else:
            url = f"https://{self._recordings_bucket}.s3.amazonaws.com/{key}"

        return UsfRecordingUpload(
            bucket=str(self._recordings_bucket),
            key=key,
            url=url,
            content_type=content_type,
            size_bytes=len(audio_bytes),
        )

    def persist_defense_turn(self, payload: UsfDefenseTurnRequest) -> tuple[datetime, int]:
        saved_at = datetime.now(timezone.utc)
        completed_round_count = payload.round_index + 1
        if not self._enabled:
            return saved_at, completed_round_count

        self._put_item(
            self._sessions_table,
            {
                "session_id": payload.session_id,
                "item_key": (
                    f"ARTIFACT#DEFENSE_TURN#{payload.round_index}"
                    f"#{saved_at.isoformat()}#{uuid4().hex}"
                ),
                "item_type": "artifact_defense_turn",
                "student_id": payload.student_id,
                "module_id": payload.module_id,
                "round_index": payload.round_index,
                "question": payload.question,
                "answer_text": payload.answer_text,
                "audio_transcript": payload.audio_transcript,
                "self_rating": payload.self_rating,
                "answered_at": payload.answered_at.isoformat()
                if payload.answered_at
                else saved_at.isoformat(),
                "created_at": saved_at.isoformat(),
            },
        )
        return saved_at, completed_round_count

    def record_error(self, payload: UsfErrorRecord) -> tuple[str, datetime]:
        error_id = uuid4().hex
        recorded_at = datetime.now(timezone.utc)
        if not self._enabled:
            return error_id, recorded_at

        self._put_item(
            self._errors_table,
            {
                "session_id": payload.session_id,
                "item_key": f"ERROR#{recorded_at.isoformat()}#{error_id}",
                "error_id": error_id,
                "student_id": payload.student_id,
                "stage": payload.stage,
                "error_scope": payload.error_scope,
                "error_message": payload.error_message,
                "raw_error": payload.raw_error,
                "round_index": payload.round_index,
                "request_id": payload.request_id,
                "metadata": payload.metadata,
                "recorded_at": recorded_at.isoformat(),
            },
        )
        return error_id, recorded_at

    def _put_item(self, table: Any, item: dict[str, Any]) -> None:
        if table is None:
            return

        try:
            table.put_item(Item=self._to_dynamodb_value(item))
        except Exception as exc:  # pragma: no cover - boto3 raises many specific errors
            raise UsfPersistenceError("Failed to write USF data to DynamoDB") from exc

    def _get_item(self, table: Any, key: dict[str, str]) -> dict[str, Any] | None:
        if table is None:
            return None

        try:
            response = table.get_item(Key=key)
        except Exception as exc:  # pragma: no cover - boto3 raises many specific errors
            raise UsfPersistenceError("Failed to read USF data from DynamoDB") from exc

        item = response.get("Item")
        return item if isinstance(item, dict) else None

    def _query_items(self, table: Any, *, key_condition_expression: Any) -> list[dict[str, Any]]:
        if table is None:
            return []

        items: list[dict[str, Any]] = []
        exclusive_start_key: dict[str, Any] | None = None
        try:
            while True:
                kwargs: dict[str, Any] = {"KeyConditionExpression": key_condition_expression}
                if exclusive_start_key:
                    kwargs["ExclusiveStartKey"] = exclusive_start_key
                response = table.query(**kwargs)
                items.extend(item for item in response.get("Items", []) if isinstance(item, dict))
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as exc:  # pragma: no cover - boto3 raises many specific errors
            raise UsfPersistenceError("Failed to read USF data from DynamoDB") from exc

        return [self._normalize_read_value(item) for item in items]

    def _scan_items(self, table: Any, *, filter_expression: Any) -> list[dict[str, Any]]:
        if table is None:
            return []

        items: list[dict[str, Any]] = []
        exclusive_start_key: dict[str, Any] | None = None
        try:
            while True:
                kwargs: dict[str, Any] = {"FilterExpression": filter_expression}
                if exclusive_start_key:
                    kwargs["ExclusiveStartKey"] = exclusive_start_key
                response = table.scan(**kwargs)
                items.extend(item for item in response.get("Items", []) if isinstance(item, dict))
                exclusive_start_key = response.get("LastEvaluatedKey")
                if not exclusive_start_key:
                    break
        except Exception as exc:  # pragma: no cover - boto3 raises many specific errors
            raise UsfPersistenceError("Failed to scan USF data from DynamoDB") from exc

        return [self._normalize_read_value(item) for item in items]

    def _session_summary_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_read_value(item)
        return {
            "session_id": normalized.get("session_id"),
            "student_id": normalized.get("student_id"),
            "stage": normalized.get("stage"),
            "module_id": normalized.get("module_id"),
            "module_number": normalized.get("module_number"),
            "module_topic": normalized.get("module_topic"),
            "module_week": normalized.get("module_week"),
            "learning_objectives": normalized.get("learning_objectives", []),
            "learned_response": normalized.get("learned_response"),
            "remaining_questions_response": normalized.get("remaining_questions_response"),
            "current_round_index": normalized.get("current_round_index"),
            "completed_round_count": normalized.get("completed_round_count") or 0,
            "defense_turns": normalized.get("defense_turns", []),
            "question_count": 0,
            "transcript_count": 0,
            "defense_turn_count": 0,
            "event_count": 0,
            "error_count": 0,
            "started_at": normalized.get("started_at"),
            "last_seen_at": normalized.get("last_seen_at"),
            "completed_at": normalized.get("completed_at"),
        }

    def _session_activity_counts(self, session_id: str) -> dict[str, int]:
        session_items = self._query_items(
            self._sessions_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )
        event_items = self._query_items(
            self._events_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )
        error_items = self._query_items(
            self._errors_table,
            key_condition_expression=Key("session_id").eq(session_id),
        )
        question_count = 0
        transcript_count = 0
        defense_turn_count = 0
        for item in session_items:
            item_key = str(item.get("item_key") or "")
            if item_key.startswith("ARTIFACT#QUESTION#"):
                question_count += 1
            elif item_key.startswith("ARTIFACT#TRANSCRIPT#"):
                transcript_count += 1
            elif item_key.startswith("ARTIFACT#DEFENSE_TURN#"):
                defense_turn_count += 1

        return {
            "question_count": question_count,
            "transcript_count": transcript_count,
            "defense_turn_count": defense_turn_count,
            "event_count": len(event_items),
            "error_count": len(error_items),
        }

    def _event_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_read_value(item)
        return {
            "item_key": normalized.get("item_key"),
            "event_id": normalized.get("event_id"),
            "student_id": normalized.get("student_id"),
            "event_type": normalized.get("event_type"),
            "stage": normalized.get("stage"),
            "round_index": normalized.get("round_index"),
            "client_timestamp": normalized.get("client_timestamp"),
            "recorded_at": normalized.get("recorded_at"),
            "payload": normalized.get("payload", {}),
        }

    def _error_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_read_value(item)
        return {
            "item_key": normalized.get("item_key"),
            "error_id": normalized.get("error_id"),
            "student_id": normalized.get("student_id"),
            "stage": normalized.get("stage"),
            "error_scope": normalized.get("error_scope"),
            "error_message": normalized.get("error_message"),
            "raw_error": normalized.get("raw_error"),
            "round_index": normalized.get("round_index"),
            "request_id": normalized.get("request_id"),
            "metadata": normalized.get("metadata", {}),
            "recorded_at": normalized.get("recorded_at"),
        }

    def _artifact_from_item(self, item: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_read_value(item)
        return {
            "item_key": normalized.get("item_key"),
            "item_type": normalized.get("item_type"),
            "student_id": normalized.get("student_id"),
            "module_id": normalized.get("module_id"),
            "module_number": normalized.get("module_number"),
            "module_topic": normalized.get("module_topic"),
            "round_index": normalized.get("round_index"),
            "question": normalized.get("question"),
            "answer_text": normalized.get("answer_text"),
            "audio_transcript": normalized.get("audio_transcript"),
            "self_rating": normalized.get("self_rating"),
            "transcript": normalized.get("transcript"),
            "audio_mime_type": normalized.get("audio_mime_type"),
            "audio_bucket": normalized.get("audio_bucket"),
            "audio_key": normalized.get("audio_key"),
            "audio_url": self._generate_presigned_recording_url(
                normalized.get("audio_bucket"),
                normalized.get("audio_key"),
            )
            or normalized.get("audio_url"),
            "audio_content_type": normalized.get("audio_content_type"),
            "audio_size_bytes": normalized.get("audio_size_bytes"),
            "model": normalized.get("model"),
            "prompt": normalized.get("prompt"),
            "learning_objectives": normalized.get("learning_objectives", []),
            "learned_response": normalized.get("learned_response"),
            "remaining_questions_response": normalized.get("remaining_questions_response"),
            "previous_turns": normalized.get("previous_turns", []),
            "answered_at": normalized.get("answered_at"),
            "created_at": normalized.get("created_at"),
        }

    def _normalize_read_value(self, value: Any) -> Any:
        if isinstance(value, Decimal):
            if value % 1 == 0:
                return int(value)
            return float(value)
        if isinstance(value, dict):
            return {key: self._normalize_read_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize_read_value(item) for item in value]
        return value

    def _generate_presigned_recording_url(
        self, bucket: str | None, key: str | None, expires_in: int = 3600
    ) -> str | None:
        if not bucket or not key:
            return None

        try:
            return self._s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except Exception:
            return None

    def _to_dynamodb_value(self, value: Any) -> Any:
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, dict):
            return {key: self._to_dynamodb_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._to_dynamodb_value(item) for item in value]
        return value
