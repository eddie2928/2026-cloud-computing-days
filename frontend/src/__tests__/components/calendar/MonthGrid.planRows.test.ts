import { describe, it, expect } from 'vitest';
import { computePlanRowByDate } from '../../../components/calendar/planRowUtils';
import type { PlanWithTodosOut } from '../../../lib/plans';

function makePlan(id: number, start: string, end: string): PlanWithTodosOut {
  return {
    id,
    user_id: 1,
    title: `Plan ${id}`,
    description_input: '',
    goal_input: '',
    period_start: start,
    period_end: end,
    source: 'ai',
    created_at: '2026-01-01T00:00:00Z',
    progress: 0,
    todos: [],
  };
}

describe('computePlanRowByDate', () => {
  const A = makePlan(1, '2026-06-01', '2026-06-10');
  const B = makePlan(2, '2026-06-02', '2026-06-04');
  const C = makePlan(3, '2026-06-03', '2026-06-10');

  const dates = [
    '2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04',
    '2026-06-05', '2026-06-10', '2026-06-11',
  ];

  it('6/1: A만 활성 → A=row0', () => {
    const result = computePlanRowByDate(['2026-06-01'], [A, B, C]);
    expect(result.get('2026-06-01')?.get(A.id)).toBe(0);
    expect(result.get('2026-06-01')?.get(B.id)).toBeUndefined();
  });

  it('6/2: A,B 활성 → A=0, B=1', () => {
    const result = computePlanRowByDate(['2026-06-02'], [A, B, C]);
    const day = result.get('2026-06-02')!;
    expect(day.get(A.id)).toBe(0);
    expect(day.get(B.id)).toBe(1);
  });

  it('6/3: A,B,C 활성 → A=0, B=1, C=2', () => {
    const result = computePlanRowByDate(['2026-06-03'], [A, B, C]);
    const day = result.get('2026-06-03')!;
    expect(day.get(A.id)).toBe(0);
    expect(day.get(B.id)).toBe(1);
    expect(day.get(C.id)).toBe(2);
  });

  it('6/5: A,C 활성 → A=0, C=1 (B 끝나도 빈 줄 없음)', () => {
    const result = computePlanRowByDate(['2026-06-05'], [A, B, C]);
    const day = result.get('2026-06-05')!;
    expect(day.get(A.id)).toBe(0);
    expect(day.get(B.id)).toBeUndefined();
    expect(day.get(C.id)).toBe(1);
  });

  it('6/10: A,C 활성 → A=0, C=1', () => {
    const result = computePlanRowByDate(['2026-06-10'], [A, B, C]);
    const day = result.get('2026-06-10')!;
    expect(day.get(A.id)).toBe(0);
    expect(day.get(C.id)).toBe(1);
  });

  it('6/11: 활성 없음 → 빈 맵', () => {
    const result = computePlanRowByDate(['2026-06-11'], [A, B, C]);
    const day = result.get('2026-06-11');
    expect(day?.size ?? 0).toBe(0);
  });

  it('복수 날짜 한 번에 계산', () => {
    const result = computePlanRowByDate(dates, [A, B, C]);
    // 6/5에 C가 row1
    expect(result.get('2026-06-05')?.get(C.id)).toBe(1);
    // 6/11에 아무것도 없음
    expect(result.get('2026-06-11')?.size ?? 0).toBe(0);
  });

  it('동일 시작일: end asc 정렬 → D(끝6/2)=0, E(끝6/9)=1', () => {
    const D = makePlan(5, '2026-06-01', '2026-06-02');
    const E = makePlan(3, '2026-06-01', '2026-06-09');
    const result = computePlanRowByDate(['2026-06-01'], [D, E]);
    const day = result.get('2026-06-01')!;
    expect(day.get(D.id)).toBe(0);
    expect(day.get(E.id)).toBe(1);
  });

  it('동일 시작/종료일: id asc 정렬', () => {
    const X = makePlan(10, '2026-06-01', '2026-06-05');
    const Y = makePlan(5, '2026-06-01', '2026-06-05');
    const result = computePlanRowByDate(['2026-06-01'], [X, Y]);
    const day = result.get('2026-06-01')!;
    expect(day.get(Y.id)).toBe(0); // id=5 먼저
    expect(day.get(X.id)).toBe(1); // id=10 다음
  });

  it('단일 일자 플랜 단독 → row0', () => {
    const F = makePlan(7, '2026-06-05', '2026-06-05');
    const result = computePlanRowByDate(['2026-06-05'], [F]);
    expect(result.get('2026-06-05')?.get(F.id)).toBe(0);
  });
});
