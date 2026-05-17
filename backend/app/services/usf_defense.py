"""LLM-backed question generation for the USF defense workflow."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from textwrap import dedent
from typing import Any

import httpx

from app.schemas.usf import UsfDefenseQuestionRequest

logger = logging.getLogger(__name__)


class UsfDefenseServiceError(RuntimeError):
    """Raised when a USF defense question cannot be generated."""


@dataclass
class UsfGeneratedQuestion:
    """Generated defense question plus prompt metadata."""

    model: str
    question: str
    generated_at: datetime
    prompt: str


class UsfDefenseService:
    """Generate probing defense questions scoped to course objectives."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate_question(
        self, payload: UsfDefenseQuestionRequest
    ) -> UsfGeneratedQuestion:
        """Return exactly one follow-up question for the current defense round."""

        if not self.api_key:
            raise UsfDefenseServiceError("USF defense question generation is not configured")

        prompt = self.build_prompt(payload)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "text": {"format": {"type": "json_object"}},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=body,
                )
            response.raise_for_status()
            data = response.json()
            content = self._extract_json_text(data)
            question = self._parse_question(content)
        except Exception as exc:
            logger.exception("USF defense question generation failed")
            raise UsfDefenseServiceError(
                "Unable to generate a USF defense question"
            ) from exc

        return UsfGeneratedQuestion(
            model=self.model,
            question=question,
            generated_at=datetime.now(timezone.utc),
            prompt=prompt,
        )

    def build_prompt(self, payload: UsfDefenseQuestionRequest) -> str:
        """Build the prompt used for question generation."""

        objectives = (
            "\n".join(f"- {objective}" for objective in payload.learning_objectives)
            or "- No learning objectives were provided; anchor questions to the module topic."
        )
        learned_response = (
            payload.learned_response
            or "No pre-defense reflection was required for this module."
        )
        remaining_questions_response = (
            payload.remaining_questions_response
            or "No pre-defense reflection was required for this module."
        )
        previous_turns = "\n\n".join(
            dedent(
                f"""
                Round {turn.round_index + 1}
                Question: {turn.question}
                Student answer: {turn.answer_text or 'No answer captured.'}
                Voice transcript: {turn.audio_transcript or 'none'}
                Self-rating: {f'{turn.self_rating}/10' if turn.self_rating is not None else 'not collected'}
                """
            ).strip()
            for turn in payload.previous_turns
        )

        return dedent(
            f"""
            You are running a rigorous but supportive live defense for an undergraduate course
            on digital identity. Act like a thesis-defense examiner: analyze the student's
            claims, look for weak reasoning, missing evidence, overgeneralizations, or unresolved
            questions, and ask the next best connected follow-up question. This is a continuous
            defense conversation, not a random quiz.

            Hard constraints:
            - Return JSON only with this shape: {{"question": "..."}}.
            - Generate exactly one follow-up question, not a list and not multiple questions.
            - The question field must contain one question mark total.
            - Do not combine two prompts with "and", "also", "then", or a second question mark.
            - Keep it concise enough for a 30-second student response.
            - Base the question on the student's reflection and stated remaining questions.
            - Stay inside the selected module's learning objectives when provided.
            - If no learning objectives are provided, stay tightly tied to the selected module topic.
            - Do not answer the question for the student.
            - Do not repeat previous questions.
            - Make the new question clearly follow from the immediately previous question and
              student answer when previous turns exist.
            - Do not jump randomly across learning objectives. Use the objectives as guardrails,
              but let the prior answer determine the next probe.

            Session:
            - Student ID: {payload.student_id}
            - Module: {payload.module_number} - {payload.module_topic}
            - Week: {payload.module_week or 'not provided'}
            - Round: {payload.round_index + 1} of 5

            Learning objectives:
            {objectives}

            Student reflection:
            What they learned:
            {learned_response}

            Remaining questions:
            {remaining_questions_response}

            Previous defense turns:
            {previous_turns or 'No previous defense turns yet.'}

            Choose the single highest-priority follow-up question that continues the thread of
            the defense, especially the most recent answer. It should sound like a natural next
            probe from an examiner who is listening closely, while remaining fair and tied to the
            objectives or module topic.
            """
        ).strip()

    def _extract_json_text(self, data: dict[str, Any]) -> str:
        if isinstance(data.get("output_text"), str):
            return str(data["output_text"])

        for item in data.get("output", []):
            if isinstance(item, dict):
                if item.get("type") == "output_text" and isinstance(item.get("text"), str):
                    return str(item["text"])
                for content in item.get("content", []):
                    if isinstance(content, dict) and isinstance(content.get("text"), str):
                        return str(content["text"])

        raise UsfDefenseServiceError("Unexpected response from defense question service")

    def _parse_question(self, content: str) -> str:
        try:
            parsed = httpx.Response(200, text=content).json()
        except Exception as exc:
            raise UsfDefenseServiceError("Defense question response was not JSON") from exc

        question = parsed.get("question") if isinstance(parsed, dict) else None
        if not isinstance(question, str) or not question.strip():
            raise UsfDefenseServiceError("Defense question response did not include a question")

        return _single_follow_up_question(question)


def _single_follow_up_question(question: str) -> str:
    """Normalize accidental multi-question model output to one follow-up question."""

    normalized = " ".join(question.strip().split())
    if not normalized:
        raise UsfDefenseServiceError("Defense question response did not include a question")

    numbered_match = re.match(r"^(?:\d+[.)]|[-*])\s*(.+)$", normalized)
    if numbered_match:
        normalized = numbered_match.group(1).strip()

    question_mark_index = normalized.find("?")
    if question_mark_index != -1:
        return normalized[: question_mark_index + 1].strip()

    first_line = re.split(r"(?:\s+\d+[.)]\s+|\s+[-*]\s+)", normalized, maxsplit=1)[0]
    return first_line.strip()
