"""Audio transcription helpers."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class AudioTranscriptionError(RuntimeError):
    """Raised when the transcription service fails."""


@dataclass
class TranscriptionResult:
    """Return payload for an audio transcription request."""

    text: str


class AudioTranscriber:
    """Thin wrapper around the OpenAI transcription endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def transcribe(
        self,
        payload: bytes,
        content_type: str | None,
    ) -> TranscriptionResult:
        """Transcribe the provided audio bytes into text."""

        headers = {"Authorization": f"Bearer {self._api_key}"}
        form = {"model": self._model}

        mime = content_type or "audio/webm"
        filename = f"recording.{_extension_for_content_type(mime)}"
        files = {"file": (filename, payload, mime)}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/audio/transcriptions",
                    headers=headers,
                    data=form,
                    files=files,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - depends on upstream
                detail = _extract_openai_error_message(exc.response)
                raise AudioTranscriptionError(
                    f"Transcription service rejected the audio: {detail}"
                ) from exc
            except httpx.HTTPError as exc:  # pragma: no cover - network errors not deterministic
                raise AudioTranscriptionError("Failed to contact the transcription service") from exc

        data = response.json()
        try:
            text = data["text"].strip()
        except (KeyError, TypeError) as exc:
            raise AudioTranscriptionError("Unexpected response from transcription service") from exc

        return TranscriptionResult(text=text)


def _extension_for_content_type(content_type: str) -> str:
    """Return an OpenAI-supported file extension matching the browser MIME type."""

    mime = content_type.split(";", 1)[0].strip().lower()
    if mime in {"audio/wav", "audio/wave", "audio/x-wav"}:
        return "wav"
    if mime in {"audio/mpeg", "audio/mp3"}:
        return "mp3"
    if mime in {"audio/mp4", "audio/m4a", "audio/x-m4a"}:
        return "m4a"
    if mime in {"video/mp4"}:
        return "mp4"
    if mime in {"audio/webm", "video/webm"}:
        return "webm"
    if mime in {"audio/mpga"}:
        return "mpga"
    return "webm"


def _extract_openai_error_message(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:500] or f"HTTP {response.status_code}"

    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"]
    return response.text[:500] or f"HTTP {response.status_code}"


__all__ = ["AudioTranscriber", "AudioTranscriptionError", "TranscriptionResult"]

