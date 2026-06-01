# Task: 취향 DB 스키마 + 마이그레이션 + 모델

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-backend
스킬 내의 지시에 따라 caution.md도 읽게 된다.
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
사용자 상세 취향을 저장할 신규 테이블 `taste_profiles`를 추가한다.
- `backend/app/models.py`에 `TasteProfile` 모델 추가 (User에 1:1 relationship).
- `backend/alembic/versions/0010_taste_profiles.py` 마이그레이션 작성 (down_revision = "0009", 0009 파일에서 revision id 확인).
- PostgreSQL 배열은 `sqlalchemy.dialects.postgresql.ARRAY(TEXT)`, JSONB 사용 (기존 models.py 패턴 그대로).

## 컨텍스트
- 기존 `User`(users), `UserProfile`(user_profiles) 모델이 `backend/app/models.py`에 있다. **user_profiles는 절대 수정하지 말 것** — 신규 테이블로 분리한다.
- 컬럼 사양 (plan.md "도메인 사양" 참조, 아래 포함 필수):
  - id PK, user_id FK→users.id UNIQUE NOT NULL (ondelete CASCADE)
  - music_genres TEXT[] (server_default "{}"), favorite_artists TEXT[], preferred_music_mood TEXT[]
  - mbti TEXT NULL, ideal_type TEXT NULL
  - personality_keywords TEXT[], movie_genres TEXT[], food_preferences TEXT[], life_values TEXT[]
  - weekend_style TEXT NULL, love_language TEXT NULL
  - answers JSONB NULL
  - completed BOOL NOT NULL server_default "false"
  - created_at, updated_at (DateTime(timezone=True), server_default func.now(), updated_at에 onupdate=func.now())
- 배열 컬럼은 `nullable=False, server_default="{}"` 로 (기존 UserProfile.hobbies 패턴 동일).
- 마이그레이션의 배열 컬럼 server_default는 `sa.text("'{}'::text[]")` 형태로 안전하게 작성.
- 마이그레이션은 upgrade()에서 create_table, downgrade()에서 drop_table.

## 기존 단위 테스트 (참조)
- backend/tests/unit/test_plan_models.py (모델 정의 테스트 패턴 참고)
관련 기존 테스트: 위 1건 외 없음.

## 금지 사항
- user_profiles, users 등 기존 테이블/모델 수정 금지.
- backend/app/main.py, routers 수정 금지 (이 task 범위 아님 — 다른 task가 담당).
- alembic을 실제 DB에 적용(upgrade head 실행)하지 말 것. 파일만 작성.

## 완료 조건
- models.py에 TasteProfile 추가, 0010 마이그레이션 파일 작성.
- `cd backend && python -c "import app.models"` 무오류 import.
- `cd backend && python -m pytest tests/unit -q` 통과 (신규 모델 단위 테스트 포함).
- result.md Status: DONE.

## 자동 진행 목표 (/goal 명령 — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, backend/app/models.py에 TasteProfile 존재, 0010 마이그레이션 파일 존재, pytest tests/unit 통과. NEEDS_CONTEXT/BLOCKED 보고 시에도 종료. 최대 40턴.
```
`/goal`이 UI 전용이라 호출 불가하면, 위 조건을 완료 기준으로 삼아 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
backend/tests/unit/ (예: test_taste_models.py) — TasteProfile 컬럼/제약 정의 검증.
### 완료 시 보고
result.md에 작성한 테스트 파일과 covers 소스를 명시.

## 작업 디렉토리
C:/Users/ab550/OneDrive/Desktop/projects/proj_days

## Resume 규약 (필수)
1. 작업을 atomic 단위로 분할.
2. 매 단위 완료 시 git-commit-lock.sh로 커밋:
   ```bash
   bash ~/.claude/skills/jmh-orchestrator/scripts/git-commit-lock.sh \
     --repo "C:/Users/ab550/OneDrive/Desktop/projects/proj_days" \
     --message "task(agent-task1): 취향 모델/마이그레이션" \
     --add "backend/app/models.py backend/alembic/versions/0010_taste_profiles.py backend/tests/unit/test_taste_models.py"
   ```
3. result.md를 점진 업데이트 (시작 IN_PROGRESS, 완료 DONE).
4. 재개 시 기존 result.md와 git log 확인.

## Retrospect (필수)
작업 완료 후 작성:
  C:/Users/ab550/OneDrive/Desktop/projects/proj_days/jmh-agent-orchestration/retrospect/jmh-worker-backend-{TIMESTAMP}.md
겪은 이슈 기록 (없으면 "이슈 없음" 명시).

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task1/ 에서 task.md/result.md/question.md/answer.md로 통신.
모호하거나 차단되면 question.md 작성 후 result.md Status=NEEDS_CONTEXT로 설정하고 중단.
