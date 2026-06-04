---
name: diary-insights
description: >
  Use when querying or analyzing stored diary data through the qna-diary MCP
  server — listing users, reading diary entries over a date range, summarizing
  a specific day's full QnA + diary, analyzing emotion trends, or correlating
  life events (schedules) with mood. Documents the read-only workflow over the
  six mcp__qna-diary__* tools.
user-invocable: true
---

# diary-insights — qna-diary MCP 조회·분석 가이드

## 사전 점검: 서버 연결 확인

분석 시작 전 `.mcp.json`에 유효한 IP가 채워져 있고 MCP EC2가 기동 중인지 확인한다.

서버가 응답하지 않으면:

1. EC2 기동: AWS 콘솔 또는 CLI로 MCP EC2를 start
2. IP 갱신:
   ```bash
   cd infra
   terraform refresh
   terraform output -raw mcp_public_ip
   ```
3. `.mcp.json`의 `<MCP_PUBLIC_IP>` 자리를 얻은 IP로 교체
4. Claude Code 재시작

---

## 0. 대상 사용자 확보 (모든 분석의 출발점)

**항상 `mcp__qna-diary__list_users`로 시작한다.** user_id를 알고 있어도 먼저 목록을 호출해 확인한다.

```
mcp__qna-diary__list_users()
```

반환: `[{"user_id": ..., "display_name": ..., "profile": {...|null}}]` 목록 — `user_id`를 다른 모든 도구의 입력으로 사용한다.

프로필 맥락이 필요하면 `mcp__qna-diary__get_user_info`로 보강한다.

```
mcp__qna-diary__get_user_info(user_id=<id>)
```

반환 필드: `nickname`, `gender`, `age`, `occupation`, `hobbies`, `interests` (미설정 시 `null`)

---

## 워크플로우 1: 기간별 일기 조회/요약

### 1단계: 요약 목록으로 개관

```
mcp__qna-diary__list_diaries(
  user_id=<id>,
  date_from="YYYY-MM-DD",
  date_to="YYYY-MM-DD"
)
```

- 반환: `diary_date`, `emotion`, `summary`(한 줄 요약), `created_at`
- 본문 미포함 — 응답 크기 절약
- 날짜 범위는 포함(inclusive), 날짜 오름차순 정렬
- 해당 기간 일기가 없으면 빈 배열 `[]` 반환

### 2단계: 특정일 상세 조회 (사용자가 요청할 때만)

```
mcp__qna-diary__get_diary_session(
  user_id=<id>,
  date="YYYY-MM-DD"
)
```

- 반환: QnA 전체 대화(`qna_items`, `sequence` 순) + 일기 전문(`diary.body`)
- `status: in_progress`이면 `diary`가 `null` → "아직 완료되지 않은 일기입니다"라고 안내
- 해당 날짜 세션이 없으면 `data: null` 반환

---

## 워크플로우 2: 감정 흐름 분석

```
mcp__qna-diary__get_emotion_trend(
  user_id=<id>,
  date_from="YYYY-MM-DD",
  date_to="YYYY-MM-DD"
)
```

- 반환: `[{"diary_date": "...", "emotion": "..."}]` 날짜 오름차순
- 감정값: `happy` / `sad` / `angry` / `neutral` / `bored` 5종 (서버 고정 열거값 — 이 외 값은 반환되지 않음)
- **일기가 없는 날짜는 결과에서 누락됨** — 갭이 있으면 사용자에게 명시
- 전체 기간 일기가 없으면 빈 배열 `[]` 반환

분석 패턴 예시:

- 연속 구간: 동일 감정이 며칠 이어지는지
- 변화점: 감정이 급격히 바뀐 날짜
- 기간 비교: 두 기간의 감정 분포 비교

---

## 워크플로우 3: 생활 이벤트 연관 분석

### 1단계: 일정 조회

```
mcp__qna-diary__get_user_schedules(
  user_id=<id>,
  date_from="YYYY-MM-DD",  # 선택
  date_to="YYYY-MM-DD"     # 선택
)
```

- 날짜 인자 생략 시 전체 일정 반환
- 범위 겹침 필터: `period_end >= date_from AND period_start <= date_to`
- 반환 필드: `period_start`, `period_end`, `situation`(사용자 작성 자유 텍스트)

### 2단계: 워크플로우 1·2와 결합

`get_user_schedules`로 얻은 일정의 `period_start`를 `date_from`으로, `period_end`를 `date_to`로 사용해 `get_emotion_trend` 또는 `list_diaries`를 호출한다.

해석 예시: "이 기간 동안 situation이 X였고, 감정 레이블이 Y에서 Z로 바뀌었다"

---

## 에러 응답 처리

모든 도구는 `{"status": "error", "code": "...", "message": "..."}` 형식으로 오류를 반환한다.

| code             | 의미            | 대응                                 |
| ---------------- | --------------- | ------------------------------------ |
| `USER_NOT_FOUND` | 잘못된 user_id  | `list_users` 재호출로 올바른 id 확인 |
| `INVALID_DATE`   | 날짜 형식 오류  | `YYYY-MM-DD` 형식으로 교정 후 재호출 |
| `DB_ERROR`       | 서버 측 DB 오류 | EC2·RDS 기동 여부 점검 안내          |

---

## 응답 작성 규칙

1. 데이터에 없는 내용은 추측하지 않는다
2. 모든 날짜는 `YYYY-MM-DD` 형식으로 표시한다
3. 일기 본문(`diary.body`)과 QnA 내용은 개인적 내용이므로 전문 그대로 출력하지 않고 관련 부분만 요약하거나 패러프레이즈한다
4. 분석 결과를 제시할 때 근거가 된 날짜·일기·감정을 함께 제시한다
