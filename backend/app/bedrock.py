import asyncio
import json
import re
import time
from typing import Any

import boto3

from app.config import get_settings
from app.models import QnAItem


def _build_profile_block(user_profile: dict | None) -> str:
    if not user_profile:
        return ""
    parts = [f"닉네임: {user_profile.get('nickname', '')}"]
    if user_profile.get("occupation"):
        parts.append(f"직업: {user_profile['occupation']}")
    if user_profile.get("interests"):
        parts.append(f"관심사: {', '.join(user_profile['interests'])}")
    if user_profile.get("hobbies"):
        parts.append(f"취미: {', '.join(user_profile['hobbies'])}")
    return "사용자 정보: " + " / ".join(parts)


def _build_rag_block(rag_items: list[QnAItem]) -> str:
    if not rag_items:
        return "이전 일기 없음"
    sorted_items = sorted(rag_items, key=lambda x: x.asked_at, reverse=True)
    lines = []
    for item in sorted_items:
        if item.answer:
            lines.append(f"[{item.asked_at.date()}] Q: {item.question} / A: {item.answer}")
    return "\n".join(lines) if lines else "이전 일기 없음"


def _build_session_block(session_items: list[QnAItem]) -> str:
    answered = [i for i in session_items if i.answer is not None]
    answered.sort(key=lambda x: x.sequence)
    if not answered:
        return ""
    lines = [f"Q{i.sequence}: {i.question}\nA{i.sequence}: {i.answer}" for i in answered]
    return "\n".join(lines)


def _invoke_claude(client: Any, model_id: str, prompt: str) -> tuple[str, dict]:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    t0 = time.monotonic()
    response = client.invoke_model(
        modelId=model_id,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    latency_ms = int((time.monotonic() - t0) * 1000)
    result = json.loads(response["body"].read())
    text = result["content"][0]["text"]
    usage = result.get("usage", {})
    meta = {
        "model_id": model_id,
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "latency_ms": latency_ms,
    }
    return text, meta


class BedrockClient:
    def __init__(self, region: str | None = None, model_id: str | None = None):
        cfg = get_settings()
        self._region = region or cfg.aws_region
        self._model_id = model_id or cfg.bedrock_model_id
        self._client = boto3.client("bedrock-runtime", region_name=self._region)

    async def generate_question(
        self,
        rag_items: list[QnAItem],
        session_so_far: list[QnAItem],
        next_sequence: int,
        user_profile: dict | None = None,
    ) -> tuple[str, dict]:
        profile_block = _build_profile_block(user_profile)
        rag_block = _build_rag_block(rag_items)
        session_block = _build_session_block(session_so_far)
        profile_line = f"{profile_block}\n" if profile_block else ""
        prompt = (
            f"당신은 사용자의 하루를 일기로 기록하는 AI입니다.\n"
            f"{profile_line}"
            f"사용자의 과거 일기 참고:\n{rag_block}\n\n"
            f"오늘 지금까지의 대화:\n{session_block}\n\n"
            f"위 내용을 바탕으로 {next_sequence}번째 질문을 한 문장으로 작성하세요. "
            f"총 5개의 질문을 통해 하루 일기를 완성합니다.\n"
            f"규칙: 마크다운(**, *, #, ` 등) 절대 사용 금지. 이모지 절대 사용 금지. 순수 텍스트 한 문장만 출력."
        )
        text, meta = await asyncio.to_thread(
            _invoke_claude, self._client, self._model_id, prompt
        )
        return text.strip(), meta

    async def generate_diary(
        self,
        qna_items: list[QnAItem],
        user_profile: dict | None = None,
    ) -> tuple[str, str, dict]:
        profile_block = _build_profile_block(user_profile)
        sorted_items = sorted(qna_items, key=lambda x: x.sequence)
        qa_text = "\n".join(
            f"Q{i.sequence}: {i.question}\nA{i.sequence}: {i.answer}" for i in sorted_items
        )
        profile_line = f"{profile_block}\n" if profile_block else ""
        prompt = (
            f"아래 질문과 답변을 바탕으로 한국어 일기와 요약을 작성하세요.\n"
            f"자연스럽고 감성적인 문체로, 1인칭 시점으로 작성합니다.\n"
            f"{profile_line}\n"
            f"{qa_text}\n\n"
            f"반드시 아래 형식으로만 응답하세요(다른 텍스트 금지):\n"
            f"<diary>500자 이내 일기 본문</diary>\n"
            f"<summary>100자 이내 요약문</summary>"
        )
        text, meta = await asyncio.to_thread(
            _invoke_claude, self._client, self._model_id, prompt
        )
        raw = text.strip()
        diary_match = re.search(r"<diary>(.*?)</diary>", raw, re.DOTALL)
        summary_match = re.search(r"<summary>(.*?)</summary>", raw, re.DOTALL)
        if diary_match and summary_match:
            body = diary_match.group(1).strip()
            summary = summary_match.group(1).strip()
        else:
            body = raw
            summary = ""
        return body, summary, meta
