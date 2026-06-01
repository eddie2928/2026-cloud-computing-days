# Task: 음원 프록시 /api/music/search (iTunes Search API) + httpx

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-backend
스킬 내의 지시에 따라 caution.md도 읽게 된다.
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
무료 음원 API인 **iTunes Search API**를 백엔드 프록시로 통합한다(CORS 회피 + 통신 확인 목적).
- 신규 라우터 `backend/app/routers/music.py`:
  - `GET /api/music/search?term=<str>&limit=<int, 기본 10, 최대 25>` (require_session 보호).
  - 서버에서 `https://itunes.apple.com/search` 호출. 쿼리: `term`, `media=music`, `limit`, `country=KR`(또는 미지정).
  - httpx.AsyncClient(timeout=8.0) 사용.
  - 정규화 응답:
    ```json
    {
      "ok": true,
      "status_code": 200,
      "latency_ms": 123,
      "count": 10,
      "results": [
        {"trackName": "...", "artistName": "...", "previewUrl": "...",
         "artworkUrl100": "...", "collectionName": "...", "trackViewUrl": "..."}
      ]
    }
    ```
  - 외부 호출 실패(타임아웃/네트워크/비200)는 예외를 던지지 말고 `{"ok": false, "status_code": <or null>, "latency_ms": <ms>, "error": "<메시지>", "results": []}` 로 200 응답(개발자 페이지 진단용). 단, term 누락 등 클라이언트 입력 오류는 422/400.
- `backend/app/main.py`에 `music` 라우터 등록 (기존 include_router 블록에 1줄 추가, import 라인에도 추가).
- `httpx`를 `backend/requirements.txt`에 추가 (현재 미존재).

## 컨텍스트
- 라우터 패턴은 `backend/app/routers/insights.py`, `backend/app/routers/admin.py` 참고. prefix=`/api/music`, tags=["music"].
- 인증 의존성: `from app.auth import require_session`, `user_id: int = Depends(require_session)`.
- main.py 현재 import 라인: `from app.routers import admin, auth, calendar, diary, insights, pet, plans, profile, push, qna, schedules, share, user` → `music` 추가.
- 단위 테스트는 **외부 네트워크 호출 없이** 통과해야 한다. httpx의 `AsyncClient.get`을 monkeypatch하거나 `httpx.MockTransport`/`respx` 미사용 시 monkeypatch로 가짜 응답 주입. 정상/실패/입력검증 3경로 모두 커버.

## 기존 단위 테스트 (참조)
- backend/tests/integration/test_admin.py, backend/tests/unit/test_push.py (라우터/의존성 테스트 패턴 참고)
관련 기존 테스트: 음원 관련 없음 (신규).

## 금지 사항
- backend/app/models.py, schemas.py(취향 부분), 다른 라우터 수정 금지. main.py는 music 등록 2줄만 추가.
- 실제 외부 네트워크에 의존하는 테스트 작성 금지 (반드시 mock).
- alembic/DB 변경 금지.

## 완료 조건
- routers/music.py 작성, main.py 등록, requirements.txt에 httpx 추가.
- `cd backend && python -m pytest tests/unit -q` 통과 (음원 프록시 단위 테스트 포함, 외부 네트워크 없이).
- `cd backend && python -c "import app.main"` 무오류.
- result.md Status: DONE.

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, routers/music.py 존재, main.py에 music 등록, requirements.txt에 httpx, pytest tests/unit 통과(네트워크 mock). NEEDS_CONTEXT/BLOCKED 시에도 종료. 최대 45턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 삼아 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
backend/tests/unit/test_music.py — 정상 응답 정규화, 외부 실패→ok:false, term 누락→4xx.
### 완료 시 보고
result.md에 작성한 테스트 파일과 covers 소스를 명시.

## 작업 디렉토리
C:/Users/ab550/OneDrive/Desktop/projects/proj_days

## Resume 규약 (필수)
1. atomic 단위 분할.
2. 매 단위 git-commit-lock.sh로 커밋:
   ```bash
   bash ~/.claude/skills/jmh-orchestrator/scripts/git-commit-lock.sh \
     --repo "C:/Users/ab550/OneDrive/Desktop/projects/proj_days" \
     --message "task(agent-task4): 음원 프록시 + httpx" \
     --add "backend/app/routers/music.py backend/app/main.py backend/requirements.txt backend/tests/unit/test_music.py"
   ```
3. result.md 점진 업데이트 (IN_PROGRESS→DONE).
4. 재개 시 기존 result.md와 git log 확인.

## Retrospect (필수)
완료 후 작성:
  C:/Users/ab550/OneDrive/Desktop/projects/proj_days/jmh-agent-orchestration/retrospect/jmh-worker-backend-{TIMESTAMP}.md
이슈 기록 (없으면 "이슈 없음").

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task4/ 에서 통신.
차단 시 question.md 작성 + result.md Status=NEEDS_CONTEXT 후 중단.
