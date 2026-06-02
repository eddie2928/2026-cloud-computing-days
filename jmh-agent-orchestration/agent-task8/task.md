# Task: 프론트 E2E/빌드 검증 (tsc --noEmit + vitest)

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-frontend
필요 시 days-design 스킬도 참조.
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE (통합/E2E 검증)

## 목표
Task 6(취향 문진)·Task 7(Admin 음악 탭) 합류점에서 프론트엔드 전체 정합성을 검증한다.
- `cd frontend && npx tsc --noEmit` 가 **무오류**여야 한다. 타입 오류가 있으면 원인을 분석해 최소 수정한다(신규 코드 한정).
- `cd frontend && npm test -- --run` 전체 통과여야 한다.
- 스모크 렌더 통합 테스트 추가 (없으면 보강):
  - TasteSurvey 페이지: 첫 단계 렌더 + 다음 단계 진행 + 저장(PUT) 호출 mock 확인.
  - Admin music 탭: 탭 전환 → 검색 호출 mock → 결과/실패 표시.
  - 라우팅: `/profile/taste` 가 App.tsx에 등록되어 렌더되는지 (MemoryRouter 스모크).
- 발견된 회귀(기존 테스트 깨짐)도 신규 변경 범위 내에서 수정.

## 컨텍스트
- Task 6 산출: pages/TasteSurvey.tsx, api/taste.ts, lib/taste.ts, App.tsx 라우트, Profile.tsx 취향 섹션.
- Task 7 산출: Admin.tsx music 탭, api/music.ts.
- 기존 vitest 설정/테스트 유틸을 따른다. axios/client mock 방식은 기존 테스트 파일 참고.

## 기존 단위 테스트 (참조)
- frontend/src/**/*.test.tsx 전체 (Task6/Task7가 작성한 테스트 포함).

## 금지 사항
- backend/ 수정 금지. 기능 로직 대규모 변경 금지 — 타입/테스트 정합성 위주 최소 수정.
- 실제 외부 네트워크 호출 테스트 금지(mock).

## 완료 조건
- `cd frontend && npx tsc --noEmit` 무오류, `cd frontend && npm test -- --run` 전체 통과.
- result.md Status: DONE (회귀/결함은 DONE_WITH_CONCERNS로 상세 기록 가능).

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, tsc --noEmit 무오류, npm test --run 전체 통과, 스모크 통합 테스트 존재. NEEDS_CONTEXT/BLOCKED/DONE_WITH_CONCERNS 시에도 종료. 최대 50턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
frontend/src/ 내 통합 스모크 테스트 (TasteSurvey, Admin music, 라우팅).
### 완료 시 보고
result.md에 작성/수정한 테스트 파일과 covers 명시 + tsc/vitest 최종 출력 요약.

## 작업 디렉토리
C:/Users/ab550/OneDrive/Desktop/projects/proj_days

## Resume 규약 (필수)
1. atomic 단위 분할.
2. 매 단위 git-commit-lock.sh로 커밋:
   ```bash
   bash ~/.claude/skills/jmh-orchestrator/scripts/git-commit-lock.sh \
     --repo "C:/Users/ab550/OneDrive/Desktop/projects/proj_days" \
     --message "task(agent-task8): 프론트 E2E/빌드 검증" \
     --add "frontend/src"
   ```
3. result.md 점진 업데이트.
4. 재개 시 result.md/git log 확인.

## Retrospect (필수)
완료 후: jmh-agent-orchestration/retrospect/jmh-worker-frontend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task8/ 에서 통신. 차단 시 question.md + Status=NEEDS_CONTEXT 후 중단.
