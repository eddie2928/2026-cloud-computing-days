# Reusable Test Assets

이 디렉토리의 테스트는 프로젝트 내 다른 기능 구현 시 참고/재사용할 수 있는 테스트입니다.

## 목록
- `test_calendar_timezone.py` — KST timezone 변환 로직 검증 패턴 (출처: CalendarEntry written_date 필드 추가, 2026-05-28)
  - `test_calendar_kst_midnight_boundary`: UTC 15:30 = KST 자정 경계 검증
  - `test_calendar_written_date_same_day`: db_session.commit()으로 created_at 직접 조작 후 API 응답 검증 패턴
