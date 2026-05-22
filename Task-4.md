# Task-4: 온보딩 화면 + 프로필 설정 화면

> **상태**: 작성 완료, 사용자 승인 대기 중
> **인코딩**: UTF-8 (BOM 없음)
> **작성일**: 2026-05-22
> **선행 조건**: Task-1 ~ Task-3 완료 (백엔드 34 / 프론트 11 테스트 통과)
> **후속 작업**: Task-5 (채팅 세션 UI 마무리), Task-6 (AWS 실배포), Task-7 (선택)

---

## 1. Goal (목적)

Days.md PRD v2.0의 **Screen 2 (온보딩)** + **Screen 4 (프로필 설정)** + 로그인 후 분기 로직을 구현한다.

- **첫 로그인 분기**: 로그인 성공 → `GET /api/profile` 404 → `/onboarding` 강제 이동.
- **온보딩 화면**: 닉네임·성별·나이(필수) + 직업·취미·관심사·알림시간(선택) 입력 → `PUT /api/profile` → Home.
- **프로필 화면**: 기존 프로필 로드해 동일 항목 수정 + 로그아웃 + 뒤로가기.
- **ProtectedRoute 보강**: 프로필 미완성 상태로 `/`나 `/profile`을 직접 진입 시도하면 `/onboarding`으로 redirect.

본 Task는 **프론트엔드 전용** 작업이다. 백엔드 API(`GET /api/profile`, `PUT /api/profile`)는 Task-2에서 이미 완성됐고, 테스트 4개도 통과 중이므로 **백엔드 변경 없음**. 다만 한국어 라벨/태그 처리를 위해 프론트 측 매핑 유틸 하나가 추가된다.

---

## 2. Context (사전 조사 결과)

### 2.1 현재 상태와 Task-4 후 차이

| 영역 | 현재 (Task-3 완료 시점) | Task-4 후 |
| --- | --- | --- |
| `/onboarding` 라우트 | 없음 | **신설** — `Onboarding.tsx` |
| `Login.tsx` | 성공 시 `navigate('/qna')` (제거된 라우트) | 성공 시 프로필 체크 → `/onboarding` or `/` |
| `Profile.tsx` | dummy 폼 (`defaultValue="default-user"` + noop) | **실제 폼** — GET/PUT 연동 + 로그아웃 + 뒤로가기 |
| `ProtectedRoute.tsx` | `GET /me`만 검증 | 인증 OK + 프로필 미완성 → `/onboarding` redirect |
| `useAuth.ts` | `isAuthed` 상태만 보유 | 그대로 유지 (프로필 체크는 별도 훅 또는 ProtectedRoute 내부) |
| `Home.tsx` 헤더 | 프로필 아이콘 1개 (👤) | (선택) 닉네임 표시 추가 |

### 2.2 백엔드 현황 (변경 없음)

기존 `backend/app/routers/profile.py`에 이미 정의:

| 메서드 | 경로 | 동작 | 응답 |
| --- | --- | --- | --- |
| `GET` | `/api/profile` | 프로필 조회 | 200 `UserProfileOut` / 404 `Profile not found` / 401 |
| `PUT` | `/api/profile` | upsert | 200 `UserProfileOut` / 401 / 422(검증 실패) |

`UserProfileIn` 스키마:
- `nickname: str` (필수)
- `gender: str` (필수, pattern `^(male|female|other|private)$`)
- `age: int` (필수, 0 < age < 150)
- `occupation: Optional[str]`
- `hobbies: list[str]` (기본 `[]`)
- `interests: list[str]` (기본 `[]`)
- `notification_time: Optional[time]` (HH:MM:SS, null 허용)

기존 통합 테스트(`test_profile.py`) 4개 — 본 Task에서 **변경하지 않음**.

### 2.3 라우팅 구조

```
이전 (Task-3):                        이후 (Task-4):
  /          → Home                     /             → Home (프로필 완료 시)
  /login     → Login                    /onboarding   → Onboarding (신설)
  /profile   → Profile (dummy)          /login        → Login
  *          → Navigate /                /profile      → Profile (실제 폼)
                                         *             → Navigate /
```

- `Onboarding`은 `ProtectedRoute`로 감싸지 않는다. 인증된 사용자만 접근하되, 프로필 미완성 상태에서도 진입 가능해야 하므로 별도 가드(`OnboardingRoute`) 또는 `ProtectedRoute(requireProfile=false)` 옵션이 필요.
- `Home`, `Profile`은 인증 + 프로필 완료 둘 다 필요. 미완성 시 `/onboarding` redirect.

### 2.4 폼 UI 결정

| 항목 | 입력 방식 | 비고 |
| --- | --- | --- |
| 닉네임 | `<input type="text">` | 1~30자 (프론트 검증) |
| 성별 | 라디오 버튼 4종 | 라벨: 남/여/기타/비공개 → value: male/female/other/private |
| 나이 | `<input type="number">` | 1~149 |
| 직업 | `<input type="text">` | 빈값 허용 |
| 취미 | **콤마 구분 텍스트 입력** | `"독서, 요가"` → `["독서", "요가"]` 변환. 태그 UI는 Task-7로 이월 |
| 관심사 | **콤마 구분 텍스트 입력** | 동일 |
| 알림 시간 | `<input type="time">` | HH:MM 입력 → 백엔드는 HH:MM:SS 받음, axios 직렬화에서 `null` 처리 |

**근거**: 태그 위젯(`react-tag-input` 등) 도입은 의존성 증가 + 디자인 작업 부담이 큼. 콤마 구분 텍스트는 Task-1/2 백엔드 테스트의 입력 형식과 호환됨.

### 2.5 분기 로직 구현

**옵션 A (채택)**: `Login.tsx` 내부에서 직접 분기
```ts
await client.post('/login', { password })
try {
  await client.get('/profile')
  navigate('/')
} catch (e) {
  if (e.response?.status === 404) navigate('/onboarding')
  else throw e
}
```

**옵션 B (기각)**: `useAuth.ts`에 `hasProfile` 상태 추가
- 장점: 한 곳에 응집
- 단점: ProtectedRoute에서 매번 GET 호출 비용 + 상태 동기화 복잡

옵션 A 채택. ProtectedRoute는 추가로 `GET /api/profile`을 호출해 미완성 시 `/onboarding` redirect (Login을 거치지 않고 URL 직접 입력 시 대응).

### 2.6 ProtectedRoute 캐싱 고려

매 라우트 진입마다 `GET /me` + `GET /profile` 2번 호출은 비효율. 단일 가상 사용자 환경에서는 큰 문제 아니지만, 로직 단순화를 위해 **세션 단위 캐시**(`useRef` or `useState` 모듈 레벨)는 도입하지 않고 매번 호출한다. 추후 성능 이슈 발생 시 Task-7로 이월.

### 2.7 디렉토리 변경 요약

```
frontend/src/
├── pages/
│   ├── Onboarding.tsx       ← 신설
│   ├── Profile.tsx          ← 전면 재작성
│   ├── Home.tsx             (변경 없음 또는 헤더에 닉네임만 추가)
│   ├── Login.tsx            ← navigate 분기 로직 갱신
├── components/
│   ├── ProtectedRoute.tsx   ← 프로필 미완성 시 /onboarding redirect
│   ├── ProfileForm.tsx      ← 신설 (Onboarding + Profile 공통 폼)
├── lib/
│   ├── profile.ts           ← 신설 (성별 라벨 매핑, 태그 직렬화 헬퍼)
```

- `ProfileForm.tsx`는 props로 `initial`, `submitLabel`, `onSubmit`을 받아 Onboarding과 Profile 양쪽에서 재사용.

### 2.8 백워드 호환성 및 회귀

- **삭제되는 코드**: `Profile.tsx`의 dummy 내용. 외부 참조 없음.
- **유지되는 컴포넌트**: `Login.tsx`, `Home.tsx`, `useAuth.ts`, `ProtectedRoute.tsx` — props/시그니처 변경 없이 내부 로직만 수정.
- **테스트 영향**: 기존 `Login.test.tsx`(3 케이스)는 로그인 성공 후 navigate 검증이 있을 가능성. 현재 코드는 `/qna`로 가는데, Task-3 시점에 이 라우트가 제거됐으므로 사실상 이미 깨졌을 가능성 있음 → 확인 필요. (현재 11 passed 상태로 봐서는 navigate 자체를 검증하지 않을 듯)

---

## 3. Open Questions

다음 항목은 코드 작성 전 사용자 확인 필요. **기본 답안**으로 진행하되, 변경 요청 시 본 문서 수정 후 재시작.

| # | 항목 | 기본 답안 | 대안 |
| --- | --- | --- | --- |
| 1 | 취미/관심사 입력 방식 | **콤마 구분 텍스트** (`"독서, 요가"` → 배열) | 체크박스 프리셋 / 태그 칩 UI |
| 2 | 온보딩 진입 후 뒤로가기 가능 여부 | **뒤로가기 없음** (프로필 완성해야 Home 진입) | 헤더에 "나중에 하기" 버튼 |
| 3 | ProtectedRoute의 프로필 체크 | **매 라우트 진입마다 GET /profile** | 세션 캐시 (Task-7 이월) |
| 4 | 첫 로그인 후 홈 안내문구 | **표시 안 함** (Task-7로 이월) | Onboarding 완료 직후 toast 1회 |
| 5 | Home 헤더에 닉네임 노출 | **현 단계 미반영** (아이콘만 유지, 향후 추가) | 닉네임 + 아이콘 동시 표시 |
| 6 | Profile 저장 후 자동 이동 | **저장 성공 시 Home으로 navigate** (사용자 의도 확인용) | 머무름 + toast 알림만 |
| 7 | 로그아웃 후 이동 | **`/login`으로 navigate** + isAuthed 초기화 | 페이지 새로고침 |
| 8 | 알림 시간 미입력 시 직렬화 | **빈 문자열 → `null` 변환 후 PUT** | 항상 PUT (백엔드가 빈 문자열 거부할 위험) |

---

## 4. Approach (구현 전략)

1. **공통 폼 부품부터**: `ProfileForm.tsx` + `lib/profile.ts`를 먼저 만들고, Onboarding/Profile이 조립.
2. **Onboarding → Login 분기 → Profile → ProtectedRoute 보강 순**으로 작업. 각 단계마다 빌드 + 기존 테스트 회귀 확인.
3. **백엔드는 손대지 않음**. 기존 API/스키마/테스트(`test_profile.py` 4개)를 그대로 활용.
4. **한 todo 당 1 커밋 원칙**(Task-3과 동일). Verify 명령 통과 후에만 다음 todo로 진행.
5. **테스트 마이그레이션 마지막**: Login 테스트는 분기 로직 추가 케이스로 보강. Onboarding/Profile은 신설.
6. 폼 유효성은 HTML5 `required` + `minLength` + `min`/`max` 우선 사용. 정교한 에러 메시지는 Task-7 이월.

---

## 5. Todo List

### Phase 1 — 공통 부품 신설

- [ ] **1.1** `frontend/src/lib/profile.ts` 작성
  - `GENDER_OPTIONS: Array<{value, label}>` — male/female/other/private + 한국어 라벨.
  - `parseCsvTags(value: string): string[]` — 콤마 구분 → 배열, 빈 토큰 제외.
  - `stringifyTags(arr: string[]): string` — 배열 → "a, b, c".
  - `normalizeNotificationTime(v: string): string | null` — 빈값/공백 → `null`, "HH:MM" → 그대로.
  - Verify: `npm run build` 통과.

- [ ] **1.2** `frontend/src/components/ProfileForm.tsx` 신설
  - props: `initial: ProfileFormValue`, `submitLabel: string`, `onSubmit: (v) => Promise<void>`, `onCancel?: () => void`.
  - 필드: 닉네임/성별(라디오)/나이/직업/취미(csv)/관심사(csv)/알림 시간.
  - HTML5 검증 + submit 시 `lib/profile.ts` 변환 적용.
  - 제출 중 disabled, 에러 시 `<p role="alert">` 표시.
  - Verify: 빌드 통과 + 다음 todo에서 사용해 검증.

### Phase 2 — 온보딩 화면

- [ ] **2.1** `frontend/src/pages/Onboarding.tsx` 신설
  - 마운트 시 `GET /api/profile` 호출 → 200이면 이미 완성된 상태이므로 `/`로 즉시 redirect.
  - 404인 경우만 폼 표시.
  - `<ProfileForm>` 렌더, `onSubmit` 내부에서 `PUT /api/profile` → 성공 시 `navigate('/')`.
  - 뒤로가기 버튼 없음 (Open Question #2 기본 답안).
  - Verify: `npm run build` 통과.

- [ ] **2.2** `frontend/src/App.tsx` 라우팅 갱신
  - `<Route path="/onboarding" element={<Onboarding />} />` 추가.
  - `<Route path="*" element={<Navigate to="/" />}>`는 유지하되 onboarding 이후로 둘 것.
  - Verify: 빌드 통과.

### Phase 3 — 로그인 분기 로직

- [ ] **3.1** `frontend/src/pages/Login.tsx` 수정
  - 로그인 성공 직후 `try { GET /profile; navigate('/') } catch (e) { if 404 navigate('/onboarding') else throw }`.
  - 5xx/네트워크 에러 시 기존 에러 처리 유지.
  - Verify: `Login.test.tsx`에서 분기 케이스 추가 후 통과.

### Phase 4 — Profile 화면 재작성

- [ ] **4.1** `frontend/src/pages/Profile.tsx` 전면 재작성
  - 마운트 시 `GET /api/profile`로 초기값 로드. 404면 `/onboarding` redirect (방어 차원).
  - `<ProfileForm initial={loaded} submitLabel="저장" onSubmit={put}>` 렌더.
  - 헤더: 좌측 "← 뒤로" 버튼 (Home 복귀) + 우측 "로그아웃" 버튼.
  - 로그아웃: `useAuth().logout()` → `navigate('/login', { replace: true })`.
  - 저장 성공 후: `navigate('/')` (Open Question #6 기본 답안).
  - Verify: `npm run build` 통과 + Phase 6 테스트.

### Phase 5 — ProtectedRoute 보강

- [ ] **5.1** `frontend/src/components/ProtectedRoute.tsx` 수정
  - props 추가: `requireProfile?: boolean` (기본 `true`).
  - `requireProfile=true`인 경우 인증 통과 후 추가로 `GET /api/profile` 시도. 404면 `/onboarding` redirect.
  - 호출 비용: 라우트 진입마다 1회 (Open Question #3 기본 답안).
  - Verify: 빌드 통과.

- [ ] **5.2** `App.tsx`에서 Home/Profile을 `ProtectedRoute`로 감싸기
  - `/` → `<ProtectedRoute><Home /></ProtectedRoute>`
  - `/profile` → `<ProtectedRoute><Profile /></ProtectedRoute>`
  - `/onboarding` → `<ProtectedRoute requireProfile={false}><Onboarding /></ProtectedRoute>`
  - Verify: 빌드 통과 + 수동 시나리오(Phase 7) 통과.

### Phase 6 — 테스트 신설 및 갱신

- [ ] **6.1** `frontend/tests/handlers.ts` 확장
  - `GET /api/profile`: 기본 404 응답. 테스트 케이스에서 `server.use(...)`로 200 오버라이드.
  - `PUT /api/profile`: 받은 body를 그대로 200으로 반환.
  - `POST /api/logout`: 200 `{ ok: true }` 반환. (Profile 6.3(c) 로그아웃 테스트용)
  - Verify: 기존 11개 테스트 회귀 0 fail.

- [ ] **6.2** `frontend/tests/Onboarding.test.tsx` 신설 (3 케이스)
  - (a) 마운트 시 `GET /profile` 호출. 404 응답 시 폼이 표시된다.
  - (b) `GET /profile`이 200이면 즉시 Home(`/`)으로 이동한다(`MemoryRouter` + `useLocation` 검증).
  - (c) 필수 항목(닉네임/성별/나이) 입력 후 "시작하기" 클릭 → `PUT /profile` 호출 + navigate('/').
  - Verify: 3 passed.

- [ ] **6.3** `frontend/tests/Profile.test.tsx` 신설 (3 케이스)
  - (a) 마운트 시 `GET /profile` 호출 후 초기값이 폼에 표시된다 (닉네임/성별/나이/취미 등).
  - (b) 값 수정 후 "저장" → `PUT /profile`이 변경된 body로 호출 + navigate('/').
  - (c) "로그아웃" 버튼 클릭 → `POST /logout` 호출 + navigate('/login').
  - Verify: 3 passed.

- [ ] **6.4** `frontend/tests/Login.test.tsx` 갱신
  - 기존 3 케이스(잘못된 비밀번호 / 성공 / 빈 입력 비활성) 중 "성공" 케이스에 분기 검증 추가:
    - 성공 + GET /profile 404 → `/onboarding` navigate
    - 성공 + GET /profile 200 → `/` navigate (신규 1 케이스 추가)
  - 총 4 케이스 → 4 passed.
  - Verify: 4 passed.

- [ ] **6.5** 프론트엔드 전체 회귀
  - 실행: `cd frontend && npm test -- --run && npm run build`
  - 누적 테스트: 4(Login) + 3(Home) + 3(ChatSessionPanel) + 2(DiaryDetailModal) + 3(Onboarding) + 3(Profile) = **18 passed**.
  - 빌드 번들 크기 ±10% 이내 확인.

### Phase 7 — 수동 통합 검증

- [ ] **7.1** 백엔드 + 프론트 동시 기동 후 수동 E2E
  - 실행: `make db && make migrate && make backend` + `make frontend`.
  - 시나리오:
    1. 로그아웃 상태에서 `/`접근 → `/login` redirect.
    2. 로그인 (`inha-nxt`) → 프로필 없으면 `/onboarding`으로.
    3. 온보딩 폼 작성 후 제출 → Home 캘린더 표시.
    4. 헤더 프로필 아이콘 → `/profile`에서 기존 값 표시 + 수정 가능.
    5. 닉네임 변경 → 저장 → Home 복귀 → 다시 `/profile` 진입 시 변경된 값 유지.
    6. 로그아웃 클릭 → `/login`. 새로고침해도 인증 안 됨.
    7. (DB 리셋 없이) 다시 로그인 → 프로필 있으므로 Home으로 바로 이동.
  - Verify: 7개 시나리오 모두 동작 + 콘솔 에러 0건.

---

## 6. Test Plan

### 6.1 신규/갱신 단위·통합 테스트

| Test | Input | Expected |
| --- | --- | --- |
| `Onboarding.test_form_shown_on_404` | mount + GET 404 | 폼 렌더 + 닉네임 input 존재 |
| `Onboarding.test_redirects_when_profile_exists` | mount + GET 200 | `/` 로 navigate |
| `Onboarding.test_submit_calls_put_and_navigates` | 필수 3개 입력 + 제출 | `PUT /profile` 1회 + navigate `/` |
| `Profile.test_loads_initial_values` | mount + GET 200 | 닉네임/성별/나이 input의 value 일치 |
| `Profile.test_save_calls_put_and_navigates` | 닉네임 수정 + 저장 | PUT body의 nickname 변경 + navigate `/` |
| `Profile.test_logout_calls_api_and_navigates` | 로그아웃 클릭 | `POST /logout` + navigate `/login` |
| `Login.test_success_with_profile_navigates_home` | 로그인 + GET 200 | navigate `/` |
| `Login.test_success_without_profile_navigates_onboarding` | 로그인 + GET 404 | navigate `/onboarding` |

### 6.2 통합 시나리오 (수동 E2E, Phase 7.1)

| Scenario | Final state |
| --- | --- |
| 비로그인 상태로 `/` 진입 | `/login` 리다이렉트 |
| 로그인 + 프로필 없음 | `/onboarding` 자동 진입 |
| 온보딩 제출 | Home 이동, 캘린더 표시 |
| `/profile`에서 닉네임 수정 | 저장 후 Home 복귀, 재진입 시 변경 유지 |
| 로그아웃 | `/login`, 새 세션 |
| 재로그인 (프로필 존재) | Home 직행 (`/onboarding` 우회) |

### 6.3 회귀 보장

- 백엔드 기존 34개 → **34 passed** (변경 없음)
- 프론트 기존 11개 → **18 passed** (Login 3→4, Onboarding +3, Profile +3)
- `npm run build` 빌드 성공 유지

### 6.4 자동화 명령

```bash
# 백엔드 (회귀만)
cd 2026-cloud-computing-days/backend && .venv/bin/pytest -v --tb=short

# 프론트
cd 2026-cloud-computing-days/frontend && npm test -- --run && npm run build

# 로컬 통합
make db && make migrate && make backend   # 터미널 1
make frontend                              # 터미널 2
```

---

## 7. Resume Protocol

Task-3과 동일한 5단계 원칙. 추가로:

- **Login 분기 변경 도중 중단(Phase 3.1)**: navigate 경로 일관성이 깨질 수 있음. 재개 시 `Login.test.tsx` 통과 여부 먼저 확인.
- **ProtectedRoute 변경 도중 중단(Phase 5.1)**: 인증된 사용자도 무한 redirect 루프에 빠질 위험. 재개 시 `/onboarding` 자체에 `requireProfile=false`가 적용됐는지 grep으로 확인.
- **백엔드 변경 없음**: 본 Task에서 `backend/` 디렉토리 수정 시 즉시 중단하고 원복. Task-2/3 테스트(34 passed)를 그대로 유지해야 함.

---

## 8. Hand-off

Task-4.md 작성 완료. **8개 Open Questions의 기본 답안에 동의하는지** 또는 변경할지 알려주세요. 변경 사항이 있으면 본 문서를 먼저 수정 후 코드 작업을 시작합니다. **승인 전까지 코드는 절대 수정하지 않습니다.**
