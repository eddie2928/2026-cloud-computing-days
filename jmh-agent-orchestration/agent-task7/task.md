# Task: 개발자 페이지(Admin) 음악 API 테스트 탭

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-frontend
UI 작업이므로 **days-design 스킬도 반드시 invoke**하여 디자인 토큰을 준수하라.
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
개발자 페이지 `frontend/src/pages/Admin.tsx`에 무료 음원 API(iTunes, 백엔드 프록시) 통신 확인용 신규 탭을 추가한다.
- 기존 탭(`'db' | 'bedrock' | 'date' | 'push'`)에 `'music'` 추가. 탭 버튼 라벨 "음악 API".
- 음악 탭 UI:
  - 검색어(term) 입력 + limit 입력(기본 10) + "검색/통신 테스트" 버튼.
  - `GET /api/music/search?term=&limit=` 호출 (api/music.ts 경유).
  - 통신 결과 패널: `ok`(성공/실패 배지), `status_code`, `latency_ms`, `count` 표시. push 탭의 상태 패널 스타일 재사용.
  - 결과 리스트: artworkUrl100 썸네일 + trackName + artistName + collectionName + `<audio controls src={previewUrl}>` 30초 미리듣기 + trackViewUrl 링크.
  - Raw/Pretty 토글(JSON 원본). 기존 push 탭의 Raw 토글 패턴 동일.
  - 실패 시(ok:false) error 메시지 표시.
- `frontend/src/api/music.ts`: `searchMusic(term: string, limit?: number)` (api/client 사용).

## 컨텍스트
- **백엔드 프록시는 Task 4가 구현 완료**: `GET /api/music/search?term=&limit=` → `{ok, status_code, latency_ms, count, results:[{trackName, artistName, previewUrl, artworkUrl100, collectionName, trackViewUrl}]}`. 실패 시 ok:false + error. 정확한 응답 형태는 backend/app/routers/music.py를 읽어 확인하라.
- Admin.tsx의 기존 구조(탭 state, tabStyle, 각 탭 조건부 렌더)를 그대로 따른다. 인라인 스타일 + var(--*) 토큰 사용.
- api/client baseURL에 이미 `/api`가 포함되어 있으므로 `client.get('/music/search', { params: { term, limit } })` 형태.

## 기존 단위 테스트 (참조)
- frontend src 내 *.test.tsx (vitest 패턴).
관련 기존 테스트: 음악 관련 없음 (신규).

## 금지 사항
- Admin.tsx 외 페이지 수정 금지. App.tsx 수정 불필요(라우트 이미 존재). backend/ 수정 금지.
- TasteSurvey/Profile/api/taste/lib/taste 파일 건드리지 말 것 (Task 6 담당).

## 완료 조건
- Admin.tsx에 music 탭 추가, api/music.ts 생성.
- `cd frontend && npx tsc --noEmit` 무오류.
- `cd frontend && npm test -- --run` 통과.
- result.md Status: DONE.

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, Admin.tsx에 music 탭, api/music.ts 생성, tsc --noEmit 무오류, vitest 통과. NEEDS_CONTEXT/BLOCKED 시에도 종료. 최대 50턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
frontend/src/pages/Admin.music.test.tsx 또는 api/music 테스트 — 검색 호출/결과 렌더/실패 표시 mock 스모크.
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
     --message "task(agent-task7): Admin 음악 API 탭" \
     --add "frontend/src/pages/Admin.tsx frontend/src/api/music.ts"
   ```
3. result.md 점진 업데이트.
4. 재개 시 result.md/git log 확인.

## Retrospect (필수)
완료 후: jmh-agent-orchestration/retrospect/jmh-worker-frontend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task7/ 에서 통신. 차단 시 question.md + Status=NEEDS_CONTEXT 후 중단.
