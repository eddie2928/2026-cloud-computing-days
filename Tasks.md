# Task-1: AI 채팅 세션 UI 마무리 (이어서 하기 + 일기 생성 로딩 + 에러 처리)

> **상태**: 작성 완료, 사용자 승인 대기 중
> **인코딩**: UTF-8 (BOM 없음)
> **작성일**: 2026-05-22
> **선행 조건**: Task-1 ~ Task-4 완료 (백엔드 34 / 프론트 18 테스트 통과)
> **후속 작업**: Task-6 (AWS 실배포), Task-7 (선택)

---

## 1. Goal (목적)

roadmap.md의 **Task-1: AI 채팅 세션 UI 마무리** 항목을 처리한다. Task-3에서 채팅 패널을 모달로 통합하는 것까지는 완료됐고, 본 Task는 **사용자 경험 미결 사항 3건**을 마무리한다.

1. **이어서 하기 (Resume UX)**: 5문답 도중 모달을 닫고 다시 같은 날짜를 클릭했을 때, 이전에 답변한 Q/A가 채팅 히스토리에 그대로 복원되어야 한다. (현재는 첫 미답변 질문 1개만 표시되어 사용자가 어디까지 했는지 알 수 없음.)
2. **일기 생성 로딩 UI**: 5번째 답변 전송 후 Bedrock의 일기 생성에 1~3초 걸린다. 일반 "Thinking..."과 구분되는 명시적 로딩 화면을 노출해, 사용자가 답변이 끊긴 게 아니라 일기가 생성 중임을 인지하도록 한다.
3. **조기 종료 안내 + 에러 처리 보강**: 채팅 진행 중 모달 닫기 시 "진행 상황은 자동 저장됩니다. 같은 날짜를 다시 클릭하면 이어서 진행할 수 있어요" 안내를 1회 표시한다. 네트워크 끊김 등 5xx/네트워크 에러 시 "재시도" 버튼을 제공한다.

본 Task는 **백엔드 API 1개 확장**(`POST /api/qna/start` 응답에 `history` 필드 추가)과 **프론트엔드 채팅 컴포넌트 보강**이 중심이다. 새 라우터/페이지는 없다.

---

## 2. Context (사전 조사 결과)

### 2.1 현재 상태와 Task-1 후 차이

| 영역 | 현재 (Task-4 완료 시점) | Task-1 후 |
| --- | --- | --- |
| `POST /api/qna/start` 응답 | `{session_id, question, sequence}` (첫 미답변 질문 1개) | `+ history: [{sequence, question, answer}]` (이전 답변 포함) |
| `ChatSessionPanel.tsx` 마운트 직후 메시지 | 첫 미답변 질문 1개만 표시 | history 메시지 → 미답변 질문 순으로 채팅 히스토리 전체 복원 |
| 5번째 답변 후 화면 | `thinking=true` + 일반 "Thinking..." 말풍선 | "당신의 일기를 만들고 있어요..." 명시적 로딩 UI (스피너 포함) |
| 모달 닫기 (진행 중) | 안내 없이 단순 닫힘 | 진행도 1~4면 1회성 토스트 안내, 0이면 안내 없음 |
| 네트워크/5xx 에러 | "오류가 발생했습니다" 정적 메시지 | 에러 메시지 + "재시도" 버튼 (마지막 액션 재실행) |
| `ChatSessionModal.tsx` 닫기 동작 | `onClose` 직접 호출 | 조기 종료 가드를 통해 안내 1회 후 `onClose` |

### 2.2 백엔드 변경 — `/qna/start` 응답 확장

기존 `QnAStartResponse`:
```python
class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int
```

확장:
```python
class QnAHistoryItem(BaseModel):
    sequence: int
    question: str
    answer: str  # 답변된 항목만

class QnAStartResponse(BaseModel):
    session_id: int
    question: str
    sequence: int
    history: list[QnAHistoryItem] = []
```

- `start_qna` 라우터: 신규 세션 생성 시 `history=[]`, `_resume_session` 시 `history`에 `answer is not None`인 QnAItem을 `sequence` 오름차순으로 채워 반환.
- 후방 호환: 클라이언트가 `history`를 무시해도 동작은 동일 (기본 `[]`).

### 2.3 프론트엔드 변경 — `ChatSessionPanel.tsx`

#### 2.3.1 마운트 시 히스토리 복원

```ts
client.post('/qna/start', { diary_date: date }).then((resp) => {
  const { session_id, question, sequence, history = [] } = resp.data
  const historyMessages: Message[] = history.flatMap((h) => ([
    { role: 'ai', text: h.question, seq: h.sequence },
    { role: 'user', text: h.answer },
  ]))
  setMessages([...historyMessages, { role: 'ai', text: question, seq: sequence }])
  setQnaState({ sessionId: session_id, sequence })
})
```

- 백엔드 DB의 `qna_sessions` + `qna_items`가 진실의 원천. `diary_date` 기준 selectinload로 이미 메모리에 올라와 있으므로 추가 DB 호출 0회로 history 응답 가능.
- 기존 localStorage(`qna:{date}`) 저장 로직은 **완전 제거**한다. 현재 코드는 저장만 하고 읽지 않는 dead code이며, 백엔드 history 도입 후엔 더더욱 불필요. 캐시 일관성 문제도 사라진다.
- 사용자가 이미 답변을 보낸 상태에서 새로고침/재진입 → 같은 날짜 모달 클릭 → 이전 대화 그대로 보이고 마지막 미답변 질문에 답변 입력 가능.

#### 2.3.2 일기 생성 로딩 상태 분리

기존 `thinking: boolean` 1개 상태 → `phase: 'idle' | 'thinking' | 'finalizing'` 로 확장.

- `phase='thinking'`: 다음 질문 생성 대기 (기존 동작)
- `phase='finalizing'`: 5번째 답변 전송 직후 ~ `completed=true` 응답 도착 전.
- `finalizing` 동안 채팅 영역 위에 큰 박스로 "✨ 당신의 일기를 만들고 있어요" + 회전 스피너(`@keyframes` CSS) 표시.
- `finalizing` 동안 textarea/전송 버튼은 disabled 유지 + 입력값 클리어, **모달 닫기 버튼도 disabled** 처리 (백엔드 일기 생성은 진행되지만 프론트에서 결과를 못 받으면 다음 진입 시 409로 빠짐 → 사용자 혼란 방지). 닫기 버튼 hover/disabled 상태에서 "거의 다 됐어요, 잠시만 기다려주세요" 툴팁 노출.

```tsx
{phase === 'finalizing' && (
  <div role="status" aria-live="polite" className="diary-finalizing">
    <Spinner />
    <p>✨ 당신의 일기를 만들고 있어요...</p>
    <small>10초 이상 걸릴 수 있어요</small>
  </div>
)}
```

#### 2.3.3 에러 재시도

`error` 단일 상태 → `error: { message: string, retry: (() => void) | null } | null` 로 구조 변경.

- 다음 질문 생성 실패: `retry`는 마지막 답변 재전송.
- `/qna/start` 실패 (네트워크): `retry`는 start 재시도.
- 409: `retry=null` (재시도 불가).

```tsx
{error && (
  <div role="alert">
    <p>{error.message}</p>
    {error.retry && <button onClick={error.retry}>재시도</button>}
  </div>
)}
```

### 2.4 모달 닫기 가드 — `ChatSessionModal.tsx`

- 추가 props: `progress?: number` (0~5, 현재 답변 완료 수).
- `Modal`의 `onClose`를 직접 노출하지 않고 래퍼에서 가로채기:
  - `progress === 0` → 즉시 닫기.
  - `progress >= 1 && !shownNotice` → 한 번만 안내 토스트(작은 div) 1.5초 노출 후 자동 닫힘.
  - `shownNotice` 상태는 같은 모달 인스턴스 내에서 1회만 표시.
- 안내 문구: `진행 상황은 저장됐어요. 같은 날짜를 다시 클릭하면 이어서 할 수 있어요.`
- `confirm()` 다이얼로그는 사용하지 않음 (Task-3의 DiaryDetailModal과 동일하게 `window.confirm`을 쓰지 않고, 토스트로 일관).

> ChatSessionPanel이 부모(ChatSessionModal)에 `progress` 변화를 알리려면 새 콜백이 필요. 옵션:
> - (A) `onProgressChange?: (n: number) => void` 콜백 prop 추가. 부모가 state로 보관.
> - (B) `progress`를 외부에서 주입 (불가능 — 답변 완료 수는 Panel 내부에서 계산).
> **채택: (A)**.

### 2.5 백엔드 회귀 영향

- `QnAStartResponse`에 필드 추가 — 기존 응답 필드는 그대로. 기존 테스트 영향 없음.
- 기존 `tests/integration/test_qna.py`의 응답 assertion이 `response.json() == {...}` 형태로 strict 비교 시 깨질 가능성 있음. 확인 필요.

### 2.6 프론트엔드 회귀 영향

- `ChatSessionPanel.test.tsx`의 3 케이스 모두 단일 thinking/error 가정 → 새 구조에 맞춰 갱신.
- 기존 핸들러(`handlers.ts`)의 `/qna/start` 응답은 `history` 없음 → 옵셔널이므로 OK. 신규 케이스에서만 `server.use(...)`로 history 포함 응답 오버라이드.

### 2.7 디렉토리 변경 요약

```
backend/app/
├── schemas.py                ← QnAHistoryItem 추가, QnAStartResponse 확장
└── routers/qna.py            ← _resume_session + start_qna에서 history 빌드

frontend/src/
├── components/
│   ├── ChatSessionPanel.tsx  ← phase 상태, history 복원, retry, onProgressChange
│   ├── ChatSessionModal.tsx  ← progress prop + 닫기 안내 토스트
│   └── Spinner.tsx           ← 신설 (재사용 가능한 회전 스피너)
└── lib/
    └── (변경 없음)
```

### 2.8 백워드 호환성

- 백엔드: `history` 필드는 옵셔널 (기본 `[]`), 기존 클라이언트 영향 없음.
- 프론트엔드: `ChatSessionPanel`의 props 시그니처에 `onProgressChange?` 옵셔널 추가 → 기존 테스트의 직접 렌더(`onProgressChange` 없이)는 그대로 동작.
- localStorage `qna:{date}` 저장 로직은 **제거**. 기존에 저장된 키가 남아 있더라도 누구도 읽지 않으므로 무해 (필요 시 별도 마이그레이션 없음).

---

## 3. Open Questions

다음 항목은 코드 작성 전 사용자 확인 필요. **기본 답안**으로 진행하되, 변경 요청 시 본 문서 수정 후 재시작.

| # | 항목 | 기본 답안 | 대안 |
| --- | --- | --- | --- |
| 1 | history 응답 위치 | **`POST /qna/start` 응답에 포함** | 별도 `GET /qna/{date}` 신설 |
| 2 | 일기 생성 로딩 UI 디자인 | **중앙 박스 + 스피너 + 안내 문구 1줄 + "10초 이상 걸릴 수 있어요" 부가 텍스트** | 채팅 영역에 AI "일기를 만들고 있어요..." 말풍선 1개 |
| 3 | 모달 닫기 안내 방식 | **인라인 토스트 1.5초 자동 사라짐** | `window.confirm()` 또는 별도 확인 모달 |
| 4 | 닫기 안내 표시 조건 | **`progress >= 1`일 때만 1회** | 항상 표시 / 표시 안 함 |
| 5 | 에러 재시도 버튼 | **마지막 액션 재실행** (start 또는 answer) | "다시 시작하기" (세션 초기화) |
| 6 | localStorage `qna:{date}` 처리 | **완전 제거** (백엔드 history가 진실의 원천, 현재 dead code) | 유지 |
| 7 | finalizing 상태에서 textarea 상태 | **disabled 유지 + 입력값 클리어** | 입력창 자체를 숨김 |
| 8 | 일기 생성 타임아웃 처리 | **이번 Task 미포함** (Bedrock SDK 기본 타임아웃에 위임) | 30초 후 클라이언트 abort + 에러 화면 |
| 9 | 진행률 바 표시 기준 | **현재 코드 유지 — "다음 답할 질문 번호 / 5"** (예: 답변 2개 후 재진입 시 `3 / 5`) | "답변 완료 수 / 5" (Days.md spec) |
| 10 | finalizing 중 모달 닫기 | **닫기 버튼 disabled + "거의 다 됐어요" 안내** | 닫기 허용 + 백그라운드 완료 |

---

## 4. Approach (구현 전략)

1. **백엔드 먼저**: `QnAStartResponse`에 `history` 필드 추가 → 기존 테스트 회귀 확인 → history 케이스 1개 추가.
2. **프론트엔드 공용 부품**: `Spinner.tsx` 신설 (이후 단계에서 재사용).
3. **ChatSessionPanel 단계적 보강**: history 복원 → phase 상태 분리 → retry → onProgressChange 순서.
4. **ChatSessionModal 닫기 가드**: progress prop + 토스트 추가.
5. **테스트 마이그레이션 마지막**: 기존 3 케이스 갱신 + 신규 2 케이스 (history 복원, 5번째 finalizing).
6. **한 todo 당 1 커밋 원칙**(Task-3/4와 동일). Verify 명령 통과 후에만 다음 todo로 진행.
7. **Bedrock/RAG 로직은 건드리지 않음** — 본 Task는 응답 스키마 1개 확장 + UI 보강만.

---

## 5. Todo List

### Phase 1 — 백엔드 history 응답 확장

- [x] **1.1** `backend/app/schemas.py`에 `QnAHistoryItem` 추가, `QnAStartResponse.history` 필드 추가 — `QnAHistoryItem` 및 `history: list[QnAHistoryItem] = []` 추가 완료, import 확인
  - `QnAHistoryItem(BaseModel)`: `sequence: int`, `question: str`, `answer: str`.
  - `QnAStartResponse.history: list[QnAHistoryItem] = Field(default_factory=list)`.
  - Verify: `python -c "from app.schemas import QnAStartResponse; QnAStartResponse(session_id=1, question='q', sequence=1)"` 에러 없음.

- [x] **1.2** `backend/app/routers/qna.py`의 `start_qna` / `_resume_session` 갱신 — resume 시 answered items를 QnAHistoryItem으로 빌드, 신규 세션은 history=[] 기본값. 기존 6 테스트 모두 통과
  - 신규 세션 생성 경로: `history=[]` (기본값).
  - resume 경로: `existing.items` 중 `answer is not None`인 항목을 `sequence` 오름차순 정렬해 `QnAHistoryItem` 리스트로 매핑.
  - Verify: 기존 `tests/integration/test_qna.py` 회귀 0 fail (`pytest tests/integration/test_qna.py -v`).

- [x] **1.3** `tests/integration/test_qna.py`에 history 복원 케이스 1개 추가 — `test_start_returns_history_on_resume` 추가, 백엔드 전체 35 passed
  - 시나리오: start → 1번 answer → start 재호출 → 응답의 `history`가 1개(seq=1) 포함되고 `sequence`는 2를 가리킴.
  - Verify: 새 케이스 1 passed, 백엔드 전체 회귀 `pytest -v --tb=short` → **35 passed** (34 + 1).

### Phase 2 — 프론트엔드 공용 부품

- [x] **2.1** `frontend/src/components/Spinner.tsx` 신설 — SVG 회전 스피너, size/color props, 빌드 통과
  - 24px 정도의 회전 원형 스피너. `@keyframes spin` 인라인 정의.
  - props: `size?: number` (기본 24), `color?: string` (기본 `#4f46e5`).
  - Verify: `npm run build` 통과.

### Phase 3 — ChatSessionPanel 보강

- [x] **3.1** `ChatSessionPanel.tsx`에 history 응답 처리 추가 — history flatMap으로 기존 Q/A 메시지 prepend, 빈 history는 기존 동작과 동일. 빌드 통과
  - `/qna/start` 응답에서 `history` 읽어 messages 초기 상태에 prepend.
  - 빈 `history`는 기존 동작과 동일.
  - Verify: `npm run build` 통과.

- [x] **3.2** `phase` 상태로 thinking / finalizing 분리 — thinking 제거, phase: 'idle'|'thinking'|'finalizing' 도입, finalizing 중 Spinner+안내 박스 표시, textarea/전송 비활성화. 빌드 통과
  - `phase: 'idle' | 'thinking' | 'finalizing'` 도입, 기존 `thinking` 제거.
  - 5번째 답변 제출 시 `phase='finalizing'` → `completed=true` 응답 후 `phase='idle'`.
  - finalizing 동안: textarea/전송 disabled + 입력값 클리어, "Thinking..." 말풍선 대신 중앙 박스 + Spinner.
  - Verify: `npm run build` 통과.

- [x] **3.5** localStorage `qna:{date}` 저장 로직 완전 제거 — ChatSessionPanel.tsx에서 handleAnswer 재작성(3.2) 시 함께 제거. grep 결과 0건 확인. QnA.tsx는 App.tsx에서 미사용 dead code
  - `ChatSessionPanel.tsx:110-114`의 `localStorage.setItem(...)` 블록 삭제.
  - 백엔드 history가 진실의 원천이므로 클라이언트 캐시 불필요.
  - Verify: `npm run build` 통과 + `grep -r "qna:" frontend/src` 결과 0건.

- [x] **3.3** 에러 상태를 `{message, retry}` 구조로 확장 + 재시도 버튼 — ErrorState 인터페이스, submitAnswer 헬퍼로 retry closure 캡처, 409는 retry=null. 빌드 통과
  - `error: { message: string, retry: (() => void | Promise<void>) | null } | null`.
  - `/qna/start` 실패 시 retry는 start 재호출.
  - `/qna/answer` 실패 시 retry는 마지막 answer 재전송.
  - 409는 `retry=null`.
  - Verify: `npm run build` 통과.

- [x] **3.4** `onProgressChange?: (n: number) => void`, `onFinalizingChange?: (b: boolean) => void` 옵셔널 prop 추가 — submitAnswer에서 콜백 호출, 기존 호출자 영향 없음. 빌드 통과
  - 답변 완료 시마다 `onProgressChange(answeredCount)` 호출.
  - `phase === 'finalizing'` 진입/이탈 시 `onFinalizingChange(true/false)` 호출.
  - 둘 다 옵셔널이므로 기존 호출자 영향 없음.
  - Verify: `npm run build` 통과.

### Phase 4 — ChatSessionModal 닫기 가드

- [x] **4.1** `ChatSessionModal.tsx`에 progress 추적 + 토스트 안내 추가 — finalizing 중 닫기 차단+안내, progress>=1 첫 닫기 1.5초 토스트 후 onClose, ESC/백드롭도 동일 가드. 빌드 통과
  - 내부 state: `progress: number` (기본 0), `noticeShown: boolean`, `finalizing: boolean` (Panel에서 콜백으로 받음).
  - `<ChatSessionPanel onProgressChange={setProgress} onFinalizingChange={setFinalizing} />`.
  - 닫기 요청 시:
    - `finalizing === true` → **닫기 무시 + "거의 다 됐어요, 잠시만 기다려주세요" 툴팁/안내**.
    - `progress >= 1 && !noticeShown` → 토스트 1.5초 노출 후 `onClose()`.
    - 그 외 → 즉시 `onClose()`.
  - 토스트는 모달 내부 상단에 absolute로 표시.
  - Modal의 백드롭 클릭 / ESC 키도 동일한 가드를 거치도록 처리.
  - Verify: `npm run build` 통과 + 수동 확인 (Phase 6.4).

### Phase 5 — 테스트 갱신 및 신설

- [x] **5.1** `frontend/tests/handlers.ts`에 history 핸들러 베이스 갱신 — /qna/start 응답에 history:[] 추가, 기존 18 passed 회귀 없음
  - 기본 `/qna/start` 응답에 `history: []` 추가 (안전한 디폴트).
  - Verify: 기존 테스트 회귀 0 fail.

- [x] **5.2** `frontend/tests/ChatSessionPanel.test.tsx` 갱신 (기존 3 케이스 유지 + 2 추가) — history 복원, finalizing UI 케이스 추가. 5 passed
  - 기존 케이스 갱신: phase/error 구조 변경에 맞춰 셀렉터 조정.
  - (신규 a) `history` 응답 시 이전 Q/A가 화면에 표시되고 마지막 미답변 질문에 답변 가능.
  - (신규 b) 5번째 답변 전송 시 "당신의 일기를 만들고 있어요" 로딩 UI 노출 → `completed=true` 응답 후 사라지고 `onComplete` 호출.
  - Verify: ChatSessionPanel 테스트 5 passed.

- [ ] **5.3** `frontend/tests/ChatSessionModal.test.tsx` 신설 (3 케이스)
  - (a) `progress=0`에서 닫기 클릭 → 토스트 미노출 + `onClose` 즉시 호출.
  - (b) `progress=2`에서 닫기 클릭 → 토스트 노출 + 1.5초 후 `onClose` 호출.
  - (c) `finalizing=true`에서 닫기 클릭 → `onClose` 호출되지 않음 + "거의 다 됐어요" 안내 표시.
  - Verify: 3 passed.

- [ ] **5.4** 프론트엔드 전체 회귀
  - 실행: `cd frontend && npm test -- --run && npm run build`
  - 누적 테스트: 4(Login) + 3(Home) + 5(ChatSessionPanel) + 2(DiaryDetailModal) + 3(Onboarding) + 3(Profile) + 3(ChatSessionModal) = **23 passed** (실제 기존 카운트는 `npm test` 한 번 돌려 검증).
  - 빌드 번들 크기 ±10% 이내 확인.

### Phase 6 — 수동 통합 검증

- [ ] **6.1** 백엔드 + 프론트 동시 기동 후 수동 E2E
  - 실행: `make db && make migrate && make backend` + `make frontend`.
  - 시나리오:
    1. 로그인 + 온보딩 완료 상태에서 일기 없는 날짜 클릭 → ChatSessionModal 열림 → 1번 질문 표시.
    2. 2개 질문에 답변 후 모달 닫기 → "진행 상황은 저장됐어요..." 토스트 1.5초 → 모달 닫힘.
    3. 같은 날짜 다시 클릭 → 이전 2개 Q/A가 화면에 그대로 표시 + 3번 질문이 마지막에 표시.
    4. 5번째 답변 전송 → "당신의 일기를 만들고 있어요..." 로딩 UI 1~3초 → 자동 닫힘 → 캘린더에 이모티콘 + DiaryDetailModal 자동 열림.
    5. (개발자 도구) `/qna/answer` 응답을 강제로 500 만들어 답변 제출 → 에러 + "재시도" 버튼 → 클릭 시 동일 답변 재전송 → 성공.
    6. 답변 0개인 상태에서 모달 닫기 → 토스트 없이 즉시 닫힘.
    7. 5번째 답변 전송 직후 finalizing 상태에서 닫기 버튼 클릭 → 닫히지 않음 + "거의 다 됐어요, 잠시만 기다려주세요" 안내 노출 → 1~3초 후 일기 생성 완료 → DiaryDetailModal 자동 전환.
    8. 로컬스토리지 확인: 답변 1~2개 후 DevTools Application 탭에서 `qna:{date}` 키가 **생성되지 않음** 확인.
  - Verify: 8개 시나리오 모두 동작 + 콘솔 에러 0건.

---

## 6. Test Plan

### 6.1 신규/갱신 단위·통합 테스트

| Test | Input | Expected |
| --- | --- | --- |
| `test_qna.test_start_returns_history_on_resume` | start → answer seq=1 → start 재호출 | 응답 `history`에 seq=1 항목 1개, `sequence==2` |
| `ChatSessionPanel.test_first_question` (갱신) | mount + history=[] | 1번 질문 표시 |
| `ChatSessionPanel.test_5_cycle_invokes_oncomplete` (갱신) | 5회 답변 | finalizing UI 노출 후 `onComplete(diary)` 호출 |
| `ChatSessionPanel.test_409_disabled` (갱신) | start 409 | 입력창 disabled + retry 버튼 없음 |
| `ChatSessionPanel.test_history_restores_messages` | start with history=[{1,q1,a1},{2,q2,a2}] | 화면에 q1, a1, q2, a2, 그리고 3번 질문 순서로 표시 |
| `ChatSessionPanel.test_finalizing_ui_during_5th_answer` | 5번째 답변 제출 직후 | "당신의 일기를 만들고 있어요" 노출 + textarea disabled |
| `ChatSessionModal.test_close_without_progress` | progress=0 + 닫기 | 토스트 미노출 + `onClose` 즉시 호출 |
| `ChatSessionModal.test_close_with_progress_shows_toast` | progress=2 + 닫기 | 토스트 노출 + 1.5초 후 `onClose` 호출 |
| `ChatSessionModal.test_close_blocked_during_finalizing` | finalizing=true + 닫기 | `onClose` 미호출 + "거의 다 됐어요" 안내 표시 |

### 6.2 통합 시나리오 (수동 E2E, Phase 6.1)

| Scenario | Final state |
| --- | --- |
| 2번 답변 후 모달 닫고 재진입 | 이전 Q/A 그대로 + 3번 질문에 답변 입력 가능 |
| 5번째 답변 전송 직후 | 로딩 UI 1~3초 → 모달 자동 닫힘 → DiaryDetailModal 표시 |
| 진행 중 닫기 | 토스트 1.5초 후 자동 닫힘 |
| 답변 0개 상태로 닫기 | 즉시 닫힘 (토스트 없음) |
| `/qna/answer` 5xx 응답 | 에러 + 재시도 버튼 → 재시도 성공 |
| 409 (완료된 날짜) | 입력창 비활성 + 재시도 버튼 없음 |

### 6.3 회귀 보장

- 백엔드 기존 34개 → **35 passed** (1개 추가) — 실제 기존 수는 `pytest -v --collect-only` 결과로 검증.
- 프론트 기존 18개 → **23 passed** (ChatSessionPanel 3→5, ChatSessionModal +3) — 실제 기존 수도 동일 방식 검증.
- `npm run build` 빌드 성공 유지

### 6.4 자동화 명령

```bash
# 백엔드
cd 2026-cloud-computing-days/backend && .venv/bin/pytest -v --tb=short

# 프론트
cd 2026-cloud-computing-days/frontend && npm test -- --run && npm run build

# 로컬 통합
make db && make migrate && make backend   # 터미널 1
make frontend                              # 터미널 2
```

---

## 7. Resume Protocol

Task-3/4와 동일한 5단계 원칙. 추가로:

- **Phase 1 백엔드 변경 도중 중단**: 응답 스키마가 깨지면 모든 QnA 테스트가 깨짐. 재개 시 `pytest tests/integration/test_qna.py -v` 먼저 → 통과 후 다음 단계.
- **Phase 3 ChatSessionPanel 단계적 보강**: 3.1~3.4를 순서대로 진행. 중간에 멈췄다면 `npm test -- --run tests/ChatSessionPanel.test.tsx`로 어느 단계까지 갔는지 확인.
- **Phase 4 모달 닫기 가드 도중 중단**: `onProgressChange` 콜백이 양방향으로 연결됐는지 확인. 깨졌으면 토스트가 절대 표시되지 않거나 항상 표시됨.
- **백엔드 변경 외 다른 백엔드 코드는 손대지 않음**: Bedrock, diary 라우터, 마이그레이션 모두 변경 금지. 변경 시 즉시 중단하고 원복.

---

## 8. Hand-off

Task-1.md 작성 완료. **8개 Open Questions의 기본 답안에 동의하는지** 또는 변경할지 알려주세요. 변경 사항이 있으면 본 문서를 먼저 수정 후 코드 작업을 시작합니다. **승인 전까지 코드는 절대 수정하지 않습니다.**