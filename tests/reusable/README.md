# Reusable Test Assets

이 디렉토리의 테스트는 프로젝트 내 다른 기능 구현 시 참고/재사용할 수 있는 테스트입니다.

## 목록
- `test_plan_models.py` — SQLAlchemy 모델 컬럼/제약 존재 확인 + Pydantic 스키마 default/optional 필드 검증 패턴 (출처: T01 Plan+PlanTodo 모델·스키마, 2026-05-29)
- `test_recommend_stub.py` — 결정론적 stub 함수의 결정론성·폴백·limit·응답 구조·meta.source 검증 패턴. AI 연동 교체 시 인터페이스 계약 검증으로 재사용 가능 (출처: agent-task3 추천 Stub, 2026-06-02)
