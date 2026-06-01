# Orchestrator Plan: days-taste-music

## 메타 정보
- 생성 일시: 2026-06-02T00:00:00+09:00
- 마지막 업데이트: 2026-06-02T00:00:00+09:00
- 상태: IN_PROGRESS
- 통합 테스트 명령어 (backend): `cd backend && python -m pytest -q`
- 통합 테스트 명령어 (frontend): `cd frontend && npx tsc --noEmit && npm test -- --run`
- 테스트 디렉토리: backend/tests/{unit,integration}, frontend/src/**/*.test.tsx

## 요구사항 요약
1. 사용자 프로필에서 상세 취향(좋아하는 노래 장르, MBTI, 이상형 등)을 **단계별 문진 플로우**로 수집한다.
2. 수집한 취향은 RDS(PostgreSQL)에 저장하고, 추후 AI 추천에 쓸 수 있도록 추천 기능을 **Stub**으로 구현한다(Bedrock 미연결).
3. 무료 음원 API(**iTunes Search API**)를 **백엔드 프록시**로 통합하고, 개발자 페이지(Admin)에 API 통신 확인 탭을 추가한다.

## 사용 가능한 Worker 스킬
| Worker | Description | Model |
|--------|-------------|-------|
| jmh-worker-backend | FastAPI 라우팅·DB 스키마·마이그레이션·인증 | sonnet |
| jmh-worker-frontend | React/TS 컴포넌트·페이지·API 연동·폼 | sonnet |
| jmh-worker-infra | Terraform/Docker/CI (이번 run 미사용 예상) | sonnet |

## 도메인 사양 (워커 공통 참조)

### 취향 데이터 모델 (RDS)
신규 테이블 `taste_profiles` (alembic 마이그레이션 `0010_taste_profiles.py`), `users.id`에 1:1.
권장 컬럼 (세부 항목은 워커 판단으로 보강 가능, 단 아래는 포함):
- `user_id` FK UNIQUE NOT NULL (ondelete CASCADE)
- `music_genres` TEXT[] — 좋아하는 노래 장르
- `favorite_artists` TEXT[] — 좋아하는 아티스트
- `preferred_music_mood` TEXT[] — 선호 분위기(잔잔한/신나는/감성적인/집중되는 등)
- `mbti` TEXT NULL — 4글자 또는 NULL
- `ideal_type` TEXT NULL — 이상형 자유서술
- `personality_keywords` TEXT[] — 성격 키워드
- `movie_genres` TEXT[] — 좋아하는 영화/콘텐츠 장르
- `food_preferences` TEXT[] — 음식 취향
- `weekend_style` TEXT NULL — 주말 성향(집/밖 등)
- `life_values` TEXT[] — 중요하게 여기는 가치
- `love_language` TEXT NULL — 사랑의 언어/애정표현 방식
- `answers` JSONB NULL — 문진 원본 응답(향후 문항 확장 대비 유연 저장)
- `completed` BOOL NOT NULL default false
- `created_at`, `updated_at` (timezone=True, server_default now())
> 기존 `user_profiles`는 건드리지 않는다. 신규 테이블로 분리한다.

### 취향 API
- `GET /api/taste-profile` → 200(TasteProfileOut) / 404(미작성)
- `PUT /api/taste-profile` → upsert, 200(TasteProfileOut)
- 모든 엔드포인트 `require_session` 보호. 라우터 파일 `backend/app/routers/taste.py`, main.py에 등록.
- 스키마는 `backend/app/schemas.py`에 `TasteProfileIn`/`TasteProfileOut` 추가.

### 추천 Stub
- `backend/app/recommend_stub.py` — `recommend_songs(taste: dict) -> list[dict]`.
  - taste의 music_genres/preferred_music_mood/favorite_artists로부터 **결정론적**으로 추천 곡 키워드/리스트 생성.
  - 각 항목: `{ "query": str, "title": str, "artist": str, "reason": str }`.
  - meta `{"source": "stub"}` 포함. Bedrock 연결 시 교체 가능하도록 인터페이스를 단순하게.
- 엔드포인트 `GET /api/recommend/songs` (require_session) → taste-profile 없으면 빈 추천 + 안내.
- 향후 Bedrock 스왑 지점을 주석으로 명시(`app/bedrock.py` 패턴 참고).

### 음원 API 프록시 (iTunes Search)
- `backend/app/routers/music.py` — `GET /api/music/search?term=&limit=` (require_session).
  - 서버에서 `https://itunes.apple.com/search?term=<term>&media=music&limit=<limit>` 호출(httpx, 타임아웃 8s).
  - 응답 정규화: `{ "ok": bool, "status_code": int, "latency_ms": int, "count": int, "results": [{trackName, artistName, previewUrl, artworkUrl100, collectionName, trackViewUrl}] }`.
  - 외부 호출 실패 시 502가 아닌 `{ok:false, error:...}` 형태로 친절히 반환(개발자 페이지 진단용).
- `httpx`를 `backend/requirements.txt`에 추가(미존재). 단위 테스트는 httpx 호출을 mock(monkeypatch)하여 외부 네트워크 의존 없이 통과해야 한다.

### 프론트엔드
- 단계별 문진 플로우: 신규 페이지 `frontend/src/pages/TasteSurvey.tsx`, 라우트 `/profile/taste` (App.tsx 등록, ProtectedRoute). 온보딩(Onboarding.tsx) 스타일의 카드형 단계 진행. days-design 스킬 토큰 준수.
- `frontend/src/api/taste.ts` (get/put), `frontend/src/lib/taste.ts` (옵션 상수/직렬화).
- Profile.tsx에 "취향" 진입 카드 + 요약 표시(편집 = 문진 재진행).
- Admin.tsx에 신규 탭 "음악 API": term 입력 → `/api/music/search` 호출 → 통신 상태(HTTP/지연/ok) + 결과 리스트 + 30초 미리듣기(audio) + Raw/Pretty 토글. `frontend/src/api/music.ts` 추가.
> 파일 소유권: T6은 TasteSurvey/Profile/App.tsx/api/taste/lib/taste, T7은 Admin.tsx/api/music 만 수정. 상호 파일 충돌 금지.

## Todo List

- [!] Task 1: 취향 DB 스키마 + 마이그레이션 + 모델 — type: NEW_FEATURE, worker: jmh-worker-backend, depends: none
- [ ] Task 2: 취향 API (GET/PUT) + 스키마 — type: NEW_FEATURE, worker: jmh-worker-backend, depends: Task 1
- [ ] Task 3: 추천 Stub 모듈 + /api/recommend/songs — type: NEW_FEATURE, worker: jmh-worker-backend, depends: Task 2
- [!] Task 4: 음원 프록시 /api/music/search (iTunes) + httpx — type: NEW_FEATURE, worker: jmh-worker-backend, depends: none
- [ ] Task 5: 백엔드 통합 테스트 (취향 CRUD + 추천 stub + 음원 프록시 mock) — type: INTEGRATION_TEST, worker: jmh-worker-backend, depends: Task 2, Task 3, Task 4
- [ ] Task 6: 취향 문진 플로우 페이지 + 라우트 + Profile 진입/요약 — type: NEW_FEATURE, worker: jmh-worker-frontend, depends: Task 2
- [ ] Task 7: 개발자 페이지(Admin) 음악 API 테스트 탭 — type: NEW_FEATURE, worker: jmh-worker-frontend, depends: Task 4
- [ ] Task 8: 프론트 E2E/빌드 검증 (tsc --noEmit + vitest) — type: INTEGRATION_TEST, worker: jmh-worker-frontend, depends: Task 6, Task 7

## 의존성 그래프
```
Task1 ──> Task2 ──> Task3 ─┐
                    └> Task6 ─┐
Task4 ──────────────┬> Task7 ─┤
       Task2,3,4 ──> Task5    │
                    Task6,7 ─> Task8
```
- Wave 1 (병렬): Task1, Task4
- Wave 2: Task2 (Task1 후)
- Wave 3 (병렬): Task3 (Task2 후), Task6 (Task2 후), Task7 (Task4 후)
- Wave 4: Task5 (Task2,3,4 후) — Task3 완료 대기
- Wave 5: Task8 (Task6,7 후)

## 테스트 전략
### 단위 테스트
- 각 워커가 자신 구현에 대해 작성. backend/tests/unit/, frontend는 *.test.tsx (vitest).
- 음원 프록시: httpx 호출 monkeypatch로 외부 네트워크 없이 검증.
### 통합 테스트 (plan 중간 삽입)
- Task 5 (backend 합류점): 취향 upsert→조회, 추천 stub 결정론, 음원 프록시 정상/실패 경로, 미인증 401, 경계값.
- Task 8 (frontend 합류점): tsc 타입체크 + vitest, 라우트/탭 렌더 스모크.
- 위치: backend/tests/integration/, frontend src 내.

## Resume Protocol
1. 이 파일을 읽는다.
2. 마지막 업데이트 일시를 확인한다.
3. 체크박스 상태 확인: [x] 건너뜀 / [!] result.md 확인 후 재시도 / [ ] 의존성 해소 시 시작.
4. status.json을 sync-status.py로 재구성.
5. 대시보드 재기동.
6. 반복 루프 재개.
