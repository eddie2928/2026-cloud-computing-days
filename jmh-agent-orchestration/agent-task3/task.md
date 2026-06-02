# Task: 추천 Stub 모듈 + /api/recommend/songs

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-backend
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
취향 프로필 기반 노래 추천을 **Stub**으로 구현한다 (Bedrock 미연결, 향후 교체).
- 신규 모듈 `backend/app/recommend_stub.py`:
  - `def recommend_songs(taste: dict, limit: int = 5) -> dict` (또는 async 불필요한 순수 함수).
  - taste의 `music_genres`, `preferred_music_mood`, `favorite_artists`로부터 **결정론적**으로 추천 리스트 생성 (입력 같으면 출력 같게 — 정렬/시드 고정).
  - 반환: `{"items": [{"query": str, "title": str, "artist": str, "reason": str}], "meta": {"source": "stub"}}`.
  - taste가 비어있으면 기본 추천(예: 인기/잔잔 키워드)으로 폴백.
  - 파일 상단에 "Bedrock 연결 시 이 함수를 교체" 주석 + app/bedrock.py의 [DISABLED] 패턴 참고.
- 신규 라우터 또는 기존 taste 라우터에 엔드포인트 추가:
  - `GET /api/recommend/songs?limit=` (require_session). taste-profile 조회 → recommend_songs 호출 → 반환.
  - taste-profile 미작성 시 빈 items + 안내 meta.
  - **권장: 신규 파일 `backend/app/routers/recommend.py`** (taste.py를 Task2가 쓰므로 충돌 회피). main.py에 등록.

## 컨텍스트
- **Task 2가 `TasteProfile` 모델과 `/api/taste-profile`를 이미 구현했다.** taste.py / models.py를 읽어 TasteProfile 컬럼명을 확인하라.
- taste row → dict 변환은 SQLAlchemy 객체 속성 접근으로. 조회 패턴은 routers/taste.py 또는 profile.py 참고.
- main.py import 라인에 `recommend` 추가 + include_router 1줄.

## 기존 단위 테스트 (참조)
- backend/tests/unit/test_bedrock_stub.py (stub 결정론 테스트 패턴 참고)
- backend/tests/unit/test_taste_router.py, backend/tests/integration/test_profile.py

## 금지 사항
- models.py, alembic, routers/music.py, routers/taste.py 수정 금지 (읽기만). main.py는 recommend 등록 라인만 추가.
- 실제 Bedrock/boto3 호출 금지 (stub만).

## 완료 조건
- recommend_stub.py + routers/recommend.py + main.py 등록.
- `cd backend && python -c "import app.main"` 무오류.
- `cd backend && python -m pytest tests/unit -q` 통과 (추천 stub 결정론 단위 테스트 포함).
- result.md Status: DONE.

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, recommend_stub.py + routers/recommend.py 존재, main.py에 recommend 등록, pytest tests/unit 통과. NEEDS_CONTEXT/BLOCKED 시에도 종료. 최대 45턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
backend/tests/unit/test_recommend_stub.py — 결정론성(동일 입력→동일 출력), 빈 taste 폴백, limit 준수.
### 완료 시 보고
result.md에 작성한 테스트 파일과 covers 명시.

## 작업 디렉토리
C:/Users/ab550/OneDrive/Desktop/projects/proj_days

## Resume 규약 (필수)
1. atomic 단위 분할.
2. 매 단위 git-commit-lock.sh로 커밋:
   ```bash
   bash ~/.claude/skills/jmh-orchestrator/scripts/git-commit-lock.sh \
     --repo "C:/Users/ab550/OneDrive/Desktop/projects/proj_days" \
     --message "task(agent-task3): 추천 stub + /api/recommend/songs" \
     --add "backend/app/recommend_stub.py backend/app/routers/recommend.py backend/app/main.py backend/tests/unit/test_recommend_stub.py"
   ```
3. result.md 점진 업데이트.
4. 재개 시 result.md/git log 확인.

## Retrospect (필수)
완료 후: jmh-agent-orchestration/retrospect/jmh-worker-backend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task3/ 에서 통신. 차단 시 question.md + Status=NEEDS_CONTEXT 후 중단.
