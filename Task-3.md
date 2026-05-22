# Task-3: Home 캘린더 메인 화면 + 감정 이모티콘 + 일기 조회/편집 모달

> **상태**: 작성 완료, 사용자 승인 대기 중
> **인코딩**: UTF-8 (BOM 없음)
> **작성일**: 2026-05-22
> **선행 조건**: Task-1 (Phase 0~6) + Task-2 (백엔드 31개 / 프론트 10개 테스트 통과) 완료
> **후속 작업**: Task-4 (온보딩 + 프로필 화면), Task-5 (채팅 세션 UI 마무리), Task-6 (AWS 실배포)

---

## 1. Goal (목적)

Days.md PRD v2.0의 **Screen 3 (홈 캘린더)** + **Screen 5 (일기 조회/편집)** + **Screen 6 (AI 채팅 세션)**의 사용자 진입 경로를 모두 구현한다.

- **홈은 캘린더가 메인**: 로그인 후 첫 화면이 월간 캘린더이고, 각 날짜 칸에 감정 이모티콘이 표시된다.
- **날짜 클릭 분기**: 일기가 있는 날 → 조회/편집 모달, 없는 날 → AI 채팅 세션 모달.
- **인라인 편집**: 일기 조회 모달에서 감정 이모티콘과 본문 텍스트를 직접 수정·저장.

본 Task는 **프론트엔드 화면 재편**이 중심이며, 일기 본문 편집을 위해 **백엔드 API 1개를 추가**(`PATCH /api/diary/{date}/body`)한다. 프로필/온보딩 화면은 Task-4, 채팅 세션 로딩 UI 등 미세 보완은 Task-5에서 처리한다.

---

## 2. Context (사전 조사 결과)

### 2.1 현재 프론트엔드 상태와 Task-3 후 차이

| 영역 | 현재 (Task-2 완료 시점) | Task-3 후 |
| --- | --- | --- |
| `/` 라우트 | `Navigate to="/qna"` | `Navigate to="/home"` (또는 직접 Home 렌더) |
| 홈 화면 | 없음 (사이드바 + QnA가 기본) | **`Home.tsx` 신설** — 캘린더 메인 |
| 사이드바 | `Sidebar.tsx` 좌측 상시 표시 (QnA/캘린더/프로필) | **제거**. 헤더에 프로필 칸 + 환경설정 아이콘만 |
| `/qna` 페이지 | 별도 페이지 (`QnA.tsx`) | `QnA.tsx` 컴포넌트는 유지하되 **Home의 채팅 모달로 임베드** |
| `/calendar` 페이지 | 별도 페이지 (`CalendarPage.tsx`) | Home에 흡수, 기존 페이지 제거 |
| `/diary/:date` 페이지 | 별도 페이지 (`DiaryView.tsx`) | Home의 **조회 모달**로 전환, 기존 페이지 제거 |
| 감정 이모티콘 렌더링 | 없음 (`// TODO Task-3` 주석) | 날짜 칸에 5종 이모티콘 표시 |
| 일기 본문 편집 | 없음 (조회만 가능) | 모달 내 인라인 에디터 + `PATCH /api/diary/{date}/body` |
| 감정 편집 | 백엔드 API만 있음 (`PATCH /api/diary/{date}/emotion`) | 모달 내 5종 선택 UI에서 호출 |

### 2.2 라우팅 구조 결정

PRD의 6개 화면 중 Task-3 범위인 Screen 3/5/6은 **모두 Home의 일부**로 묶는다. 모달은 라우팅 없이 React 상태(`useState`)로 관리한다 — URL 공유는 본 단계에서 요구사항 아님.

```
이전 (Task-2):                       이후 (Task-3):
  /            → Navigate /qna         /          → Home (캘린더 메인)
  /qna         → QnA.tsx                /login     → Login
  /calendar    → CalendarPage.tsx      /profile   → Profile (Task-4에서 실제 폼)
  /diary/:date → DiaryView.tsx         (다른 라우트 모두 제거)
  /profile     → Profile.tsx (dummy)
  /login       → Login
```

- 사이드바는 완전 제거. Home 화면 헤더에 우측 상단 **프로필 아이콘**(클릭 시 `/profile`로 이동) 1개만 둔다. 환경설정 버튼은 Task-7로 이월 (미구현 placeholder 표시 X).
- `QnA.tsx`, `DiaryView.tsx`는 **삭제하지 않고** props 기반 컴포넌트로 리팩터링해 Home의 모달 내부에서 렌더링한다. 이렇게 하면 기존 테스트(`QnA.test.tsx`)를 큰 변경 없이 재활용 가능.

### 2.3 캘린더 감정 이모티콘 렌더링

- FullCalendar의 `eventContent` 콜백에서 `event.extendedProps.emotion`을 읽어 이모티콘 출력.
- 이모티콘 매핑:

| 백엔드 값 | 이모티콘 |
| --- | --- |
| `happy` | 😊 |
| `sad` | 😭 |
| `angry` | 😠 |
| `neutral` | 😐 |
| `bored` | 😩 |

- 매핑 테이블은 `frontend/src/lib/emotions.ts`에 상수로 분리해 모달의 5종 선택 UI에서도 재사용.
- 일기가 있는 날짜만 이모티콘 표시. 없는 날짜는 빈 칸(클릭 가능).
- 날짜 클릭 시:
  - `events`에 해당 날짜가 있으면 → 일기 조회 모달
  - 없으면 → 채팅 세션 모달

### 2.4 모달 UI 결정

- 라이브러리 추가 없음. `position: fixed` + overlay 패턴으로 직접 구현 (의존성 최소화).
- 닫기 동작: 우측 상단 X 버튼, ESC 키, 배경 클릭 모두 지원.
- 채팅 세션 모달은 **조기 종료 시 in_progress 세션 유지** — 닫기 클릭 → 안내문구 없이 단순 닫기 (Task-5에서 "이어서 하기" UX 보강 예정).
- 일기 조회 모달은 **편집 미저장 상태에서 닫기 시도 시 확인 다이얼로그** (단순 `confirm()` 사용).

### 2.5 일기 본문 편집 — 백엔드 API 추가

현재 백엔드는 본문 편집 API가 없다. 신설:

| 메서드 | 경로 | Body | 응답 |
| --- | --- | --- | --- |
| `PATCH` | `/api/diary/{date}/body` | `{ body: string }` (1자 이상, 5000자 이하) | `200 + {date, body, emotion}` (전체 갱신본) |

- 422: body 비었거나 5000자 초과
- 404: 해당 날짜에 일기 없음
- 401: 비인증
- 트랜잭션: `diary_entries.body` UPDATE, `updated_at` 컬럼은 추가하지 않음 (MVP).

> **참고**: 감정 PATCH(`/emotion`)는 이미 Task-2에서 구현됨. 본 Task에서는 본문용 별도 endpoint만 추가.

### 2.6 백워드 호환성 및 회귀

- **삭제되는 라우트**: `/qna`, `/calendar`, `/diary/:date`. 기존 e2e 시나리오가 이 URL을 직접 입력하는 경우는 없으므로 영향 없음.
- **유지되는 컴포넌트**: `QnA.tsx`, `DiaryView.tsx`는 모달 내부 컴포넌트로 props 인터페이스만 변경. 기존 `QnA.test.tsx` 4개 케이스는 prop 기반으로 갱신.
- **`CalendarPage.tsx`는 삭제**, Home에서 동일 로직 흡수. 기존 `CalendarPage.test.tsx` 3개는 `Home.test.tsx`로 이전.

### 2.7 디렉토리 변경 요약

```
frontend/src/
├── pages/
│   ├── Home.tsx              ← 신설 (캘린더 + 모달 컨테이너)
│   ├── Login.tsx             (변경 없음)
│   └── Profile.tsx           (변경 없음, Task-4)
├── components/
│   ├── Modal.tsx             ← 신설 (공용 오버레이)
│   ├── DiaryDetailModal.tsx  ← 신설 (조회 + 감정/본문 편집)
│   ├── ChatSessionModal.tsx  ← 신설 (QnA 컴포넌트 임베드)
│   ├── EmotionPicker.tsx     ← 신설 (5종 선택 UI)
│   └── (Sidebar.tsx 제거)
├── lib/
│   └── emotions.ts           ← 신설 (이모티콘 매핑 상수)
└── (pages/CalendarPage.tsx, pages/DiaryView.tsx, pages/QnA.tsx는 → components/로 이동 또는 흡수)
```

- `QnA.tsx` → `components/ChatSessionPanel.tsx`로 이동 + 모달 임베드용 props 추가 (`date`, `onComplete`, `onClose`).
- `DiaryView.tsx` → `DiaryDetailModal.tsx`에 흡수 (별도 파일로 남기지 않음).

---

## 3. Open Questions

다음 항목은 코드 작성 전 사용자 확인 필요. **기본 답안**으로 진행하되, 변경 요청 시 본 문서 수정 후 재시작.

| # | 항목 | 기본 답안 | 대안 |
| --- | --- | --- | --- |
| 1 | 사이드바 처리 | **완전 제거**. 헤더 우측 상단 프로필 아이콘만. | 헤더 좌측에 햄버거 메뉴로 축소 유지 |
| 2 | 일기 본문 편집 API 메서드 | **`PATCH /api/diary/{date}/body`** (감정 PATCH와 일관) | `PUT` (전체 교체 시맨틱) |
| 3 | 모달 닫기 단축키 | **ESC + 배경 클릭 + X 버튼** 모두 지원 | X 버튼만 |
| 4 | 편집 중 모달 닫기 시 확인 | **`confirm()` 다이얼로그** (단순) | 무시하고 닫기 / 별도 confirm 모달 |
| 5 | URL 공유용 모달 라우팅 (`/?date=...`) | **하지 않음** (단순 useState) | query param 동기화 |
| 6 | 환경설정 / 알림 버튼 | **이번 Task 미포함** (Task-7로 이월) | placeholder 노출 |

---

## 4. Approach (구현 전략)

1. **백엔드 먼저**: API 1개(`PATCH /api/diary/{date}/body`) 추가 + 테스트. Task-2의 emotion PATCH 패턴을 그대로 답습해 5분 내 완료 가능.
2. **공용 컴포넌트부터**: `Modal.tsx`, `EmotionPicker.tsx`, `lib/emotions.ts` 같은 재사용 부품을 먼저 만들고 Home/DetailModal/ChatModal이 조립.
3. **Home → DiaryDetail → ChatSession 순**으로 페이지 구현. 각 단계마다 빌드 + 기존 테스트 회귀 확인.
4. **테스트 마이그레이션은 마지막**: 기존 `QnA.test.tsx`/`CalendarPage.test.tsx`를 Home/Modal 구조에 맞춰 갱신. 새 모달용 테스트 1~2개 추가.
5. **한 todo 당 1 커밋 원칙**(Task-1/2와 동일). Verify 명령 통과 후에만 다음 todo로 진행.
6. **Bedrock/RAG 로직은 건드리지 않음** — 본 Task는 UI 재편 + 본문 편집 API만.

---

## 5. Todo List

### Phase 1 — 백엔드 일기 본문 편집 API

- [ ] **1.1** `backend/app/schemas.py`에 `DiaryBodyUpdate` 스키마 추가
  - 필드: `body: str = Field(..., min_length=1, max_length=5000)`.
  - Verify: `python -c "from app.schemas import DiaryBodyUpdate; DiaryBodyUpdate(body='x')"` 에러 없음.

- [ ] **1.2** `backend/app/routers/diary.py`에 `PATCH /{diary_date}/body` 추가
  - 응답: `DiaryResponse` (기존 GET과 동일 — date, body, emotion).
  - 404: 일기 없음, 422: body 검증 실패.
  - Verify: `pytest tests/integration -k "diary or emotion" -v` 기존 회귀 0 fail.

- [ ] **1.3** `tests/integration/test_diary_body_edit.py` 신설
  - 케이스 3개:
    - (a) 정상 편집 → 200 + 재조회 시 새 body 반환
    - (b) 일기 없는 날짜 → 404
    - (c) 빈 body → 422
  - Verify: 3 passed, 백엔드 전체 회귀 `pytest -v --tb=short` → **34 passed** (31 + 3).

### Phase 2 — 프론트엔드 공용 부품 신설

- [ ] **2.1** `frontend/src/lib/emotions.ts` 작성
  - `EMOTION_KEYS = ['happy','sad','angry','neutral','bored'] as const`
  - `EMOTION_EMOJI: Record<EmotionKey, string>` 매핑.
  - `EMOTION_LABEL: Record<EmotionKey, string>` 한국어 라벨.
  - Verify: `npm run build` 통과.

- [ ] **2.2** `frontend/src/components/Modal.tsx` 신설
  - props: `open`, `onClose`, `children`. ESC 키 + 배경 클릭 + X 버튼으로 닫기.
  - 포커스 트랩 없음 (MVP), `role="dialog"` + `aria-modal="true"` 부여.
  - Verify: `npm run build` 통과.

- [ ] **2.3** `frontend/src/components/EmotionPicker.tsx` 신설
  - props: `value: EmotionKey`, `onChange: (v: EmotionKey) => void`.
  - 5종 이모티콘 가로 배치 + 선택된 항목 강조 스타일.
  - Verify: `npm run build` 통과.

### Phase 3 — Home 컴포넌트 (캘린더 메인)

- [ ] **3.1** `frontend/src/pages/Home.tsx` 신설 — 캘린더 + 모달 상태 관리
  - `GET /api/calendar` 호출 → `entries: [{date, emotion}]` 보관.
  - FullCalendar `eventContent`: 감정 이모티콘 1개를 큰 폰트로 렌더 (배경 버튼 제거).
  - 날짜 클릭 시: 해당 날짜가 entries에 있으면 `selectedDiaryDate` 상태 → DiaryDetailModal 열기, 없으면 `selectedNewDate` 상태 → ChatSessionModal 열기.
  - 헤더: 좌측 "Days" 로고, 우측 상단 프로필 아이콘 (Link to `/profile`).
  - Verify: `npm run build` 통과 + 수동 확인 (Phase 6.1).

- [ ] **3.2** `frontend/src/App.tsx` 라우팅 재편
  - `/` → `<Home />`, `/login`, `/profile`만 유지. `/qna`, `/calendar`, `/diary/:date` 제거.
  - `Layout`에서 `Sidebar` import 및 사용 제거. `<Layout>` 자체를 제거하고 페이지가 직접 헤더를 그리는 구조로 단순화.
  - Verify: `npm run build` 통과.

- [ ] **3.3** `frontend/src/components/Sidebar.tsx`, `frontend/src/pages/CalendarPage.tsx` 삭제
  - 더 이상 참조되지 않음을 grep으로 확인.
  - Verify: `grep -r "Sidebar\|CalendarPage" frontend/src` → 매치 0건.

### Phase 4 — 일기 조회/편집 모달

- [ ] **4.1** `frontend/src/components/DiaryDetailModal.tsx` 신설
  - props: `date: string`, `onClose: () => void`, `onUpdated: () => void` (Home이 캘린더 새로고침).
  - 마운트 시 `GET /api/diary/{date}` → `{body, emotion}` 로드.
  - 영역 2개:
    - **감정 영역**: 이모티콘 클릭 → `EmotionPicker` 인라인 표시 → 선택 시 `PATCH /api/diary/{date}/emotion` 호출 → 성공 시 상태 갱신.
    - **본문 영역**: 텍스트 클릭 → `<textarea>` 모드 전환 → "저장" 버튼 클릭 시 `PATCH /api/diary/{date}/body` 호출.
  - 본문 편집 미저장 상태에서 닫기 시도 → `window.confirm("저장하지 않은 변경사항이 있습니다. 닫으시겠어요?")`.
  - Verify: `npm run build` 통과 + 수동 확인 (Phase 6.2).

- [ ] **4.2** `frontend/src/pages/DiaryView.tsx` 삭제
  - DiaryDetailModal에 기능 흡수 완료.
  - Verify: `grep -r "DiaryView" frontend/src` → 매치 0건.

### Phase 5 — 채팅 세션 모달

- [ ] **5.1** `frontend/src/pages/QnA.tsx` → `frontend/src/components/ChatSessionPanel.tsx` 이동 + props화
  - props: `date: string`, `onComplete: (diaryBody: string) => void`, `onClose: () => void`.
  - 기존 내부 `date` state를 props로 대체. "날짜 선택" 폼 제거 (모달이 이미 날짜를 알고 진입).
  - 5번째 답변 완료 시 `onComplete` 호출 → 모달이 알아서 닫고 캘린더 새로고침.
  - Verify: 컴포넌트 단독 import + 빌드 통과.

- [ ] **5.2** `frontend/src/components/ChatSessionModal.tsx` 신설
  - 단순 래퍼: `<Modal>` + `<ChatSessionPanel>` + 닫기 시 단순 close (조기 종료 UX는 Task-5).
  - Home에서 `selectedNewDate`가 있을 때 표시.
  - Verify: 빌드 통과.

- [ ] **5.3** Home에서 ChatSessionModal `onComplete` 처리
  - 일기 생성 직후 캘린더 재조회 → 새 entry 표시 → 자동으로 DiaryDetailModal로 전환 (PRD: "일기 생성 완료 → 일기 조회 화면 전환").
  - Verify: 수동 시나리오 통과 (Phase 6.3).

### Phase 6 — 테스트 갱신 및 수동 통합 검증

- [ ] **6.1** `frontend/tests/QnA.test.tsx` → `ChatSessionPanel.test.tsx`로 갱신
  - props 기반 렌더로 변경 (`<ChatSessionPanel date="2026-05-11" ... />`).
  - "날짜 선택" 입력 케이스 제거 (모달에서는 이미 받음) → 4개 → 3개로 축소.
  - 5사이클 완료 시 `onComplete`가 일기 문자열로 호출됐는지 검증.
  - Verify: 갱신된 테스트 3 passed.

- [ ] **6.2** `frontend/tests/CalendarPage.test.tsx` → `Home.test.tsx`로 갱신
  - 케이스 3개:
    - (a) 캘린더 렌더링 확인 ("Days" 헤더 + `.fc` 존재)
    - (b) `/api/calendar` 호출 검증
    - (c) entries에 있는 날짜 클릭 → DiaryDetailModal 열림 (모달 내부 텍스트 확인)
  - Verify: 3 passed.

- [ ] **6.3** `frontend/tests/DiaryDetailModal.test.tsx` 신설
  - 케이스 2개:
    - (a) 마운트 시 GET diary 호출 → body/emotion 표시
    - (b) 감정 이모티콘 클릭 → EmotionPicker 노출 → 선택 시 PATCH 호출
  - Verify: 2 passed.

- [ ] **6.4** `frontend/tests/handlers.ts`에 `PATCH /api/diary/:date/body` 핸들러 추가
  - Verify: `npm test -- --run` 전체 패스. **총 테스트 수: 10 → 11** (Login 3 + Home 3 + ChatSessionPanel 3 + DiaryDetailModal 2).

- [ ] **6.5** 프론트엔드 전체 회귀
  - 실행: `cd frontend && npm test -- --run && npm run build`
  - Verify: 모두 exit 0, 빌드 번들 크기 변동 ±10% 이내 확인.

- [ ] **6.6** 백엔드 + 프론트 동시 기동 → 수동 E2E
  - 실행: `make db && make migrate && make backend` + `make frontend` (또는 빌드 후 `http://localhost:8000`).
  - 시나리오:
    1. 로그인 → Home 캘린더 표시 (Task-2에서 만든 일기 1건이 이모티콘으로 표시되는지 확인)
    2. 일기 없는 날짜 클릭 → ChatSession 모달 → 5문답 → 자동 닫힘 → 캘린더에 이모티콘 갱신
    3. 일기 있는 날짜 클릭 → DiaryDetail 모달 → 이모티콘 클릭하여 변경 → 캘린더 즉시 갱신
    4. 일기 있는 날짜 클릭 → 본문 클릭 → 텍스트 수정 → 저장 → 재조회 시 새 본문 확인
  - Verify: 4개 시나리오 모두 동작 + 콘솔 에러 0건.

---

## 6. Test Plan

### 6.1 신규/갱신 단위·통합 테스트

| Test | Input | Expected |
| --- | --- | --- |
| `test_diary_body_edit.test_patch_body_success` | PATCH body="new" | 200 + GET 시 body=="new" |
| `test_diary_body_edit.test_patch_body_404` | 없는 날짜 | 404 |
| `test_diary_body_edit.test_patch_body_validation` | body="" | 422 |
| `Home.test_render` | mount | "Days" 헤더 + `.fc` 존재 |
| `Home.test_calendar_api_call` | mount | `/calendar?month=...` 1회 호출 |
| `Home.test_date_with_diary_opens_modal` | entries 포함 날짜 클릭 | DiaryDetailModal 표시 |
| `ChatSessionPanel.test_first_question` | date prop 마운트 | 1번 질문 표시 |
| `ChatSessionPanel.test_5_cycle_invokes_oncomplete` | 5회 답변 | `onComplete(diary)` 호출 |
| `ChatSessionPanel.test_409_disabled` | start 409 | 입력창 비활성 + 안내 |
| `DiaryDetailModal.test_load_and_display` | date prop | GET 1회 + body/emoji 노출 |
| `DiaryDetailModal.test_change_emotion` | EmotionPicker 선택 | PATCH /emotion 호출 + 새 이모티콘 표시 |

### 6.2 통합 시나리오 (수동 E2E, Phase 6.6)

| Scenario | Final state |
| --- | --- |
| 로그인 후 / 진입 | Home 캘린더 표시, 좌측 사이드바 없음 |
| 일기 있는 날짜 클릭 | DiaryDetailModal 열림, 본문 + 이모티콘 표시 |
| 모달에서 이모티콘 변경 → 닫기 | 캘린더 칸 이모티콘 즉시 갱신 |
| 모달에서 본문 수정 → 저장 | 재조회 시 변경 반영, `confirm()` 다이얼로그 미발생 (이미 저장됨) |
| 일기 없는 날짜 클릭 | ChatSessionModal 열림, 1번째 질문 표시 |
| 채팅 5문답 완료 | 모달 자동 닫힘 → 캘린더에 이모티콘(neutral) 추가 |
| 본문 편집 중 X 클릭 | `confirm()` 호출, 취소 시 모달 유지 |

### 6.3 회귀 보장

- 백엔드 기존 31개 → **34 passed** (3개 추가)
- 프론트 기존 10개 → **11 passed** (구조 재편 후 Login 3 + Home 3 + ChatSessionPanel 3 + DiaryDetailModal 2)
- `npm run build` 빌드 성공 유지

### 6.4 자동화 명령

```bash
# 백엔드
cd 2026-cloud-computing-days/backend && .venv/bin/pytest -v --tb=short

# 프론트
cd 2026-cloud-computing-days/frontend && npm test -- --run && npm run build

# 로컬 통합
make db && make migrate && make backend   # 터미널 1
make frontend                              # 터미널 2 (또는 빌드 후 localhost:8000)
```

---

## 7. Resume Protocol

Task-1/2와 동일한 5단계 원칙. 추가로:

- **라우팅 재편 도중 중단(Phase 3.2)**: 기존 라우트 4개를 한 번에 정리하지 못한 채 빌드가 깨질 가능성 있음. 재개 시 `npm run build` 먼저 → 실패 시 App.tsx 라우트만 원복 후 다시 시작.
- **삭제 todo(3.3, 4.2) 도중 중단**: 파일을 지운 뒤 다른 곳에서 import가 남아 있으면 빌드 실패. 재개 시 `grep -r "<삭제대상>" frontend/src` 먼저 확인.
- **백엔드 API(1.x)와 프론트(4.x) 사이 의존**: Phase 1을 완전히 끝낸 후 Phase 4를 시작할 것. Phase 4 도중 백엔드 API에 문제 발견 시 Phase 1로 되돌아가 수정 후 재진입.

---

## 8. Hand-off

Task-3.md 작성 완료. **3 Open Questions의 기본 답안에 동의하는지** 또는 변경할지 알려주세요. 변경 사항이 있으면 본 문서를 먼저 수정 후 코드 작업을 시작합니다. **승인 전까지 코드는 절대 수정하지 않습니다.**
