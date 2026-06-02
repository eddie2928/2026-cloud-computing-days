# Task: 백엔드 통합 테스트 (취향 CRUD + 추천 stub + 음원 프록시)

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-backend
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE (통합 테스트)

## 목표
Task 2(취향 API), Task 3(추천 stub), Task 4(음원 프록시)의 합류점 통합 테스트를 작성한다.
- `backend/tests/integration/test_taste_profile.py`:
  - PUT으로 취향 upsert → GET으로 동일 데이터 조회 (배열/JSONB 포함 라운드트립).
  - 미작성 사용자 GET → 404.
  - 미인증 요청 → 401 (require_session).
  - 부분 업데이트/재 upsert 동작, 경계값(빈 배열, None mbti) 확인.
- `backend/tests/integration/test_recommend.py`:
  - 취향 있는 사용자 → /api/recommend/songs 가 items 반환, 결정론성(2회 호출 동일).
  - 취향 없는 사용자 → 빈 items + 안내 meta, 200.
  - 미인증 → 401.
- `backend/tests/integration/test_music_proxy.py`:
  - httpx 외부 호출을 monkeypatch하여 가짜 iTunes 응답 주입 → /api/music/search 정규화 결과(ok:true, results 매핑) 검증.
  - 외부 실패(타임아웃/비200) → ok:false + error, HTTP 200.
  - term 누락 → 4xx. 미인증 → 401.
  - **실제 네트워크 호출 절대 금지** (전부 mock).

## 컨텍스트
- 통합 테스트 인증/DB fixture는 기존 `backend/conftest.py`, `backend/tests/integration/test_profile.py`, `test_qna_full_cycle.py` 패턴을 그대로 따른다 (인증된 client fixture, 테스트 DB 세팅).
- 모델/스키마/라우터 실제 구현(models.py, schemas.py, routers/taste.py, routers/recommend.py, routers/music.py)을 먼저 읽고 필드명/응답형태에 맞춰 단언하라.
- 기존 통합 테스트 실행 방식 확인: `cd backend && python -m pytest tests/integration -q`.
- 참고: 일부 기존 테스트(test_push, test_scheduler)는 환경 의존성 누락으로 collect 에러가 날 수 있다. 본 task는 새로 작성한 3개 파일이 통과하면 된다 (`pytest tests/integration/test_taste_profile.py tests/integration/test_recommend.py tests/integration/test_music_proxy.py -q`로 타겟 실행 확인).

## 기존 단위 테스트 (참조)
- backend/tests/unit/test_taste_models.py, test_taste_router.py, test_recommend_stub.py, test_music.py
- backend/tests/integration/test_profile.py (CRUD/인증 통합 패턴)

## 금지 사항
- app/ 소스 코드 수정 금지 (테스트만 작성). 만약 소스 버그를 발견하면 question.md로 보고하지 말고 result.md에 DONE_WITH_CONCERNS로 구체 기록.
- 실제 외부 네트워크 의존 테스트 금지.

## 완료 조건
- 3개 통합 테스트 파일 작성, 타겟 실행 전부 통과.
- result.md Status: DONE (또는 소스 결함 발견 시 DONE_WITH_CONCERNS + 상세).

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, test_taste_profile.py + test_recommend.py + test_music_proxy.py 작성, 타겟 pytest 통과. NEEDS_CONTEXT/BLOCKED/DONE_WITH_CONCERNS 시에도 종료. 최대 55턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
이 task 자체가 통합 테스트 작성이다. 위 3개 파일이 산출물.
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
     --message "task(agent-task5): 백엔드 통합 테스트" \
     --add "backend/tests/integration/test_taste_profile.py backend/tests/integration/test_recommend.py backend/tests/integration/test_music_proxy.py"
   ```
3. result.md 점진 업데이트.
4. 재개 시 result.md/git log 확인.

## Retrospect (필수)
완료 후: jmh-agent-orchestration/retrospect/jmh-worker-backend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task5/ 에서 통신. 차단 시 question.md + Status=NEEDS_CONTEXT 후 중단.
