from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_audio_transcriber,
    get_usf_defense_service,
    get_usf_persistence,
)
from app.main import app
from app.schemas.usf import UsfDefenseQuestionRequest, UsfSessionSnapshotRequest
from app.services.transcription import TranscriptionResult
from app.services.transcription import _extension_for_content_type
from app.services.usf_defense import UsfDefenseService
from app.services.usf_defense import _single_follow_up_question
from app.services.usf_persistence import UsfPersistenceService


class _MemoryTable:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def put_item(self, *, Item: dict[str, Any]) -> None:
        self.items.append(Item)

    def get_item(self, *, Key: dict[str, str]) -> dict[str, Any]:
        for item in self.items:
            if all(item.get(key) == value for key, value in Key.items()):
                return {"Item": item}
        return {}

    def query(self, **_: Any) -> dict[str, Any]:
        session_id = self.items[0]["session_id"] if self.items else None
        return {
            "Items": [
                item for item in self.items if session_id is None or item.get("session_id") == session_id
            ]
        }

    def scan(self, **_: Any) -> dict[str, Any]:
        return {"Items": [item for item in self.items if item.get("item_key") == "SESSION#META"]}


class _MemoryS3Client:
    def __init__(self) -> None:
        self.objects: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.objects.append(kwargs)

    def generate_presigned_url(self, *, ClientMethod: str, Params: dict[str, str], ExpiresIn: int) -> str:
        return f"https://example.com/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"


def _make_persistence() -> UsfPersistenceService:
    service = UsfPersistenceService.__new__(UsfPersistenceService)
    service._enabled = True
    service._recordings_enabled = False
    service._recordings_bucket = None
    service._region = "us-east-2"
    service._sessions_table = _MemoryTable()
    service._events_table = _MemoryTable()
    service._errors_table = _MemoryTable()
    service._s3_client = _MemoryS3Client()
    return service


def _question_payload() -> dict[str, Any]:
    return {
        "session_id": "session-1",
        "student_id": "student-1",
        "round_index": 1,
        "module_id": "module-4",
        "module_number": 4,
        "module_topic": "Identity in a Rapidly Changing World - Part 1",
        "module_week": "June 8-14",
        "learning_objectives": [
            "Review Moore's Law and related theories.",
            "Consider the recent past and make predictions of what is to come next.",
        ],
        "learned_response": "I learned that Moore and Kurzweil both describe accelerating change.",
        "remaining_questions_response": "I am unsure how to compare these theories critically.",
        "previous_turns": [
            {
                "round_index": 0,
                "question": "What is the difference between Moore's Law and Kurzweil's law?",
                "answer_text": "Moore is about chips while Kurzweil is broader.",
                "audio_transcript": None,
                "self_rating": 6,
                "answered_at": "2026-05-17T04:00:00+00:00",
            }
        ],
    }


def test_usf_defense_prompt_includes_reflections_and_previous_turns() -> None:
    service = UsfDefenseService(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-5.5",
    )
    prompt = service.build_prompt(
        UsfDefenseQuestionRequest.model_validate(_question_payload())
    )

    assert "Identity in a Rapidly Changing World" in prompt
    assert "I learned that Moore and Kurzweil" in prompt
    assert "I am unsure how to compare" in prompt
    assert "Moore is about chips while Kurzweil is broader" in prompt
    assert "Return JSON only" in prompt
    assert "Base the question on the student's reflection" in prompt
    assert "Generate exactly one follow-up question" in prompt
    assert "continuous" in prompt and "not a random quiz" in prompt
    assert "immediately previous question and" in prompt
    assert "Do not jump randomly across learning objectives" in prompt


def test_usf_defense_question_is_normalized_to_one_question() -> None:
    assert (
        _single_follow_up_question(
            "What is context collapse? How would it affect a class introduction?"
        )
        == "What is context collapse?"
    )
    assert (
        _single_follow_up_question(
            "1. What is context collapse? 2. Can you give an example?"
        )
        == "What is context collapse?"
    )


def test_transcription_filename_extension_matches_browser_mime_type() -> None:
    assert _extension_for_content_type("audio/webm;codecs=opus") == "webm"
    assert _extension_for_content_type("audio/mp4") == "m4a"
    assert _extension_for_content_type("audio/wav") == "wav"


def test_usf_defense_prompt_allows_modules_without_reflection() -> None:
    service = UsfDefenseService(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-5.5",
    )
    payload = _question_payload() | {
        "module_id": "module-8",
        "module_number": 8,
        "module_topic": "Video Games and Identity",
        "module_week": "N/A",
        "learning_objectives": [],
        "learned_response": None,
        "remaining_questions_response": None,
        "previous_turns": [],
    }
    prompt = service.build_prompt(UsfDefenseQuestionRequest.model_validate(payload))

    assert "Video Games and Identity" in prompt
    assert "No learning objectives were provided" in prompt
    assert "No pre-defense reflection was required" in prompt
    assert "module topic" in prompt


def test_usf_persistence_writes_snapshot_and_generated_question_items() -> None:
    persistence = _make_persistence()
    snapshot = UsfSessionSnapshotRequest.model_validate(
        {
            "session_id": "session-1",
            "student_id": "student-1",
            "stage": "reflection",
            "module_id": "module-4",
            "module_number": 4,
            "module_topic": "Identity in a Rapidly Changing World - Part 1",
            "module_week": "June 8-14",
            "learning_objectives": ["Review Moore's Law."],
            "learned_response": "I learned about acceleration theories.",
            "remaining_questions_response": "How should I evaluate them?",
            "current_round_index": 0,
            "completed_round_count": 0,
            "defense_turns": [],
        }
    )

    persistence.save_snapshot(snapshot)
    persistence.persist_generated_question(
        payload=UsfDefenseQuestionRequest.model_validate(_question_payload()),
        question="Where does your comparison need stronger evidence?",
        model="gpt-5.5",
        prompt="prompt text",
        generated_at=datetime.now(timezone.utc),
    )

    items = persistence._sessions_table.items
    assert items[0]["item_key"] == "SESSION#META"
    assert items[0]["module_id"] == "module-4"
    assert items[1]["item_key"].startswith("ARTIFACT#QUESTION#1#")
    assert items[1]["question"] == "Where does your comparison need stronger evidence?"
    assert items[1]["previous_turns"][0]["self_rating"] == 6


class _DummyDefenseService:
    async def generate_question(self, payload: UsfDefenseQuestionRequest):
        class Generated:
            model = "gpt-test"
            question = "What evidence would challenge your claim?"
            generated_at = datetime.now(timezone.utc)
            prompt = "prompt with context"

        return Generated()


class _DummyTranscriber:
    async def transcribe(self, payload: bytes, content_type: str | None) -> TranscriptionResult:
        return TranscriptionResult(text="transcribed answer")


def test_usf_question_route_persists_generated_question() -> None:
    persistence = _make_persistence()
    app.dependency_overrides[get_usf_defense_service] = lambda: _DummyDefenseService()
    app.dependency_overrides[get_usf_persistence] = lambda: persistence

    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/usf/defense/question", json=_question_payload())
    finally:
        app.dependency_overrides.pop(get_usf_defense_service, None)
        app.dependency_overrides.pop(get_usf_persistence, None)

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "What evidence would challenge your claim?"
    assert persistence._sessions_table.items[0]["item_type"] == "artifact_defense_question"


def test_usf_transcribe_route_rejects_invalid_audio_and_records_error() -> None:
    persistence = _make_persistence()
    app.dependency_overrides[get_usf_persistence] = lambda: persistence
    app.dependency_overrides[get_audio_transcriber] = lambda: _DummyTranscriber()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/usf/defense/transcribe",
                json={
                    "session_id": "session-1",
                    "student_id": "student-1",
                    "round_index": 0,
                    "audio_base64": "not-valid-base64",
                    "audio_mime_type": "audio/webm",
                },
            )
    finally:
        app.dependency_overrides.pop(get_usf_persistence, None)
        app.dependency_overrides.pop(get_audio_transcriber, None)

    assert response.status_code == 400
    assert persistence._errors_table.items[0]["stage"] == "defense_transcribe"
    assert persistence._errors_table.items[0]["error_scope"] == "client"


def test_usf_transcribe_route_uploads_recording_when_bucket_enabled() -> None:
    persistence = _make_persistence()
    persistence._recordings_enabled = True
    persistence._recordings_bucket = "usf-defense-recordings-test"
    app.dependency_overrides[get_usf_persistence] = lambda: persistence
    app.dependency_overrides[get_audio_transcriber] = lambda: _DummyTranscriber()

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/usf/defense/transcribe",
                json={
                    "session_id": "session-1",
                    "student_id": "student-1",
                    "round_index": 0,
                    "audio_base64": "YXVkaW8=",
                    "audio_mime_type": "audio/webm;codecs=opus",
                },
            )
    finally:
        app.dependency_overrides.pop(get_usf_persistence, None)
        app.dependency_overrides.pop(get_audio_transcriber, None)

    assert response.status_code == 200
    body = response.json()
    assert body["audio_bucket"] == "usf-defense-recordings-test"
    assert body["audio_key"].endswith(".webm")
    assert persistence._s3_client.objects[0]["Bucket"] == "usf-defense-recordings-test"
    transcript_item = persistence._sessions_table.items[0]
    assert transcript_item["audio_bucket"] == "usf-defense-recordings-test"
    assert transcript_item["audio_size_bytes"] == 5


def test_usf_defense_turn_accepts_empty_unrated_timeout() -> None:
    persistence = _make_persistence()
    app.dependency_overrides[get_usf_persistence] = lambda: persistence

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/usf/defense/turn",
                json={
                    "session_id": "session-1",
                    "student_id": "student-1",
                    "module_id": "module-1",
                    "round_index": 0,
                    "question": "What is context collapse?",
                    "answer_text": "",
                    "audio_transcript": None,
                    "answered_at": "2026-05-17T04:00:00+00:00",
                },
            )
    finally:
        app.dependency_overrides.pop(get_usf_persistence, None)

    assert response.status_code == 200
    assert persistence._sessions_table.items[0]["item_type"] == "artifact_defense_turn"
    assert persistence._sessions_table.items[0]["answer_text"] == ""
    assert persistence._sessions_table.items[0]["self_rating"] is None


def test_usf_research_routes_return_overview_and_detail() -> None:
    persistence = _make_persistence()
    snapshot = UsfSessionSnapshotRequest.model_validate(
        {
            "session_id": "session-1",
            "student_id": "student-1",
            "stage": "complete",
            "module_id": "module-4",
            "module_number": 4,
            "module_topic": "Identity in a Rapidly Changing World - Part 1",
            "module_week": "June 8-14",
            "learning_objectives": ["Review Moore's Law."],
            "learned_response": "I learned about acceleration theories.",
            "remaining_questions_response": "How should I evaluate them?",
            "current_round_index": 4,
            "completed_round_count": 5,
            "defense_turns": [],
            "completed_at": "2026-05-17T04:00:00+00:00",
        }
    )
    persistence.save_snapshot(snapshot)
    persistence.persist_generated_question(
        payload=UsfDefenseQuestionRequest.model_validate(_question_payload()),
        question="Where does your comparison need stronger evidence?",
        model="gpt-5.5",
        prompt="prompt text",
        generated_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_usf_persistence] = lambda: persistence

    try:
        with TestClient(app) as client:
            overview_response = client.get("/api/v1/usf/research/overview")
            detail_response = client.get("/api/v1/usf/research/session/session-1")
    finally:
        app.dependency_overrides.pop(get_usf_persistence, None)

    assert overview_response.status_code == 200
    overview = overview_response.json()
    assert overview["session_count"] == 1
    assert overview["students"][0]["student_id"] == "student-1"
    assert overview["students"][0]["sessions"][0]["question_count"] == 1

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["session"]["module_id"] == "module-4"
    assert detail["generated_questions"][0]["question"] == "Where does your comparison need stronger evidence?"
