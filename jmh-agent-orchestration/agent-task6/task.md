# Task: 취향 문진 플로우 페이지 + 라우트 + Profile 진입/요약

## Skill 로딩 (필수 — 가장 먼저 수행)
반드시 다음 스킬을 invoke하라: /jmh-worker-frontend
그리고 UI 작업이므로 **days-design 스킬도 반드시 invoke**하여 디자인 토큰을 준수하라.
Skill invoke 없이 작업을 시작하지 마라.

## 작업 유형
NEW_FEATURE

## 목표
사용자 상세 취향을 **단계별 문진 플로우**(온보딩 스타일 카드 진행)로 수집/저장하는 UI를 만든다.
- 신규 페이지 `frontend/src/pages/TasteSurvey.tsx`:
  - 여러 단계(카드)로 한 화면에 한 질문씩 진행. 진행률 표시(기존 ProgressBar 컴포넌트 활용 가능). 뒤로/다음.
  - 문항(아래 필드에 매핑, days-design 톤의 한국어 질문):
    - 좋아하는 노래 장르 (다중 선택 칩 + 직접입력) → music_genres
    - 좋아하는 아티스트 (TagInput) → favorite_artists
    - 선호 음악 분위기 (다중 선택: 잔잔한/신나는/감성적인/집중되는 등) → preferred_music_mood
    - MBTI (16개 중 택1 또는 모름) → mbti
    - 이상형 (자유 서술 텍스트) → ideal_type
    - 성격 키워드 (TagInput/칩) → personality_keywords
    - 좋아하는 영화·콘텐츠 장르 (칩) → movie_genres
    - 음식 취향 (TagInput) → food_preferences
    - 주말 성향 (집순이/밖순이 등 택1 또는 서술) → weekend_style
    - 중요하게 여기는 가치 (다중 선택/Tag) → life_values
    - 애정표현 방식 (택1/서술) → love_language
  - 마지막 단계에서 PUT 저장 → 저장 성공 시 /profile로 이동, completed=true 포함.
  - 기존 응답이 있으면(GET 200) 초기값으로 채워 재진행 가능.
- 라우트 `/profile/taste`를 `frontend/src/App.tsx`에 등록 (ProtectedRoute + AppLayout, 기존 패턴과 동일).
- `frontend/src/pages/Profile.tsx`에 "취향" SectionCard 추가:
  - 취향 요약(장르/MBTI 등 일부) 표시 + "취향 문진하기/수정하기" 버튼 → navigate('/profile/taste').
  - GET /api/taste-profile 404면 "아직 작성 안 함" + 시작 버튼.
- API/lib:
  - `frontend/src/api/taste.ts`: `getTasteProfile()`, `putTasteProfile(payload)` (기존 api/client 사용, api/plans.ts 패턴 참고).
  - `frontend/src/lib/taste.ts`: 장르/분위기/MBTI/가치 옵션 상수, 빈 폼 기본값.

## 컨텍스트
- **백엔드 API는 Task 2가 구현 완료**: `GET /api/taste-profile`(404 가능), `PUT /api/taste-profile`(upsert). 필드는 plan.md 도메인 사양 및 backend/app/schemas.py의 TasteProfileIn 참고 — 백엔드 스키마와 필드명을 정확히 일치시켜라(가능하면 backend/app/schemas.py를 읽어 확인).
- 기존 컴포넌트 재사용: `components/days/`의 Chip(segment/선택), TagInput, BoxInput, PillButton, FieldLabel, ScreenContainer 등. Profile.tsx / Onboarding.tsx의 구조를 모델로 삼아라.
- 디자인: days-design 스킬 토큰(--sage-*, --paper-*, --font-sans 등)만 사용. 인라인 스타일 허용(기존 코드 동일).
- api/client는 `import client from '../api/client'`. baseURL이 이미 `/api`인지 client.ts를 확인하고 경로 맞춰라(기존 호출은 `client.get('/profile')` 형태 = baseURL에 /api 포함).

## 기존 단위 테스트 (참조)
- frontend의 PlanEdit 관련 *.test.tsx (vitest 패턴), 기타 src 내 테스트 파일.
관련 기존 테스트: 취향 관련 없음 (신규).

## 금지 사항
- Admin.tsx 수정 금지 (Task 7 담당). backend/ 디렉토리 수정 금지.
- 백엔드 스키마와 다른 필드명 임의 생성 금지.

## 완료 조건
- TasteSurvey.tsx, api/taste.ts, lib/taste.ts 생성, App.tsx 라우트 등록, Profile.tsx 취향 섹션 추가.
- `cd frontend && npx tsc --noEmit` 무오류.
- `cd frontend && npm test -- --run` 통과 (신규 테스트 포함).
- result.md Status: DONE.

## 자동 진행 목표 (/goal — 작업 시작 시 즉시 호출)
```
/goal result.md Status=DONE, TasteSurvey.tsx + api/taste.ts + lib/taste.ts 생성, App.tsx에 /profile/taste 라우트, Profile.tsx 취향 섹션, tsc --noEmit 무오류, vitest 통과. NEEDS_CONTEXT/BLOCKED 시에도 종료. 최대 60턴.
```
`/goal`이 UI 전용이라 호출 불가하면 위 조건을 완료 기준으로 진행하라.

## 단위 테스트 (필수)
### 테스트 디렉토리
frontend/src/pages/TasteSurvey.test.tsx (또는 인접) — 단계 진행/필드 입력/저장 호출 mock 스모크. lib/taste 직렬화 테스트.
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
     --message "task(agent-task6): 취향 문진 플로우" \
     --add "frontend/src/pages/TasteSurvey.tsx frontend/src/api/taste.ts frontend/src/lib/taste.ts frontend/src/App.tsx frontend/src/pages/Profile.tsx"
   ```
3. result.md 점진 업데이트.
4. 재개 시 result.md/git log 확인.

## Retrospect (필수)
완료 후: jmh-agent-orchestration/retrospect/jmh-worker-frontend-{TIMESTAMP}.md

## 통신 디렉토리 규약
jmh-agent-orchestration/agent-task6/ 에서 통신. 차단 시 question.md + Status=NEEDS_CONTEXT 후 중단.
