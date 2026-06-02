# Task: 취향 API (GET/PUT) + 스키마

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-backend
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
취향 프로필 조회/저장 API를 구현한다.
- `backend/app/schemas.py`에 `TasteProfileIn`, `TasteProfileOut` 추가.
- 신규 라우터 `backend/app/routers/taste.py`:
  - `GET /api/taste-profile` (require_session) → 200(TasteProfileOut) / 404(미작성).
  - `PUT /api/taste-profile` (require_session) → upsert, 200(TasteProfileOut).
- `backend/app/main.py`에 `taste` 라우터 등록 (import 라인 + include_router 1줄).

## 컨텍스트
- **Task 1이 이미 `TasteProfile` 모델을 `backend/app/models.py`에 추가했다.** 먼저 models.py를 읽어 실제 컬럼명을 확인하고 그에 맞춰 스키마를 작성하라.
- 기존 패턴을 그대로 따르라: `backend/app/routers/profile.py`(get/put upsert)와 `backend/app/schemas.py`의 `UserProfileIn/Out`(`model_config = {"from_attributes": True}`).
- prefix는 `/api`, tags=["taste"]. 엔드포인트 경로는 `/taste-profile`.
- TasteProfileIn 필드: 배열 필드는 `list[str] = []` 기본값, 텍스트 nullable은 `Optional[str] = None`, mbti는 `Optional[str]`(검증은 느슨하게 — 빈문자 None 처리), answers는 `Optional[dict] = None`, completed `bool = False`.
- PUT 시 user_profiles의 upsert 로직(profile.py)과 동일 구조: 기존 row select → 없으면 생성 → 필드 대입 → commit → refresh.

## 기존 단위 테스트 (참조)
- backend/tests/integration/test_profile.py (profile CRUD 통합 테스트 패턴 — 인증 fixture/conftest 사용법 그대로 참고)
- backend/tests/unit/test_taste_models.py (Task1 작성, 모델 컬럼 확인용)

## 금지 사항
- models.py, alembic 수정 금지 (Task1 산출물 사용만).
- routers/music.py, recommend 관련 파일 수정 금지.
- main.py는 taste 등록 라인만 추가. 다른 라우터 등록 순서 건드리지 말 것.

## 완료 조건
- schemas.py에 TasteProfileIn/Out, routers/taste.py, main.py 등록 완료.
- `cd backend && python -c "import app.main"` 무오류.
- `cd backend && python -m pytest tests/unit -q` 통과 (취향 스키마/라우터 단위 테스트 포함).
- result.md Status: DONE.

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, schemas.py에 TasteProfileIn/Out, routers/taste.py 존재, main.py에 taste 등록, pytest tests/unit 통과. NEEDS_CONTEXT/BLOCKED 시에도 종료. 최대 45턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
backend/tests/unit/test_taste_router.py 또는 schemas 검증 — TasteProfileIn 기본값/직렬화, TasteProfileOut from_attributes.
### 완료 시 보고
result.md에 작성한 테스트 파일과 covers 소스 명시.

## 작업 디렉토리
C:/Users/ab550/OneDrive/Desktop/projects/proj_days

## Resume 규약 (필수)
1. atomic 단위 분할.
2. 매 단위 git-commit-lock.sh로 커밋:
   ```bash
   bash ~/.claude/skills/jmh-orchestrator/scripts/git-commit-lock.sh \
     --repo "C:/Users/ab550/OneDrive/Desktop/projects/proj_days" \
     --message "task(agent-task2): 취향 API + 스키마" \
     --add "backend/app/schemas.py backend/app/routers/taste.py backend/app/main.py backend/tests/unit/test_taste_router.py"
   ```
3. result.md 점진 업데이트 (IN_PROGRESS→DONE).
4. 재개 시 기존 result.md와 git log 확인.

## Retrospect (필수)
완료 후 작성:
  C:/Users/ab550/OneDrive/Desktop/projects/proj_days/jmh-agent-orchestration/retrospect/jmh-worker-backend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task2/ 에서 통신. 차단 시 question.md + result.md Status=NEEDS_CONTEXT 후 중단.
