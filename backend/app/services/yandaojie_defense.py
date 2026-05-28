"""LLM-backed question generation for the Yandaojie defense workflow using DeepSeek API."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from textwrap import dedent
from typing import Any

import httpx

from app.schemas.yandaojie import YandaojieDefenseQuestionRequest

logger = logging.getLogger(__name__)

_MAX_RETRIES = 1
_RETRY_BACKOFF_SECONDS = 2.0


class YandaojieDefenseServiceError(RuntimeError):
    """Raised when a Yandaojie defense question cannot be generated."""


@dataclass
class YandaojieGeneratedQuestion:
    """Generated defense question plus prompt metadata."""

    model: str
    question: str
    generated_at: datetime
    prompt: str
    reasoning_content: str | None = None
    targeted_objectives: list[dict[str, Any]] | None = None
    diagnoses: dict[str, list[str]] | None = None


class YandaojieDefenseService:
    """Generate probing defense questions for Chinese elementary school subjects via DeepSeek."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-pro",
        timeout: float = 180.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate_question(
        self, payload: YandaojieDefenseQuestionRequest
    ) -> YandaojieGeneratedQuestion:
        """Return exactly one follow-up question for the current defense round."""

        if not self.api_key:
            raise YandaojieDefenseServiceError(
                "Yandaojie defense question generation is not configured (missing DEEPSEEK_API_KEY)"
            )

        system_prompt, user_prompt = self._build_messages(payload)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "thinking": {"type": "enabled"},
            "reasoning_effort": "high",
            "temperature": 0.7,
            "stream": False,
        }

        try:
            data = await self._call_deepseek_with_retry(headers, body)
            content = self._extract_content(data)
            reasoning_content = self._extract_reasoning_content(data)
            question, targeted_objectives, diagnoses = self._parse_question(content)
        except YandaojieDefenseServiceError:
            raise
        except Exception as exc:
            logger.exception("Yandaojie defense question generation failed")
            raise YandaojieDefenseServiceError(
                "Unable to generate a Yandaojie defense question"
            ) from exc

        return YandaojieGeneratedQuestion(
            model=data.get("model", self.model),
            question=question,
            generated_at=datetime.now(timezone.utc),
            prompt=user_prompt,
            reasoning_content=reasoning_content,
            targeted_objectives=targeted_objectives,
            diagnoses=diagnoses,
        )

    async def _call_deepseek_with_retry(
        self, headers: dict[str, str], body: dict[str, Any]
    ) -> dict[str, Any]:
        """POST to DeepSeek with one retry on timeout."""
        last_exc: httpx.ReadTimeout | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    )
                response.raise_for_status()
                return response.json()
            except httpx.ReadTimeout as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    backoff = _RETRY_BACKOFF_SECONDS * (attempt + 1)
                    logger.warning(
                        "DeepSeek ReadTimeout (attempt %d/%d), retrying in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES + 1,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    logger.error(
                        "DeepSeek ReadTimeout after %d attempts", _MAX_RETRIES + 1
                    )
        assert last_exc is not None
        raise last_exc

    def _build_messages(
        self, payload: YandaojieDefenseQuestionRequest
    ) -> tuple[str, str]:
        """Build system and user prompts for DeepSeek chat completions."""

        system_prompt = dedent("""
            你是一位严谨但友善的小学六年级教师，正在对学生进行"知识保卫"答辩。
            你的角色类似论文答辩考官：分析学生的回答，寻找推理薄弱处、缺少证据、
            过度概括或未解决的疑问，然后提出下一个最佳的追问。这是一场连续的答辩
            对话，而非随机测验。

            严格约束:
            - 仅返回JSON，格式为: {"question": "...", "targeted_objectives": [{"objective_index": 1, "reason": "..."}], "diagnoses": {"mastered": ["..."], "not_mastered": ["..."]}}
            - question: 你的追问文本。
            - targeted_objectives: 一个数组，说明这个问题考察的是哪个（些）教学目标，以及为什么。objective_index从1开始编号，对应上面的目标编号。reason应解释：这个问题如何帮助你发现学生对该教学目标掌握薄弱的地方（而非帮学生复习）。
            - diagnoses: 基于学生目前所有回答（包括反思内容）的诊断分析。mastered列出学生已展示掌握的知识点，not_mastered列出学生尚未掌握或表现薄弱的知识点。每项用简短一句话描述。每一轮都必须提供诊断。
            - 生成恰好一个追问，不要列表或多个问题。
            - question字段中只能有一个问号。
            - 不要用"和""另外""然后"拼接两个问题。
            - 问题要简洁，适合小学六年级学生30秒内回答。
            - 必须用简体中文提问。
            - 基于学生的反思和前序回答来提问。
            - 紧扣教学目标。
            - 不要替学生回答问题。
            - 不要重复之前的问题。
            - 让新问题明确地承接上一轮的回答。
            - 你的问题必须直接引用或回应学生在上一轮说过的某个具体内容。如果学生未提供有意义的回答，要求学生展开说明，而不是引入新的知识点。
            - 必须提出开放式问题（如"为什么""怎么""请解释"），不要问是非题或选择题。
            - 你的追问必须直接考察教学目标中明确提到的知识或能力，不要偏离到与教学目标无直接关系的泛泛话题讨论。
            - 如果科目是英语课：学生可以用中文或英文回答。如果你的问题需要学生用英文作答（例如造句、写词汇、写短文），必须在问题中明确写出"请用英语回答"或"Please answer in English"，不能假设学生会自动用英语。
        """).strip()

        objectives = "\n".join(
            f"- 目标{i + 1}: {obj}"
            for i, obj in enumerate(payload.learning_objectives)
        ) or "- 未提供具体教学目标，请围绕课程主题提问。"

        reflections_text = ""
        for r in payload.reflections:
            reflections_text += f"\n目标{r.objective_index + 1}的反思:\n"
            reflections_text += f"  学生所学: {r.learned or '未填写'}\n"
            reflections_text += f"  学生疑问: {r.questions or '未填写'}\n"

        previous_turns = "\n\n".join(
            dedent(f"""
                第{turn.round_index + 1}轮
                问题: {turn.question}
                学生回答: {turn.answer_text or '未作答'}
            """).strip()
            for turn in payload.previous_turns
        )

        user_prompt = dedent(f"""
            科目: {payload.subject_label}
            课题: {payload.subject_topic}
            年级: 小学六年级
            轮次: 第{payload.round_index + 1}轮 / 共5轮

            教学目标:
            {objectives}

            学生反思:
            {reflections_text or '学生未提供反思。'}

            前序答辩轮次:
            {previous_turns or '尚无前序答辩。'}

            请选择一个最具针对性的追问，自然地承接上一轮回答（如果有），
            同时保持公平并紧扣教学目标。仅返回JSON。
        """).strip()

        return system_prompt, user_prompt

    def build_prompt(self, payload: YandaojieDefenseQuestionRequest) -> str:
        """Build the full prompt (for logging/persistence)."""
        _, user_prompt = self._build_messages(payload)
        return user_prompt

    def _extract_content(self, data: dict[str, Any]) -> str:
        """Extract the assistant message content from DeepSeek chat completion response."""
        choices = data.get("choices", [])
        if not choices:
            raise YandaojieDefenseServiceError(
                "DeepSeek returned no choices in response"
            )

        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise YandaojieDefenseServiceError(
                "DeepSeek response had empty content"
            )
        return content.strip()

    def _extract_reasoning_content(self, data: dict[str, Any]) -> str | None:
        """Extract the reasoning_content (chain-of-thought) from DeepSeek response, if present."""
        choices = data.get("choices", [])
        if not choices:
            return None
        message = choices[0].get("message", {})
        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()
        return None

    def _parse_question(self, content: str) -> tuple[str, list[dict[str, Any]] | None, dict[str, list[str]] | None]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise YandaojieDefenseServiceError(
                "Defense question response was not valid JSON"
            ) from exc

        question = parsed.get("question") if isinstance(parsed, dict) else None
        if not isinstance(question, str) or not question.strip():
            raise YandaojieDefenseServiceError(
                "Defense question response did not include a question"
            )

        targeted_objectives = None
        if isinstance(parsed, dict) and isinstance(parsed.get("targeted_objectives"), list):
            targeted_objectives = parsed["targeted_objectives"]

        diagnoses = None
        if isinstance(parsed, dict) and isinstance(parsed.get("diagnoses"), dict):
            diagnoses = parsed["diagnoses"]

        return question.strip(), targeted_objectives, diagnoses

