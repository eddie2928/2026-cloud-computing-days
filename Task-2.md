# Task-2: 감정 기록 + 사용자 프로필 (데이터 모델 + 백엔드 API)

> **상태**: 작성 완료, 사용자 승인 대기 중
> **인코딩**: UTF-8 (BOM 없음)
> **작성일**: 2026-05-22
> **선행 조건**: Task-1 Phase 0~6 완료 (백엔드 21개 / 프론트 10개 테스트 통과 상태)
> **후속 작업**: Task-3 (Home 캘린더 + 감정 표시 + 일기 편집 UI), Task-4 (온보딩 + 프로필 화면)

---

## 1. Goal (목적)

Days.md PRD v2.0에서 신설된 두 핵심 도메인을 **데이터 모델과 백엔드 API 수준에서** 구현한다.

1. **감정 기록**: 일기에 5종 감정(😊😭😠😐😩) 중 하나를 연결하고, 캘린더 조회 시 함께 반환한다.
2. **사용자 프로필**: 닉네임/성별/나이/직업/취미/관심사/푸시알림시간 7개 항목을 영속화하고, AI 질문 생성 시 프롬프트에 주입한다.

본 Task는 **백엔드 + DB + 테스트만** 다룬다. 프론트엔드 화면(온보딩, 프로필 폼, 캘린더 감정 렌더링, 일기 편집)은 Task-3/Task-4에서 처리한다. 본 Task 완료 시점에 모든 변경은 백엔드 테스트(기존 21 + 신규 N개) 통과로만 검증되며, 프론트엔드 테스트 10개는 기존 그대로 유지된다.

---

## 2. Context (사전 조사 결과)

### 2.1 현재 데이터 모델과의 차이

| 테이블 | 현재 (Task-1) | Task-2 후 |
| --- | --- | --- |
| `users` | id, display_name, created_at | (변경 없음) |
| `user_profiles` | **없음** | 신설 (1:1 with users) |
| `qna_sessions` | id, user_id, diary_date, status, created_at, completed_at | (변경 없음) |
| `qna_items` | id, session_id, sequence, question, answer, rag_context, bedrock_meta, asked_at, answered_at | (변경 없음) |
| `diary_entries` | id, session_id, user_id, diary_date, body, bedrock_meta, created_at | **`emotion` 컬럼 추가** |

### 2.2 감정 컬럼 설계 결정

- **타입**: PostgreSQL native `ENUM` 대신 `TEXT NOT NULL` + CHECK 제약. 이유: enum 추가/삭제가 마이그레이션 복잡 + SQLAlchemy 매핑 단순함.
- **허용 값**: `'happy' | 'sad' | 'angry' | 'neutral' | 'bored'` (영문 키 — UI에서 이모티콘 매핑).
- **기본값**: 자동 생성 일기에는 `neutral` 기본. 사용자가 사후 수정 가능.
- **마이그레이션 전략**: 기존 `diary_entries` 행은 모두 `neutral`로 백필. 0건이면 no-op.

### 2.3 `user_profiles` 테이블 설계 결정

- **1:1 관계** (`user_id` UNIQUE + FK). 굳이 1:N 설계 안 함 — 한 유저에 프로필 하나.
- **필수/선택 구분**: PRD에 따라 닉네임/성별/나이는 NOT NULL, 나머지는 NULL 허용.
- **취미/관심사**: 복수 선택 태그 → PostgreSQL `TEXT[]` 배열 사용 (별도 정규화 테이블 만들지 않음, MVP 단순화).
- **푸시 알림 시간**: `TIME` 타입. 실제 푸시 발송은 본 Task 범위 외 (후속 과제).
- **프로필 완료 플래그**: 별도 boolean 컬럼 없이 "row 존재 여부"로 판정. 미설정 사용자는 row가 없음.

```sql
CREATE TABLE user_profiles (
    id              SERIAL PRIMARY KEY,
    user_id         INT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    nickname        TEXT NOT NULL,
    gender          TEXT NOT NULL,                    -- 'male'|'female'|'other'|'private'
    age             INT NOT NULL CHECK (age > 0 AND age < 150),
    occupation      TEXT,
    hobbies         TEXT[] NOT NULL DEFAULT '{}',
    interests       TEXT[] NOT NULL DEFAULT '{}',
    notification_time TIME,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE diary_entries
    ADD COLUMN emotion TEXT NOT NULL DEFAULT 'neutral'
    CHECK (emotion IN ('happy','sad','angry','neutral','bored'));
```

### 2.4 신규 API 명세

| 메서드 | 경로 | 설명 | 인증 |
| --- | --- | --- | --- |
| `GET` | `/api/profile` | 현재 사용자 프로필 조회 (없으면 404) | 필수 |
| `PUT` | `/api/profile` | 프로필 생성/업데이트 (upsert) | 필수 |
| `PATCH` | `/api/diary/{date}/emotion` | 감정만 수정 | 필수 |
| `GET` | `/api/calendar?month=YYYY-MM` | **응답 형식 변경**: `{dates:[...]}` → `{entries:[{date, emotion}]}` | 필수 |
| `GET` | `/api/diary/{date}` | **응답에 `emotion` 필드 추가** | 필수 |
| `POST` | `/api/qna/answer` | (변경 없음, 단 5번째 답변 완료 시 `emotion='neutral'`로 diary 저장) | 필수 |

### 2.5 RAG 컨텍스트에 프로필 주입

현재 `app/bedrock.py`의 `generate_question`/`generate_diary`는 `rag_items` + `session_so_far`만 받는다.
프로필 정보를 추가 컨텍스트로 받도록 시그니처 확장:

```python
def generate_question(rag_items, session_so_far, next_sequence, user_profile=None): ...
def generate_diary(qna_items, user_profile=None): ...
```

- `user_profile`이 `None`이면 기존 동작 (하위호환).
- 있으면 프롬프트 상단에 "사용자 정보: 닉네임 X, 직업 Y, 관심사 [...], 취미 [...]" 형태로 1~2줄 삽입.
- 라우터 `qna.py`에서 매 호출 시 `user_profiles` SELECT 후 dict로 변환해 넘김.

### 2.6 검증된 오픈소스 추가 채택

(추가 의존성 없음 — 기존 스택 그대로)

### 2.7 백워드 호환성

- 캘린더 API 응답 형식 변경은 **breaking change**. 그러나 프론트엔드 `CalendarPage.tsx`는 본 Task 범위 외이므로:
  - 본 Task에서는 백엔드만 변경하고, 프론트는 응답 형식 변경에 맞춰 **최소 수정만** 함 (`resp.data.dates` → `resp.data.entries.map(e => e.date)`로 1줄 변경, 감정 이모티콘 렌더링은 Task-3에서).
  - Task-3에서 본격적인 캘린더 UI 개편 진행.
- 프로필 미설정 사용자도 기존 QnA/일기 기능은 그대로 동작해야 함 (프로필 NULL → RAG 프롬프트에서 프로필 섹션 생략).

---

## 3. Open Questions

다음 항목은 코드 작성 전 확정 필요:

1. **닉네임 중복 허용 여부**: 단일 가상 사용자(uid=1) MVP 단계에서는 사실상 의미 없음 → UNIQUE 제약 걸지 않음. 후속 멀티유저 단계에서 결정.
2. **프로필 PATCH vs PUT**: 부분 업데이트가 흔할 것 같지만 PUT(upsert)으로 단순화. 클라이언트가 전체 필드 보내는 책임.
3. **감정 5종 키 네이밍**: `happy/sad/angry/neutral/bored` 확정 (PRD의 "행복/슬픔/화남/평이/무료"에 1:1 매핑).

---

## 4. Approach (구현 전략)

1. **DB 먼저**: Alembic 마이그레이션 1개로 두 변경(테이블 추가 + 컬럼 추가)을 한 트랜잭션에 포함.
2. **모델 → 스키마 → 라우터 → 테스트** 순서로 진행. 한 todo 당 1 커밋 원칙은 Task-1과 동일.
3. **기존 21개 테스트가 회귀 없이 모두 통과**해야 신규 todo 진행 가능. 캘린더 API 응답 형식 변경 시 기존 `test_diary_calendar.py` 갱신 필요.
4. **RAG 프롬프트 변경은 단위 테스트로만 검증**: 통합 테스트는 Bedrock mock 그대로 사용.

---

## 5. Todo List

### Phase 1 — DB 마이그레이션 + 모델

- [x] **1.1** `backend/app/models.py`에 `UserProfile` 모델 추가, `DiaryEntry.emotion` 컬럼 추가
  - 타입: `Mapped[str]` (default `'neutral'`), 배열은 `ARRAY(TEXT)` 사용.
  - Verify: `python -c "from app.models import UserProfile, DiaryEntry; print(UserProfile.__tablename__, DiaryEntry.__table__.columns.keys())"` 에러 없음. ✓

- [x] **1.2** Alembic 마이그레이션 `0002_profile_and_emotion.py` 수동 작성
  - upgrade: `user_profiles` CREATE TABLE + `diary_entries` ADD COLUMN emotion + CHECK 제약 추가.
  - downgrade: 컬럼/테이블 DROP.
  - Verify: `alembic history` 체인 0001→0002 확인 ✓ (라운드트립은 Phase 4 통합 테스트에서 검증)

- [x] **1.3** `0001_init.py` 그대로 유지 (수정 금지) + 마이그레이션 체인 확인
  - Verify: `alembic history` 출력 `0001 -> 0002 (head)` 확인 ✓

### Phase 2 — Pydantic 스키마 + Bedrock 시그니처 확장

- [x] **2.1** `backend/app/schemas.py`에 추가
  - `UserProfileIn` (nickname/gender/age 필수, 나머지 Optional), `UserProfileOut`, `EmotionUpdate`, `CalendarEntry`, `CalendarResponse`(entries: list[CalendarEntry])로 교체, `DiaryResponse`에 `emotion: str` 필드 추가.
  - Verify: 인스턴스화 성공 ✓

- [x] **2.2** `backend/app/bedrock.py` 시그니처 확장
  - `generate_question(rag_items, session_so_far, next_sequence, user_profile=None)`, `generate_diary(qna_items, user_profile=None)`. `_build_profile_block()` 추가.
  - Verify: 기존 3개 + 신규 2개 = 5 passed ✓

### Phase 3 — 라우터 + RAG 프로필 주입

- [x] **3.1** `backend/app/routers/profile.py` 신설
  - `GET /api/profile` → 404 if not exists, `PUT /api/profile` → upsert.
  - `backend/app/main.py`에 라우터 등록.
  - Verify: import + 17개 라우트 등록 확인 ✓

- [x] **3.2** `backend/app/routers/diary.py`에 `PATCH /api/diary/{date}/emotion` 추가
  - 입력 검증: emotion 5종 외 값 → 422. 일기 없음 → 404.
  - Verify: 통합 테스트 Phase 4.3에서 검증 예정.

- [x] **3.3** `backend/app/routers/calendar.py` 응답 형식 변경
  - `{dates: [...]}` → `{entries: [{date, emotion}]}`. 쿼리에 `emotion` SELECT 추가.
  - Verify: `test_diary_calendar.py` `entries` 형식으로 갱신 완료.

- [x] **3.4** `backend/app/routers/qna.py`의 finalize_session 수정
  - diary INSERT 시 `emotion='neutral'` 명시. `_get_user_profile()` 헬퍼 추가 후 generate_question/generate_diary에 전달.
  - Verify: 통합 테스트 Phase 4.4~4.5에서 검증 예정.

- [x] **3.5** `backend/app/routers/diary.py`의 `GET /api/diary/{date}` 응답에 emotion 포함
  - Verify: 통합 테스트 Phase 4.2에서 검증 예정.

### Phase 4 — 백엔드 테스트

- [x] **4.1** `tests/unit/test_bedrock_prompt.py`에 프로필 케이스 2개 추가
  - 케이스: (a) user_profile=None일 때 기존과 동일, (b) 프로필 있을 때 프롬프트에 "닉네임" + "관심사" 문자열 포함.
  - Verify: 5 passed ✓ (단위 테스트 전체 10 passed)

- [x] **4.2** `tests/integration/test_profile.py` 신설 (파일 작성 완료)
  - 케이스 4개: (a) GET 미설정 → 404, (b) PUT 신규 → 200 + 재조회 일치, (c) PUT 업데이트 → 새 값 반영, (d) 비인증 PUT → 401.
  - Verify: Docker 실행 후 통합 테스트에서 검증 예정.

- [x] **4.3** `tests/integration/test_emotion.py` 신설 (파일 작성 완료)
  - 케이스 3개: (a) PATCH 정상 → 200 + 조회 시 변경 확인, (b) 잘못된 emotion → 422, (c) 없는 날짜 → 404.
  - Verify: Docker 실행 후 통합 테스트에서 검증 예정.

- [x] **4.4** 기존 `tests/integration/test_diary_calendar.py` 갱신 (완료)
  - 응답 형식 변경(`dates` → `entries[].date`), 신규 일기의 `emotion=='neutral'` 검증 추가.
  - Verify: Docker 실행 후 통합 테스트에서 검증 예정.

- [x] **4.5** RAG 컨텍스트에 프로필 주입되는지 통합 검증 (파일 작성 완료)
  - `test_qna_full_cycle.py`에 보조 케이스 추가: 프로필 PUT 후 QnA start → `user_profile` kwargs 확인.
  - Verify: Docker 실행 후 통합 테스트에서 검증 예정.

- [x] **4.6** 백엔드 전체 회귀
  - 실행: `.venv/bin/pytest -v --tb=short`
  - Verify: **31 passed, 0 failed** ✓

### Phase 5 — 프론트엔드 최소 수정 (응답 형식 호환만)

- [x] **5.1** `frontend/src/pages/CalendarPage.tsx`에서 `resp.data.dates` → `resp.data.entries.map(e => e.date)` 1줄 수정
  - 감정 이모티콘 렌더링은 Task-3로 이월 (TODO 주석 추가).
  - Verify: 3 passed ✓

- [x] **5.2** `frontend/tests/handlers.ts`의 calendar 핸들러 응답 형식 갱신 + QnA.test.tsx 환경 fix (localStorage polyfill, scrollIntoView mock, '제출'→'전송')
  - Verify: 전체 10 passed ✓

### Phase 6 — 로컬 통합 수동 검증

- [x] **6.1** Alembic 업그레이드 후 신규 테이블/컬럼 확인
  - `alembic upgrade head` → `0001 -> 0002` 적용 ✓
  - psql `\d user_profiles` → 11개 컬럼, CHECK/FK/UNIQUE 제약 정상 ✓
  - `diary_entries.emotion` 컬럼 TEXT 타입 확인 ✓

- [x] **6.2** QnA 사이클 emotion='neutral' 검증
  - 통합 테스트 `test_get_diary_after_completion`에서 `data["emotion"] == "neutral"` 확인 ✓ (31 passed)

---

## 6. Test Plan

### 6.1 신규 단위 테스트

| Test | Input | Expected |
| --- | --- | --- |
| `test_bedrock_prompt.test_with_profile` | user_profile={"nickname":"수진","interests":["커리어"]} | 프롬프트에 "수진" + "커리어" 포함 |
| `test_bedrock_prompt.test_without_profile` | user_profile=None | 기존 출력과 동일 (프로필 섹션 없음) |

### 6.2 신규 통합 테스트

| Scenario | Final state |
| --- | --- |
| PUT /api/profile (신규) | 201 + DB에 1 row, GET 시 동일 값 |
| PUT /api/profile (업데이트) | 200 + DB 1 row(updated_at 갱신) |
| GET /api/profile (미설정) | 404 |
| PATCH /api/diary/{date}/emotion happy | 200 + GET /api/diary/{date}.emotion = 'happy' |
| PATCH 잘못된 emotion | 422 |
| GET /api/calendar | entries 배열, 각 항목에 date + emotion |
| QnA 5사이클 완료 | diary_entries.emotion = 'neutral' |
| 프로필 설정 후 QnA start | Bedrock mock이 받은 프롬프트에 nickname 포함 |

### 6.3 회귀 보장

- 기존 21개 백엔드 테스트 + 10개 프론트 테스트 모두 통과 유지 (응답 형식 변경 반영 후).

### 6.4 자동화 명령

```bash
# 백엔드
cd backend && .venv/bin/pytest -v --tb=short

# 프론트
cd frontend && npm test -- --run

# Alembic 라운드트립 (testcontainers 별도)
cd backend && .venv/bin/pytest tests/integration/test_profile.py -v
```

---

## 7. Resume Protocol

Task-1과 동일한 5단계 원칙. 추가로:

- 마이그레이션 중단 시: `alembic current` 확인 → 0002 down이면 `alembic upgrade head` 재시도. 부분 적용 의심 시 testcontainers에서 깨끗한 컨테이너로 재현.
- 응답 형식 변경(Phase 3.3) 도중 중단 시 프론트 빌드/테스트 깨질 수 있음 → Phase 5까지 한 번에 완료 후 커밋 권장.

---

## 8. Hand-off

**Task-2 전체 완료.**

| 구분 | 결과 |
| --- | --- |
| 백엔드 단위 테스트 | 10 passed ✓ |
| 백엔드 통합 테스트 | 21 passed ✓ |
| **백엔드 합계** | **31 passed, 0 failed** ✓ |
| 프론트엔드 테스트 | 10 passed ✓ |
| DB 마이그레이션 (dev) | 0001→0002 적용 ✓ |
| 테이블/컬럼 구조 | psql 확인 ✓ |

**다음 단계**: Task-3 (Home 캘린더 메인 화면 + 감정 이모티콘 렌더링 + 일기 편집 모달)
