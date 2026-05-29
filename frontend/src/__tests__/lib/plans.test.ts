import { describe, it, expect } from 'vitest';
import {
  planProgressPercent,
  todosByDate,
  dateRangeInclusive,
  isSameLocalDay,
} from '../../lib/plans';
import type { PlanOut, PlanTodoOut } from '../../lib/plans';

// ── planProgressPercent ──────────────────────────────────────────────────────

describe('planProgressPercent', () => {
  const basePlan: PlanOut = {
    id: 1,
    user_id: 1,
    title: 'Test',
    description_input: null,
    goal_input: null,
    period_start: '2026-06-01',
    period_end: '2026-06-30',
    source: 'manual',
    created_at: '2026-06-01T00:00:00Z',
    progress: 0,
  };

  it('0.0 → 0', () => {
    expect(planProgressPercent({ ...basePlan, progress: 0 })).toBe(0);
  });

  it('1.0 → 100', () => {
    expect(planProgressPercent({ ...basePlan, progress: 1 })).toBe(100);
  });

  it('0.5 → 50', () => {
    expect(planProgressPercent({ ...basePlan, progress: 0.5 })).toBe(50);
  });

  it('0.456 → 46 (rounds)', () => {
    expect(planProgressPercent({ ...basePlan, progress: 0.456 })).toBe(46);
  });

  it('0.999 → 100 (rounds up)', () => {
    expect(planProgressPercent({ ...basePlan, progress: 0.999 })).toBe(100);
  });
});

// ── todosByDate ──────────────────────────────────────────────────────────────

describe('todosByDate', () => {
  const makeTodo = (id: number, date: string): PlanTodoOut => ({
    id,
    plan_id: 1,
    todo_date: date,
    sequence: id,
    content: `todo ${id}`,
    completed: false,
    completed_at: null,
  });

  it('empty array returns empty record', () => {
    expect(todosByDate([])).toEqual({});
  });

  it('single todo is grouped under its date', () => {
    const result = todosByDate([makeTodo(1, '2026-06-01')]);
    expect(result['2026-06-01']).toHaveLength(1);
    expect(result['2026-06-01'][0].id).toBe(1);
  });

  it('multiple todos on same date are grouped together', () => {
    const todos = [makeTodo(1, '2026-06-01'), makeTodo(2, '2026-06-01')];
    const result = todosByDate(todos);
    expect(result['2026-06-01']).toHaveLength(2);
  });

  it('todos on different dates produce separate keys', () => {
    const todos = [makeTodo(1, '2026-06-01'), makeTodo(2, '2026-06-02')];
    const result = todosByDate(todos);
    expect(Object.keys(result)).toHaveLength(2);
    expect(result['2026-06-01'][0].id).toBe(1);
    expect(result['2026-06-02'][0].id).toBe(2);
  });
});

// ── dateRangeInclusive ───────────────────────────────────────────────────────

describe('dateRangeInclusive', () => {
  it('same start and end returns single date', () => {
    const result = dateRangeInclusive('2026-06-01', '2026-06-01');
    expect(result).toEqual(['2026-06-01']);
  });

  it('3-day range returns 3 dates', () => {
    const result = dateRangeInclusive('2026-06-01', '2026-06-03');
    expect(result).toEqual(['2026-06-01', '2026-06-02', '2026-06-03']);
  });

  it('start after end returns empty array', () => {
    expect(dateRangeInclusive('2026-06-05', '2026-06-01')).toEqual([]);
  });

  it('spans month boundary correctly', () => {
    const result = dateRangeInclusive('2026-05-30', '2026-06-02');
    expect(result).toEqual(['2026-05-30', '2026-05-31', '2026-06-01', '2026-06-02']);
  });
});

// ── isSameLocalDay ───────────────────────────────────────────────────────────

describe('isSameLocalDay', () => {
  it('identical date strings return true', () => {
    expect(isSameLocalDay('2026-06-01', '2026-06-01')).toBe(true);
  });

  it('different dates return false', () => {
    expect(isSameLocalDay('2026-06-01', '2026-06-02')).toBe(false);
  });

  it('ISO datetime strings with same date return true', () => {
    expect(isSameLocalDay('2026-06-01T12:00:00Z', '2026-06-01T23:59:59Z')).toBe(true);
  });

  it('ISO datetime strings with different dates return false', () => {
    expect(isSameLocalDay('2026-06-01T23:59:59Z', '2026-06-02T00:00:00Z')).toBe(false);
  });
});
