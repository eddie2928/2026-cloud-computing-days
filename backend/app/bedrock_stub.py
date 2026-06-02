from datetime import date, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import QnAItem

_STUB_META = {
    "model_id": "stub",
    "input_tokens": 0,
    "output_tokens": 0,
    "latency_ms": 0,
    "prompt": "stub",
    "raw_response": "<stub>",
}

_STUB_QUESTIONS = [
    "오늘 하루 중 가장 기억에 남는 순간은 무엇인가요?",
    "그 순간에 어떤 감정을 느꼈나요?",
    "오늘 만난 사람들 중 인상 깊었던 사람이 있나요?",
    "내일 꼭 해보고 싶은 일이 있나요?",
    "오늘 자신에게 칭찬해주고 싶은 점은 무엇인가요?",
]

_STUB_DIARIES = [
    (
        "오늘은 출근길에 따뜻한 햇살을 맞으며 걸었다. 작은 카페에서 마신 아메리카노 한 잔이 하루를 열어주었고, 그 여유로운 순간이 온종일 마음에 남았다.",
        "출근길 햇살과 커피 한 잔으로 시작된 여유로운 하루",
    ),
    (
        "오늘은 오랜 친구와 오랜만에 통화를 했다. 바쁜 일상 속에서도 서로의 안부를 묻고 웃을 수 있어 마음이 따뜻해졌다. 소소한 연결이 큰 위안이 된다는 것을 다시 느꼈다.",
        "오랜 친구와의 통화로 일상의 따뜻함을 다시 느낀 날",
    ),
    (
        "저녁에 혼자 요리를 해 먹었다. 서툴렀지만 직접 만든 된장찌개의 맛이 생각보다 훨씬 좋았다. 작은 성취감이 하루를 충분히 뿌듯하게 만들어 주었다.",
        "직접 끓인 된장찌개에서 찾은 소소한 성취감",
    ),
    (
        "오늘은 집에서 책을 읽으며 조용히 보냈다. 좋아하는 작가의 문장들이 마음을 채워주었고, 아무 계획도 없이 쉬는 것이 오히려 큰 활력이 된다는 걸 깨달았다.",
        "독서와 휴식으로 채운 조용하고 충만한 하루",
    ),
    (
        "오늘 처음 도전한 새로운 운동 클래스에서 생각보다 잘 해냈다. 몸이 뻐근하지만 뿌듯함이 더 크다. 새로운 것에 용기를 내는 자신이 자랑스럽다.",
        "새 운동 클래스 도전으로 발견한 나의 가능성",
    ),
]


_STUB_SUGGESTIONS = [
    ["네, 좋았어요.", "별로 기억나는 게 없어요.", "생각해볼게요."],
    ["기쁘고 설렜어요.", "조금 피곤했어요.", "평범한 하루였어요."],
    ["특별히 없었어요.", "동료와 이야기했어요.", "혼자 있었어요."],
    ["쉬고 싶어요.", "새로운 걸 해보고 싶어요.", "아직 모르겠어요."],
    ["열심히 한 것 같아요.", "큰 것은 아니지만 버텼어요.", "잘 모르겠어요."],
]


class BedrockStubClient:
    async def generate_question(
        self,
        rag_summaries: list,
        session_so_far: list,
        next_sequence: int,
        user_profile: dict | None = None,
        relevant_schedules: list[str] | None = None,
        today: date | None = None,
        previously_extracted: str = "",
    ) -> tuple[str, list[dict], list[str], dict]:
        idx = ((next_sequence - 1) % 5)
        question = _STUB_QUESTIONS[idx]
        suggestions = _STUB_SUGGESTIONS[idx]
        # sequence 3(2번째 답변 후)에서 시간 포함 샘플 일정 반환 — UI 모달 흐름 확인용
        schedules: list[dict] = []
        if next_sequence == 3:
            today_str = str(today or date.today())
            schedules = [{
                "period_start": today_str,
                "period_end": today_str,
                "start_time": "14:00",
                "end_time": "16:00",
                "situation": "친구와 카페에서 공부 (더미 일정)",
            }]
        return question, schedules, suggestions, dict(_STUB_META)

    async def generate_diary(
        self,
        qna_items: list,
        user_profile: dict | None = None,
    ) -> tuple[str, str, dict]:
        idx = (len(qna_items) % 5)
        body, summary = _STUB_DIARIES[idx]
        return body, summary, dict(_STUB_META)

    async def generate_plan(
        self,
        description: str,
        period_start: date,
        period_end: date,
        goal: str,
        user_profile: dict | None = None,
    ) -> tuple[str, date, date, list[dict], dict]:
        """
        returns (title, period_start, period_end, days, meta)
          title: AI가 결정한 Plan 이름
          period_start/end: AI가 결정한 Plan 시작·종료일
          days: [{"date": date, "todos": ["...", ...]}, ...]
          meta: bedrock_meta dict
        """
        _DAILY_TODOS = ["아침 루틴", "핵심 작업", "마무리 회고"]
        title = (description[:14] + "…") if len(description) > 14 else description
        if not title:
            title = "AI Plan 초안"
        days = []
        current = period_start
        while current <= period_end:
            days.append({"date": current, "todos": list(_DAILY_TODOS)})
            current += timedelta(days=1)
        return title, period_start, period_end, days, dict(_STUB_META)
