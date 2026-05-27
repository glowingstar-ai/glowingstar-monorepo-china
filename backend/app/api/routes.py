from __future__ import annotations

import base64
import binascii
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import HttpUrl

from app.api.dependencies import (
    get_auth_client,
    get_audio_transcriber,
    # get_audio_storage,  # Commented out AWS S3 for now
    get_context_storage,
    get_emotion_analyzer,
    get_generative_ui_service,
    get_journal_coach,
    get_note_annotator,
    get_payment_service,
    get_realtime_client,
    get_research_service,
    get_saintpaul_persistence,
    get_settings,
    get_tutor_service,
    get_usf_defense_service,
    get_usf_persistence,
    get_vision_analyzer,
    get_yandaojie_defense_service,
    get_yandaojie_persistence,
)
from app.core.config import Settings
from app.schemas.auth import (
    AuthCallbackRequest,
    AuthLoginResponse,
    AuthTokenResponse,
    AuthUserInfoResponse,
)
from app.schemas.emotion import EmotionAnalysisRequest, EmotionAnalysisResponse
from app.schemas.generative_ui import GenerativeUIRequest, GenerativeUIResponse
from app.schemas.health import HealthResponse
from app.schemas.payment import PaymentCheckoutRequest, PaymentCheckoutResponse
from app.schemas.realtime import (
    HighlightInstruction as HighlightInstructionSchema,
    RealtimeSessionToken,
    VisionFrameRequest,
    VisionFrameResponse,
)

from app.schemas.journal import JournalEntryRequest, JournalEntryResponse
from app.schemas.research import ResearchPaperSummary, ResearchSearchRequest
from app.schemas.note import NoteCreateRequest, NoteCreateResponse
from app.schemas.saintpaul import (
    SaintPaulErrorRecord,
    SaintPaulEventRequest,
    SaintPaulEventResponse,
    SaintPaulQuizAttemptRequest,
    SaintPaulQuizAttemptResponse,
    SaintPaulResearchOverviewResponse,
    SaintPaulResearchSessionDetailResponse,
    SaintPaulSessionMessageRequest,
    SaintPaulSessionMessageResponse,
    SaintPaulSessionSnapshotRequest,
    SaintPaulSessionSnapshotResponse,
    SaintPaulSessionStartRequest,
    SaintPaulSessionStartResponse,
)
from app.schemas.tutor import (
    TutorChatRequest,
    TutorChatResponse,
    TutorImageExplanationRequest,
    TutorImageExplanationResponse,
    TutorModeRequest,
    TutorModeResponse,
    TutorQuizRequest,
    TutorQuizResponse,
)
from app.schemas.usf import (
    UsfDefenseQuestionRequest,
    UsfDefenseQuestionResponse,
    UsfDefenseTurnRequest,
    UsfDefenseTurnResponse,
    UsfErrorRecord,
    UsfEventRequest,
    UsfEventResponse,
    UsfResearchOverviewResponse,
    UsfResearchSessionDetailResponse,
    UsfSessionSnapshotRequest,
    UsfSessionSnapshotResponse,
    UsfSessionStartRequest,
    UsfSessionStartResponse,
    UsfTranscriptionRequest,
    UsfTranscriptionResponse,
)
from app.services.auth import Auth0Client, Auth0ClientError
from app.services.emotion import EmotionAnalyzer
from app.services.generative_ui import (
    GenerativeUIService,
    GenerativeUIServiceError,
    ThemeSuggestion,
)
from app.services.journal import JournalCoach, JournalCoachError
from app.services.note import NoteAnnotator, NoteAnnotationError
from app.services.transcription import AudioTranscriber, AudioTranscriptionError
from app.services.payment import StripePaymentError, StripePaymentService
from app.services.realtime import RealtimeSessionClient, RealtimeSessionError
from app.services.research import ResearchDiscoveryService
from app.services.saintpaul_persistence import (
    SaintPaulPersistenceError,
    SaintPaulPersistenceService,
)
# from app.services.storage import S3AudioStorage, StorageServiceError  # Commented out AWS S3 for now
from app.services.tutor import TutorModeService, TutorServiceUnavailableError
from app.services.usf_defense import UsfDefenseService, UsfDefenseServiceError
from app.services.usf_persistence import UsfPersistenceError, UsfPersistenceService
from app.services.vision import (
    VisionAnalysisError,
    VisionAnalyzer,
    VisionContext,
)
from app.services.context_storage import ContextStorage
from app.schemas.yandaojie import (
    YandaojieDefenseQuestionRequest,
    YandaojieDefenseQuestionResponse,
    YandaojieDefenseTurnRequest,
    YandaojieDefenseTurnResponse,
    YandaojieErrorRecord,
    YandaojieEventRequest,
    YandaojieEventResponse,
    YandaojieSessionSnapshotRequest,
    YandaojieSessionSnapshotResponse,
    YandaojieSessionStartRequest,
    YandaojieSessionStartResponse,
)
from app.services.yandaojie_defense import (
    YandaojieDefenseService,
    YandaojieDefenseServiceError,
)
from app.services.yandaojie_persistence import (
    YandaojiePersistenceError,
    YandaojiePersistenceService,
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return basic service health information."""

    return HealthResponse(
        status="ok",
        service=settings.project_name,
        environment=settings.environment,
    )


@router.get("/auth/login", response_model=AuthLoginResponse, tags=["auth"])
async def auth_login(
    redirect_uri: HttpUrl = Query(..., description="Redirect URI configured in Auth0"),
    state: str | None = Query(None, description="Opaque state passed back after login"),
    scope: str | None = Query(None, description="Optional override for OAuth scopes"),
    audience: str | None = Query(None, description="Optional override for the API audience"),
    auth_client: Auth0Client = Depends(get_auth_client),
) -> AuthLoginResponse:
    """Return the Auth0 hosted login page URL."""

    url = auth_client.build_authorize_url(
        redirect_uri=str(redirect_uri),
        state=state,
        scope=scope,
        audience=audience,
    )
    return AuthLoginResponse(authorization_url=url)


@router.post("/auth/callback", response_model=AuthTokenResponse, tags=["auth"])
async def auth_callback(
    payload: AuthCallbackRequest,
    auth_client: Auth0Client = Depends(get_auth_client),
) -> AuthTokenResponse:
    """Exchange an Auth0 authorization code for access tokens."""

    try:
        tokens = await auth_client.exchange_code_for_tokens(
            code=payload.code,
            redirect_uri=str(payload.redirect_uri),
        )
    except Auth0ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AuthTokenResponse(
        access_token=tokens.access_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        scope=tokens.scope,
        id_token=tokens.id_token,
        refresh_token=tokens.refresh_token,
    )


@router.get("/auth/user", response_model=AuthUserInfoResponse, tags=["auth"])
async def auth_user_info(
    authorization: str = Header(..., alias="Authorization"),
    auth_client: Auth0Client = Depends(get_auth_client),
) -> AuthUserInfoResponse:
    """Return the authenticated user's profile by calling Auth0's userinfo endpoint."""

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401, detail="Authorization header must contain a Bearer token"
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Bearer token is missing")

    try:
        profile = await auth_client.get_user_info(token)
    except Auth0ClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    claims = {
        key: value
        for key, value in profile.raw.items()
        if key not in {"sub", "email", "name", "picture"}
    }

    return AuthUserInfoResponse(
        sub=profile.sub,
        email=profile.email,
        name=profile.name,
        picture=profile.picture,
        claims=claims,
    )


@router.post("/emotion/analyze", response_model=EmotionAnalysisResponse, tags=["emotion"])
async def analyze_emotion(
    payload: EmotionAnalysisRequest,
    analyzer: EmotionAnalyzer = Depends(get_emotion_analyzer),
) -> EmotionAnalysisResponse:
    """Analyze multi-modal signals and return an emotion profile."""

    return analyzer.analyze(payload)


@router.post("/realtime/session", response_model=RealtimeSessionToken, tags=["realtime"])
async def create_realtime_session(
    client: RealtimeSessionClient = Depends(get_realtime_client),
    context_storage: ContextStorage = Depends(get_context_storage),
) -> RealtimeSessionToken:
    """Return an ephemeral client secret for establishing WebRTC sessions with visual context."""

    # Get the most recent visual context
    recent_context = context_storage.get_latest_context()

    # Enhance instructions with visual context if available
    enhanced_instructions = None
    latest_frame_base64: str | None = None
    highlight_payload: list[HighlightInstructionSchema] | None = None
    if recent_context:
        latest_frame_base64 = recent_context.image_base64

        summary_lines = []
        if recent_context.description and recent_context.description.strip():
            summary_lines.append(f"- Description: {recent_context.description.strip()}")

        if recent_context.key_elements:
            key_elements = [
                element.strip()
                for element in recent_context.key_elements
                if element and element.strip()
            ]
            if key_elements:
                summary_lines.append("- Key elements: " + ", ".join(key_elements))

        if recent_context.user_intent and recent_context.user_intent.strip():
            summary_lines.append(f"- User intent: {recent_context.user_intent.strip()}")

        if recent_context.actionable_items:
            actionable_items = [
                item.strip()
                for item in recent_context.actionable_items
                if item and item.strip()
            ]
            if actionable_items:
                summary_lines.append("- Actionable items: " + ", ".join(actionable_items))

        if recent_context.dom_summary and recent_context.dom_summary.strip():
            summary_lines.append("- DOM summary: " + recent_context.dom_summary.strip())

        if recent_context.highlight_instructions:
            highlight_payload = [
                HighlightInstructionSchema(
                    selector=instruction.selector,
                    action=instruction.action,
                    reason=instruction.reason,
                )
                for instruction in recent_context.highlight_instructions
            ]
            if highlight_payload:
                highlight_overview = ", ".join(
                    f"{item.selector}{f' ({item.reason})' if item.reason else ''}"
                    for item in highlight_payload
                )
                summary_lines.append("- Highlight candidates: " + highlight_overview)

        if not summary_lines:
            summary_lines.append(
                "- Visual analysis metadata is unavailable. Request additional processing if you need structured details."
            )

        context_summary = "\n".join(summary_lines)

        enhanced_instructions = f"""You are an AI assistant that can see and understand the user's current screen context.

Visual context summary:
{context_summary}

A raw base64-encoded frame captured by the client is available for immediate multimodal processing.

When responding to the user, you MUST reply with valid JSON using this schema:

{{
  "answer": "Helpful natural-language response to the user",
  "highlights": [
    {{"selector": "CSS selector from the DOM digest", "action": "highlight", "reason": "Why it matters"}}
  ]
}}

Return an empty array for "highlights" if nothing should be highlighted. Do not include Markdown or additional prose outside the JSON.

Use this visual context to provide more relevant and helpful responses. You can reference what you see on their screen, help them with tasks they're working on, or answer questions about the content they're viewing. Be specific about what you observe and how you can assist them with their current activity."""

        if recent_context.dom_snapshot:
            enhanced_instructions += "\n\nDOM digest (JSON):\n" + recent_context.dom_snapshot

    try:
        # Create a new client with enhanced instructions
        enhanced_client = RealtimeSessionClient(
            api_key=client.api_key,
            base_url=client.base_url,
            model=client.model,
            voice=client.voice,
            instructions=enhanced_instructions or client.instructions,
            timeout=client.timeout,
        )
        
        session = await enhanced_client.create_ephemeral_session()
    except RealtimeSessionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RealtimeSessionToken(
        session_id=session.session_id,
        client_secret=session.client_secret,
        expires_at=session.expires_at,
        model=session.model,
        url=session.handshake_url,
        voice=session.voice,
        latest_frame_base64=latest_frame_base64,
        dom_summary=recent_context.dom_summary if recent_context else None,
        dom_snapshot=recent_context.dom_snapshot if recent_context else None,
        highlight_instructions=highlight_payload,
    )


@router.post("/vision/frame", response_model=VisionFrameResponse, tags=["vision"])
async def accept_vision_frame(
    payload: VisionFrameRequest,
    context_storage: ContextStorage = Depends(get_context_storage),
    analyzer: VisionAnalyzer = Depends(get_vision_analyzer),
) -> VisionFrameResponse:
    """Accept a base64-encoded frame from the client camera or UI surface."""

    try:
        decoded = base64.b64decode(payload.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64-encoded image") from exc

    received_at = datetime.now(timezone.utc)

    # Save the image to the backend folder for debugging/visualization
    try:
        # Create images directory if it doesn't exist
        images_dir = os.path.join(os.path.dirname(__file__), "..", "..", "captured_images")
        os.makedirs(images_dir, exist_ok=True)
        
        # Generate filename with timestamp and source
        timestamp_str = received_at.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"frame_{timestamp_str}_{payload.source}.jpg"
        filepath = os.path.join(images_dir, filename)
        
        # Save the decoded image
        with open(filepath, "wb") as f:
            f.write(decoded)
            
        print(f"Saved captured image to: {filepath}")
        
    except Exception as exc:
        # Don't fail the request if image saving fails, just log it
        print(f"Failed to save image: {exc}")

    # Analyze the frame with GPT-5 to extract semantic context and highlight instructions
    try:
        context = await analyzer.analyze_screenshot(
            payload.image_base64,
            source=payload.source,
            captured_at=payload.captured_at,
            dom_snapshot=payload.dom_snapshot,
        )
    except VisionAnalysisError as exc:
        print(f"Vision analysis failed: {exc}")
        context = VisionContext(
            description="Raw frame capture (analysis unavailable)",
            key_elements=[],
            user_intent=None,
            actionable_items=[],
            timestamp=received_at,
            source=payload.source,
            image_base64=payload.image_base64,
            captured_at=payload.captured_at,
            dom_snapshot=payload.dom_snapshot,
            dom_summary=None,
            highlight_instructions=[],
        )

    # Use a session ID based on timestamp for now (in production, use actual session ID)
    session_id = f"session_{int(received_at.timestamp())}"
    context_storage.store_context(session_id, context)

    return VisionFrameResponse(
        status="accepted",
        bytes=len(decoded),
        captured_at=payload.captured_at,
        received_at=received_at,
        source=payload.source,
        description=context.description,
        dom_summary=context.dom_summary,
        highlight_instructions=[
            HighlightInstructionSchema(
                selector=instruction.selector,
                action=instruction.action,
                reason=instruction.reason,
            )
            for instruction in context.highlight_instructions
        ]
        or None,
    )


@router.post("/notes", response_model=NoteCreateResponse, tags=["notes"])
async def create_note(
    payload: NoteCreateRequest,
    # storage: S3AudioStorage = Depends(get_audio_storage),  # Commented out AWS S3 for now
    annotator: NoteAnnotator = Depends(get_note_annotator),
) -> NoteCreateResponse:
    """Persist a note and request an annotated summary."""

    audio_url: str | None = None
    # Commented out AWS S3 audio upload functionality for now
    # if payload.audio_base64:
    #     try:
    #         audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
    #     except (binascii.Error, ValueError) as exc:
    #         raise HTTPException(status_code=400, detail="Invalid base64-encoded audio clip") from exc

    #     try:
    #         upload = storage.upload_audio(audio_bytes, payload.audio_mime_type)
    #     except StorageServiceError as exc:
    #         raise HTTPException(status_code=502, detail=str(exc)) from exc

    #     audio_url = upload.url

    try:
        polished_notes = await annotator.annotate(
            title=payload.title,
            content=payload.content,
            audio_url=audio_url,
        )
    except NoteAnnotationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    created_at = datetime.now(timezone.utc)

    return NoteCreateResponse(
        note_id=str(uuid4()),
        title=payload.title,
        content=polished_notes.content,  # Use polished notes as the main content
        audio_url=audio_url,
        annotation=payload.content,  # Keep original notes as annotation for reference
        created_at=created_at,
    )


@router.post("/notes/annotate", response_model=None, tags=["notes"])
async def stream_note_annotation(
    payload: NoteCreateRequest,
    # storage: S3AudioStorage = Depends(get_audio_storage),  # Commented out AWS S3 for now
    annotator: NoteAnnotator = Depends(get_note_annotator),
    transcriber: AudioTranscriber = Depends(get_audio_transcriber),
) -> StreamingResponse:
    """Stream the full note annotation workflow."""

    async def event_stream():
        annotation_chunks: list[str] = []
        audio_url: str | None = None
        transcript_text: str | None = None

        try:
            yield _encode_event(
                {
                    "type": "status",
                    "stage": "initializing",
                    "message": "Preparing to polish your notes with GPT-5",
                }
            )

            # Commented out AWS S3 audio upload functionality for now
            # if payload.audio_base64:
            #     try:
            #         audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
            #     except (binascii.Error, ValueError) as exc:
            #         raise ValueError("Invalid base64-encoded audio clip") from exc

            # if audio_bytes:
            #     yield _encode_event(
            #         {
            #             "type": "status",
            #             "stage": "transcribing",
            #             "message": "Converting your voice memo to text",
            #         }
            #     )

            #     try:
            #         transcription = await transcriber.transcribe(audio_bytes, payload.audio_mime_type)
            #     except AudioTranscriptionError as exc:
            #         raise RuntimeError(str(exc)) from exc

            #     transcript_text = transcription.text
            #     yield _encode_event(
            #         {
            #             "type": "transcript",
            #             "stage": "transcribing",
            #             "text": transcript_text,
            #         }
            #     )

            #     try:
            #         upload = storage.upload_audio(audio_bytes, payload.audio_mime_type)
            #         audio_url = upload.url
            #         yield _encode_event(
            #             {
            #                 "type": "status",
            #                 "stage": "uploading",
            #                 "message": "Stored your voice memo securely",
            #             }
            #         )
            #     except StorageServiceError as exc:
            #         raise RuntimeError(str(exc)) from exc

            yield _encode_event(
                {
                    "type": "status",
                    "stage": "annotating",
                    "message": "Polishing your notes with GPT-5",
                }
            )

            try:
                async for delta in annotator.stream_annotation(
                    title=payload.title,
                    content=payload.content,
                    audio_url=audio_url,
                    transcript=transcript_text,
                ):
                    if delta:
                        if isinstance(delta, dict):
                            # Handle new format with reasoning
                            if delta.get("type") == "reasoning":
                                yield _encode_event(
                                    {
                                        "type": "reasoning_delta",
                                        "stage": "reasoning",
                                        "delta": delta["content"],
                                    }
                                )
                            elif delta.get("type") == "content":
                                annotation_chunks.append(delta["content"])
                                yield _encode_event(
                                    {
                                        "type": "annotation_delta",
                                        "stage": "annotating",
                                        "delta": delta["content"],
                                    }
                                )
                        else:
                            # Handle old format (backward compatibility)
                            annotation_chunks.append(delta)
                            yield _encode_event(
                                {
                                    "type": "annotation_delta",
                                    "stage": "annotating",
                                    "delta": delta,
                                }
                            )
            except NoteAnnotationError as exc:
                raise RuntimeError(str(exc)) from exc

            annotation_text = "".join(annotation_chunks).strip()
            if not annotation_text:
                try:
                    fallback = await annotator.annotate(
                        title=payload.title,
                        content=payload.content,
                        audio_url=audio_url,
                        transcript=transcript_text,
                    )
                except NoteAnnotationError as exc:
                    raise RuntimeError(str(exc)) from exc
                annotation_text = fallback.content
            created_at = datetime.now(timezone.utc)
            note = NoteCreateResponse(
                note_id=str(uuid4()),
                title=payload.title,
                content=annotation_text,  # Use polished notes as the main content
                audio_url=audio_url,
                annotation=payload.content,  # Keep original notes as annotation for reference
                created_at=created_at,
            )

            yield _encode_event(
                {
                    "type": "note_saved",
                    "stage": "complete",
                    "note": note.model_dump(mode="json"),
                    "transcript": transcript_text,
                }
            )
            yield _encode_event(
                {
                    "type": "complete",
                    "stage": "complete",
                    "message": "Annotation finished",
                }
            )
        except ValueError as exc:
            yield _encode_event(
                {
                    "type": "error",
                    "stage": "error",
                    "message": str(exc),
                }
            )
        except RuntimeError as exc:
            yield _encode_event(
                {
                    "type": "error",
                    "stage": "error",
                    "message": str(exc),
                }
            )
        except Exception:  # pragma: no cover - defensive guard
            yield _encode_event(
                {
                    "type": "error",
                    "stage": "error",
                    "message": "An unexpected error occurred while annotating the note.",
                }
            )

    return StreamingResponse(event_stream(), media_type="application/jsonl")


@router.post("/journals", response_model=JournalEntryResponse, tags=["journals"])
async def create_journal_entry(
    payload: JournalEntryRequest,
    coach: JournalCoach = Depends(get_journal_coach),
) -> JournalEntryResponse:
    """Transform a free-form journal entry into guided reflections."""

    try:
        guidance = await coach.guide(
            title=payload.title,
            entry=payload.entry,
            mood=payload.mood,
            gratitude=payload.gratitude,
            intention=payload.intention,
            focus_area=payload.focus_area,
        )
    except JournalCoachError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    created_at = datetime.now(timezone.utc)

    return JournalEntryResponse(
        journal_id=str(uuid4()),
        created_at=created_at,
        title=payload.title,
        entry=payload.entry,
        mood=payload.mood,
        gratitude=payload.gratitude,
        intention=payload.intention,
        focus_area=payload.focus_area,
        ai_reflection=guidance.reflection,
        affirmation=guidance.affirmation,
        suggested_prompts=guidance.prompts,
        breathing_exercise=guidance.breathwork,
    )


@router.post("/payments/checkout", response_model=PaymentCheckoutResponse, tags=["payments"])
async def create_checkout_session(
    payload: PaymentCheckoutRequest,
    payment_service: StripePaymentService = Depends(get_payment_service),
) -> PaymentCheckoutResponse:
    """Create a Stripe Checkout session for the client to complete payment."""

    try:
        session = payment_service.create_checkout_session(
            success_url=str(payload.success_url),
            cancel_url=str(payload.cancel_url),
            price_id=payload.price_id,
            quantity=payload.quantity,
            customer_email=payload.customer_email,
        )
    except StripePaymentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return PaymentCheckoutResponse(session_id=session.session_id, checkout_url=session.url)


@router.post(
    "/saintpaul/session/start",
    response_model=SaintPaulSessionStartResponse,
    tags=["saintpaul"],
)
async def create_saintpaul_session(
    payload: SaintPaulSessionStartRequest,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulSessionStartResponse:
    """Create a new persisted Saint Paul student session."""

    try:
        session_id, started_at = persistence.create_session(payload)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulSessionStartResponse(
        session_id=session_id,
        started_at=started_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/saintpaul/session/snapshot",
    response_model=SaintPaulSessionSnapshotResponse,
    tags=["saintpaul"],
)
async def save_saintpaul_session_snapshot(
    payload: SaintPaulSessionSnapshotRequest,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulSessionSnapshotResponse:
    """Persist the latest recoverable Saint Paul session snapshot."""

    try:
        saved_at = persistence.save_snapshot(payload)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulSessionSnapshotResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/saintpaul/session/event",
    response_model=SaintPaulEventResponse,
    tags=["saintpaul"],
)
async def append_saintpaul_event(
    payload: SaintPaulEventRequest,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulEventResponse:
    """Append a Saint Paul workflow event."""

    try:
        event_id, recorded_at = persistence.append_event(payload)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulEventResponse(
        event_id=event_id,
        recorded_at=recorded_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/saintpaul/session/quiz-attempt",
    response_model=SaintPaulQuizAttemptResponse,
    tags=["saintpaul"],
)
async def save_saintpaul_quiz_attempt(
    payload: SaintPaulQuizAttemptRequest,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulQuizAttemptResponse:
    """Persist a completed Saint Paul AI quiz attempt."""

    try:
        saved_at = persistence.persist_quiz_attempt(payload)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulQuizAttemptResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/saintpaul/session/message",
    response_model=SaintPaulSessionMessageResponse,
    tags=["saintpaul"],
)
async def save_saintpaul_session_message(
    payload: SaintPaulSessionMessageRequest,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulSessionMessageResponse:
    """Persist one Saint Paul session message."""

    try:
        saved_at = persistence.persist_chat_message(
            session_id=payload.session_id,
            student_id=payload.student_id,
            objective_index=payload.objective_index,
            role=payload.role,
            content=payload.content,
            model=payload.model,
            created_at=payload.created_at,
            message_key=payload.message_key,
        )
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulSessionMessageResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
    )


@router.get(
    "/saintpaul/research/overview",
    response_model=SaintPaulResearchOverviewResponse,
    tags=["saintpaul"],
)
async def get_saintpaul_research_overview(
    limit: int | None = Query(
        None,
        ge=1,
        le=1000,
        description="Optional maximum number of latest sessions to include in the activity index.",
    ),
    refresh: bool = Query(
        False,
        description="When true, recompute the overview from DynamoDB instead of using the cached result.",
    ),
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulResearchOverviewResponse:
    """Return grouped Saint Paul student/session activity for internal review."""

    try:
        payload = persistence.get_research_overview(limit=limit, force_refresh=refresh)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SaintPaulResearchOverviewResponse.model_validate(payload)


@router.get(
    "/saintpaul/research/session/{session_id}",
    response_model=SaintPaulResearchSessionDetailResponse,
    tags=["saintpaul"],
)
async def get_saintpaul_research_session_detail(
    session_id: str,
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> SaintPaulResearchSessionDetailResponse:
    """Return the full persisted activity stream for one Saint Paul session."""

    try:
        payload = persistence.get_session_research_detail(session_id)
    except SaintPaulPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if payload.get("session") is None:
        raise HTTPException(status_code=404, detail="Saint Paul session not found")

    return SaintPaulResearchSessionDetailResponse.model_validate(payload)


@router.post(
    "/usf/session/start",
    response_model=UsfSessionStartResponse,
    tags=["usf"],
)
async def create_usf_session(
    payload: UsfSessionStartRequest,
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfSessionStartResponse:
    """Create a new persisted USF defense session."""

    try:
        created = persistence.create_session(payload)
    except UsfPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfSessionStartResponse(
        session_id=created.session_id,
        started_at=created.started_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/usf/session/snapshot",
    response_model=UsfSessionSnapshotResponse,
    tags=["usf"],
)
async def save_usf_session_snapshot(
    payload: UsfSessionSnapshotRequest,
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfSessionSnapshotResponse:
    """Persist the latest recoverable USF defense session state."""

    try:
        saved_at = persistence.save_snapshot(payload)
    except UsfPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfSessionSnapshotResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/usf/session/event",
    response_model=UsfEventResponse,
    tags=["usf"],
)
async def append_usf_event(
    payload: UsfEventRequest,
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfEventResponse:
    """Append a USF workflow event."""

    try:
        event_id, recorded_at = persistence.append_event(payload)
    except UsfPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfEventResponse(
        event_id=event_id,
        recorded_at=recorded_at,
        persistence_enabled=persistence.enabled,
    )


@router.get(
    "/usf/research/overview",
    response_model=UsfResearchOverviewResponse,
    tags=["usf"],
)
async def get_usf_research_overview(
    limit: int | None = Query(
        None,
        ge=1,
        le=1000,
        description="Optional maximum number of latest USF sessions to include.",
    ),
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfResearchOverviewResponse:
    """Return grouped USF student/session activity for internal review."""

    try:
        payload = persistence.get_research_overview(limit=limit)
    except UsfPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfResearchOverviewResponse.model_validate(payload)


@router.get(
    "/usf/research/session/{session_id}",
    response_model=UsfResearchSessionDetailResponse,
    tags=["usf"],
)
async def get_usf_research_session_detail(
    session_id: str,
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfResearchSessionDetailResponse:
    """Return the full persisted activity stream for one USF session."""

    try:
        payload = persistence.get_session_research_detail(session_id)
    except UsfPersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if payload.get("session") is None:
        raise HTTPException(status_code=404, detail="USF session not found")

    return UsfResearchSessionDetailResponse.model_validate(payload)


@router.post(
    "/usf/defense/question",
    response_model=UsfDefenseQuestionResponse,
    tags=["usf"],
)
async def create_usf_defense_question(
    payload: UsfDefenseQuestionRequest,
    defense_service: UsfDefenseService = Depends(get_usf_defense_service),
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfDefenseQuestionResponse:
    """Generate and persist one USF defense follow-up question."""

    try:
        generated = await defense_service.generate_question(payload)
    except UsfDefenseServiceError as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_question",
                error_scope="backend",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
                metadata={
                    "module_id": payload.module_id,
                    "module_topic": payload.module_topic,
                },
            ),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        persistence.persist_generated_question(
            payload=payload,
            question=generated.question,
            model=generated.model,
            prompt=generated.prompt,
            generated_at=generated.generated_at,
        )
    except UsfPersistenceError as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_question_persist",
                error_scope="storage",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfDefenseQuestionResponse(
        model=generated.model,
        round_index=payload.round_index,
        question=generated.question,
        generated_at=generated.generated_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/usf/defense/transcribe",
    response_model=UsfTranscriptionResponse,
    tags=["usf"],
)
async def transcribe_usf_defense_audio(
    payload: UsfTranscriptionRequest,
    transcriber: AudioTranscriber = Depends(get_audio_transcriber),
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfTranscriptionResponse:
    """Transcribe and persist a USF defense audio answer."""

    try:
        audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_transcribe",
                error_scope="client",
                error_message="Invalid base64-encoded audio clip",
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=400, detail="Invalid base64-encoded audio clip") from exc

    try:
        transcription = await transcriber.transcribe(
            audio_bytes,
            payload.audio_mime_type,
        )
    except AudioTranscriptionError as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_transcribe",
                error_scope="backend",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        recording = (
            persistence.upload_recording(
                payload=payload,
                audio_bytes=audio_bytes,
            )
            if payload.persist_audio
            else None
        )
        saved_at = persistence.persist_transcription(
            payload=payload,
            transcript=transcription.text,
            recording=recording,
        )
    except UsfPersistenceError as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_transcript_persist",
                error_scope="storage",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfTranscriptionResponse(
        text=transcription.text,
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
        audio_bucket=recording.bucket if recording else None,
        audio_key=recording.key if recording else None,
        audio_url=recording.url if recording else None,
        audio_content_type=recording.content_type if recording else None,
        audio_size_bytes=recording.size_bytes if recording else None,
    )


@router.post(
    "/usf/defense/turn",
    response_model=UsfDefenseTurnResponse,
    tags=["usf"],
)
async def save_usf_defense_turn(
    payload: UsfDefenseTurnRequest,
    persistence: UsfPersistenceService = Depends(get_usf_persistence),
) -> UsfDefenseTurnResponse:
    """Persist a completed USF defense answer and self-rating."""

    try:
        saved_at, completed_round_count = persistence.persist_defense_turn(payload)
    except UsfPersistenceError as exc:
        _record_usf_error_safely(
            persistence,
            UsfErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_turn_persist",
                error_scope="storage",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return UsfDefenseTurnResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
        completed_round_count=completed_round_count,
    )


@router.post("/tutor/mode", response_model=TutorModeResponse, tags=["tutor"])
async def create_tutor_mode_plan(
    payload: TutorModeRequest,
    tutor_service: TutorModeService = Depends(get_tutor_service),
) -> TutorModeResponse:
    """Create a BabyAGI-inspired tutoring plan powered by GPT-5."""

    return await tutor_service.generate_plan(payload)


@router.post(
    "/yandaojie/session/start",
    response_model=YandaojieSessionStartResponse,
    tags=["yandaojie"],
)
async def create_yandaojie_session(
    payload: YandaojieSessionStartRequest,
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> YandaojieSessionStartResponse:
    """Create a new persisted Yandaojie defense session."""

    try:
        created = await persistence.create_session(payload)
    except YandaojiePersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return YandaojieSessionStartResponse(
        session_id=created.session_id,
        started_at=created.started_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/yandaojie/session/snapshot",
    response_model=YandaojieSessionSnapshotResponse,
    tags=["yandaojie"],
)
async def save_yandaojie_session_snapshot(
    payload: YandaojieSessionSnapshotRequest,
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> YandaojieSessionSnapshotResponse:
    """Persist the latest recoverable Yandaojie session state."""

    try:
        saved_at = await persistence.save_snapshot(payload)
    except YandaojiePersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return YandaojieSessionSnapshotResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/yandaojie/session/event",
    response_model=YandaojieEventResponse,
    tags=["yandaojie"],
)
async def append_yandaojie_event(
    payload: YandaojieEventRequest,
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> YandaojieEventResponse:
    """Append a Yandaojie workflow event."""

    try:
        event_id, recorded_at = await persistence.append_event(payload)
    except YandaojiePersistenceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return YandaojieEventResponse(
        event_id=event_id,
        recorded_at=recorded_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/yandaojie/defense/question",
    response_model=YandaojieDefenseQuestionResponse,
    tags=["yandaojie"],
)
async def create_yandaojie_defense_question(
    payload: YandaojieDefenseQuestionRequest,
    defense_service: YandaojieDefenseService = Depends(get_yandaojie_defense_service),
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> YandaojieDefenseQuestionResponse:
    """Generate and persist one Yandaojie defense follow-up question."""

    try:
        generated = await defense_service.generate_question(payload)
    except YandaojieDefenseServiceError as exc:
        await _record_yandaojie_error_safely(
            persistence,
            YandaojieErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_question",
                error_scope="backend",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
                metadata={
                    "subject_id": payload.subject_id,
                    "subject_topic": payload.subject_topic,
                },
            ),
        )
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        await persistence.persist_generated_question(
            payload=payload,
            question=generated.question,
            model=generated.model,
            prompt=generated.prompt,
            generated_at=generated.generated_at,
        )
    except YandaojiePersistenceError as exc:
        await _record_yandaojie_error_safely(
            persistence,
            YandaojieErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_question_persist",
                error_scope="storage",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return YandaojieDefenseQuestionResponse(
        model=generated.model,
        round_index=payload.round_index,
        question=generated.question,
        generated_at=generated.generated_at,
        persistence_enabled=persistence.enabled,
    )


@router.post(
    "/yandaojie/defense/turn",
    response_model=YandaojieDefenseTurnResponse,
    tags=["yandaojie"],
)
async def save_yandaojie_defense_turn(
    payload: YandaojieDefenseTurnRequest,
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> YandaojieDefenseTurnResponse:
    """Persist a completed Yandaojie defense answer."""

    try:
        saved_at, completed_round_count = await persistence.persist_defense_turn(payload)
    except YandaojiePersistenceError as exc:
        await _record_yandaojie_error_safely(
            persistence,
            YandaojieErrorRecord(
                session_id=payload.session_id,
                student_id=payload.student_id,
                stage="defense_turn_persist",
                error_scope="storage",
                error_message=str(exc),
                raw_error=repr(exc),
                round_index=payload.round_index,
            ),
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return YandaojieDefenseTurnResponse(
        saved_at=saved_at,
        persistence_enabled=persistence.enabled,
        completed_round_count=completed_round_count,
    )


@router.get(
    "/yandaojie/research/overview",
    tags=["yandaojie"],
)
async def get_yandaojie_research_overview(
    limit: int | None = Query(None, ge=1, le=1000),
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> dict:
    """Return grouped Yandaojie student/session activity for internal review."""
    return await persistence.get_research_overview(limit=limit)


@router.get(
    "/yandaojie/research/session/{session_id}",
    tags=["yandaojie"],
)
async def get_yandaojie_research_session_detail(
    session_id: str,
    persistence: YandaojiePersistenceService = Depends(get_yandaojie_persistence),
) -> dict:
    """Return full details for one Yandaojie session."""
    result = await persistence.get_session_research_detail(session_id)
    if result.get("session") is None:
        raise HTTPException(status_code=404, detail="Yandaojie session not found")
    return result


@router.post("/tutor/chat", response_model=TutorChatResponse, tags=["tutor"])
async def create_tutor_chat_reply(
    payload: TutorChatRequest,
    tutor_service: TutorModeService = Depends(get_tutor_service),
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> TutorChatResponse:
    """Reply as the student-facing AI tutor for one learning objective."""

    payload = payload.model_copy(
        update={
            "reference_image_url": persistence.prepare_reference_image_url(
                payload.reference_image_url
            )
        }
    )

    if payload.session_id and payload.messages:
        latest_message = payload.messages[-1]
        if latest_message.role == "user":
            try:
                persistence.persist_chat_message(
                    session_id=payload.session_id,
                    student_id=payload.student_id,
                    objective_index=payload.objective_index,
                    role=latest_message.role,
                    content=latest_message.content,
                )
            except SaintPaulPersistenceError as exc:
                try:
                    persistence.record_error(
                        SaintPaulErrorRecord(
                            session_id=payload.session_id,
                            student_id=payload.student_id,
                            stage="chat_message_persist",
                            error_scope="storage",
                            error_message=str(exc),
                            raw_error=repr(exc),
                            tab="tutor",
                            objective_index=payload.objective_index,
                            metadata={"role": latest_message.role},
                        )
                    )
                except SaintPaulPersistenceError:
                    pass

    try:
        response = await tutor_service.chat_with_student(payload)
        if payload.session_id:
            try:
                persistence.persist_chat_message(
                    session_id=payload.session_id,
                    student_id=payload.student_id,
                    objective_index=payload.objective_index,
                    role=response.message.role,
                    content=response.message.content,
                    model=response.model,
                )
            except SaintPaulPersistenceError as exc:
                try:
                    persistence.record_error(
                        SaintPaulErrorRecord(
                            session_id=payload.session_id,
                            student_id=payload.student_id,
                            stage="chat_message_persist",
                            error_scope="storage",
                            error_message=str(exc),
                            raw_error=repr(exc),
                            tab="tutor",
                            objective_index=payload.objective_index,
                            metadata={"role": response.message.role},
                        )
                    )
                except SaintPaulPersistenceError:
                    pass
        return response
    except TutorServiceUnavailableError as exc:
        if payload.session_id:
            try:
                persistence.record_error(
                    SaintPaulErrorRecord(
                        session_id=payload.session_id,
                        student_id=payload.student_id,
                        stage="tutor_chat",
                        error_scope="backend",
                        error_message=str(exc),
                        raw_error=repr(exc),
                        tab="tutor",
                        objective_index=payload.objective_index,
                        metadata={"topic": payload.topic, "objective": payload.objective},
                    )
                )
            except SaintPaulPersistenceError:
                pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/tutor/image-explanation",
    response_model=TutorImageExplanationResponse,
    tags=["tutor"],
)
async def create_tutor_image_explanation(
    payload: TutorImageExplanationRequest,
    tutor_service: TutorModeService = Depends(get_tutor_service),
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> TutorImageExplanationResponse:
    """Generate a visual explanation for the selected learning objective."""

    try:
        response = await tutor_service.generate_image_explanation(payload)
        asset = None
        if payload.session_id:
            try:
                asset = persistence.upload_image_data_url(
                    session_id=payload.session_id,
                    objective_index=payload.objective_index,
                    image_data_url=response.image_data_url,
                )
                persistence.persist_image_artifact(
                    session_id=payload.session_id,
                    student_id=payload.student_id,
                    objective_index=payload.objective_index,
                    prompt=response.prompt,
                    source=response.source,
                    error=response.error,
                    asset=asset,
                )
            except SaintPaulPersistenceError as exc:
                try:
                    persistence.record_error(
                        SaintPaulErrorRecord(
                            session_id=payload.session_id,
                            student_id=payload.student_id,
                            stage="image_asset_persist",
                            error_scope="storage",
                            error_message=str(exc),
                            raw_error=repr(exc),
                            tab="tutor",
                            objective_index=payload.objective_index,
                            metadata={"topic": payload.topic, "objective": payload.objective},
                        )
                    )
                except SaintPaulPersistenceError:
                    pass
        response.asset_bucket = asset.bucket if asset else None
        response.asset_key = asset.key if asset else None
        response.asset_url = asset.url if asset else None
        return response
    except TutorServiceUnavailableError as exc:
        if payload.session_id:
            try:
                persistence.record_error(
                    SaintPaulErrorRecord(
                        session_id=payload.session_id,
                        student_id=payload.student_id,
                        stage="tutor_image_explanation",
                        error_scope="backend",
                        error_message=str(exc),
                        raw_error=repr(exc),
                        tab="tutor",
                        objective_index=payload.objective_index,
                        metadata={"topic": payload.topic, "objective": payload.objective},
                    )
                )
            except SaintPaulPersistenceError:
                pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/tutor/quiz", response_model=TutorQuizResponse, tags=["tutor"])
async def create_tutor_quiz(
    payload: TutorQuizRequest,
    tutor_service: TutorModeService = Depends(get_tutor_service),
    persistence: SaintPaulPersistenceService = Depends(get_saintpaul_persistence),
) -> TutorQuizResponse:
    """Generate a fresh multiple-choice quiz for the selected learning objective."""

    try:
        response = await tutor_service.generate_quiz(payload)
        if payload.session_id:
            try:
                persistence.persist_quiz_artifact(
                    session_id=payload.session_id,
                    student_id=payload.student_id,
                    objective_index=payload.objective_index,
                    title=response.title,
                    quiz_id=response.quiz_id,
                    questions=[question.model_dump(mode="json") for question in response.questions],
                    source=response.source,
                    error=response.error,
                )
            except SaintPaulPersistenceError as exc:
                try:
                    persistence.record_error(
                        SaintPaulErrorRecord(
                            session_id=payload.session_id,
                            student_id=payload.student_id,
                            stage="quiz_artifact_persist",
                            error_scope="storage",
                            error_message=str(exc),
                            raw_error=repr(exc),
                            tab="tutor",
                            objective_index=payload.objective_index,
                            metadata={"topic": payload.topic, "objective": payload.objective},
                        )
                    )
                except SaintPaulPersistenceError:
                    pass
        return response
    except TutorServiceUnavailableError as exc:
        if payload.session_id:
            try:
                persistence.record_error(
                    SaintPaulErrorRecord(
                        session_id=payload.session_id,
                        student_id=payload.student_id,
                        stage="tutor_quiz",
                        error_scope="backend",
                        error_message=str(exc),
                        raw_error=repr(exc),
                        tab="tutor",
                        objective_index=payload.objective_index,
                        metadata={"topic": payload.topic, "objective": payload.objective},
                    )
                )
            except SaintPaulPersistenceError:
                pass
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _record_usf_error_safely(
    persistence: UsfPersistenceService,
    payload: UsfErrorRecord,
) -> None:
    try:
        persistence.record_error(payload)
    except UsfPersistenceError:
        pass


async def _record_yandaojie_error_safely(
    persistence: YandaojiePersistenceService,
    payload: YandaojieErrorRecord,
) -> None:
    try:
        await persistence.record_error(payload)
    except YandaojiePersistenceError:
        pass


def _encode_event(payload: dict[str, object]) -> str:
    """Return a JSONL-safe representation of a streaming event."""

    return json.dumps(payload, separators=(",", ":")) + "\n"


@router.post(
    "/research/discover",
    response_model=None,
    tags=["research"],
    summary="Discover relevant arXiv papers with a streamed RAG workflow",
)
async def discover_research_papers(
    payload: ResearchSearchRequest,
    service: ResearchDiscoveryService = Depends(get_research_service),
) -> StreamingResponse:
    """Stream the reasoning trail for a research discovery request."""

    top_k = payload.top_k or 5

    async def event_stream():
        try:
            yield _encode_event(
                {
                    "type": "status",
                    "stage": "expanding_query",
                    "message": "Expanding your description with GPT-5",
                }
            )
            expansions = await service.expand_query(payload.query)
            yield _encode_event(
                {
                    "type": "expansion",
                    "stage": "expanding_query",
                    "message": "Generated expanded search intents",
                    "expansions": expansions,
                }
            )

            yield _encode_event(
                {
                    "type": "status",
                    "stage": "retrieving_candidates",
                    "message": "Querying arXiv for candidate papers",
                }
            )
            candidates = await service.retrieve_papers(expansions)
            yield _encode_event(
                {
                    "type": "retrieval",
                    "stage": "retrieving_candidates",
                    "message": f"Retrieved {len(candidates)} unique arXiv candidates",
                    "count": len(candidates),
                }
            )

            yield _encode_event(
                {
                    "type": "status",
                    "stage": "ranking",
                    "message": "Ranking candidates with Cohere's re-ranker",
                }
            )
            ranked = await service.rank_papers(
                query=payload.query, papers=candidates, top_k=top_k
            )
            ranked_summaries = [
                paper.to_summary(score=score).model_dump(mode="json")
                for paper, score in ranked
            ]
            yield _encode_event(
                {
                    "type": "ranking",
                    "stage": "ranking",
                    "message": "Identified the strongest matches",
                    "total_candidates": len(candidates),
                    "results": ranked_summaries,
                }
            )

            enriched: list[ResearchPaperSummary] = []
            for paper, score in ranked:
                yield _encode_event(
                    {
                        "type": "status",
                        "stage": "explaining",
                        "message": f"Explaining relevance for {paper.title}",
                        "paper_id": paper.paper_id,
                    }
                )
                reason = await service.explain_relevance(query=payload.query, paper=paper)
                summary = paper.to_summary(score=score, reason=reason)
                enriched.append(summary)
                yield _encode_event(
                    {
                        "type": "explanation",
                        "stage": "explaining",
                        "paper_id": paper.paper_id,
                        "reason": reason,
                    }
                )

            yield _encode_event(
                {
                    "type": "results",
                    "stage": "complete",
                    "message": "Finished building the research digest",
                    "results": [item.model_dump(mode="json") for item in enriched],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive streaming guard
            yield _encode_event(
                {
                    "type": "error",
                    "stage": "error",
                    "message": str(exc),
                }
            )

    return StreamingResponse(event_stream(), media_type="application/jsonl")


@router.post(
    "/generative-ui/chat",
    response_model=GenerativeUIResponse,
    tags=["generative-ui"],
)
async def generative_ui_chat(
    payload: GenerativeUIRequest,
    service: GenerativeUIService = Depends(get_generative_ui_service),
) -> GenerativeUIResponse:
    """Chat endpoint that returns UI guidance and theme suggestions."""

    current_theme = None
    if payload.current_theme:
        current_theme = ThemeSuggestion(
            primary_color=payload.current_theme.primary_color,
            background_color=payload.current_theme.background_color,
            accent_color=payload.current_theme.accent_color,
            text_color=payload.current_theme.text_color,
        )

    try:
        result = await service.generate(
            messages=[message.model_dump() for message in payload.messages],
            current_theme=current_theme,
        )
    except GenerativeUIServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    suggested_theme = None
    if result.theme:
        suggested_theme = {
            "primary_color": result.theme.primary_color,
            "background_color": result.theme.background_color,
            "accent_color": result.theme.accent_color,
            "text_color": result.theme.text_color,
        }

    return GenerativeUIResponse(message=result.message, suggested_theme=suggested_theme)
