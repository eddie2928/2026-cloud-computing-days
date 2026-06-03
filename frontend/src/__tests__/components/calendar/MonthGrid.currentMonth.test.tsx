/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MonthGrid } from '../../../components/calendar/MonthGrid';
import type { PlanWithTodosOut } from '../../../lib/plans';

// 2026-06: 6월 1일 = 월요일(1), leading 1칸(5/31), trailing 11칸(7/1~11)
// Week 0: 5/31, 6/1~6   (5/31 = out-of-month)
// Week 1: 6/7~6/13
// Week 2: 6/14~6/20
// Week 3: 6/21~6/27
// Week 4: 6/28~7/4      (7/1~4 = out-of-month)
// Week 5: 7/5~7/11      → 전부 out-of-month → 행 제거 대상

const noop = vi.fn();

function renderJune(plans?: PlanWithTodosOut[]) {
  return render(
    <MemoryRouter>
      <MonthGrid
        year={2026}
        month={6}
        entries={[]}
        schedules={[]}
        holidays={[]}
        plans={plans ?? []}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />
    </MemoryRouter>,
  );
}

describe('MonthGrid — 현재 달만 표시 (2026-06)', () => {
  it('1. in-month 칸(6/15)은 렌더된다', () => {
    renderJune();
    expect(screen.getByLabelText('2026-06-15')).toBeInTheDocument();
  });

  it('2. leading 다른 달 칸(5/31)은 버튼으로 렌더되지 않는다', () => {
    renderJune();
    expect(screen.queryByLabelText('2026-05-31')).toBeNull();
  });

  it('3. trailing 다른 달 칸(7/1)은 버튼으로 렌더되지 않는다', () => {
    renderJune();
    expect(screen.queryByLabelText('2026-07-01')).toBeNull();
  });

  it('4. 전부 다음 달인 마지막 주 칸(7/5)은 렌더되지 않는다', () => {
    renderJune();
    expect(screen.queryByLabelText('2026-07-05')).toBeNull();
  });

  it('5. week-5(전부 7월)는 렌더되지 않고 week-0은 존재한다', () => {
    renderJune();
    expect(screen.queryByTestId('week-5')).toBeNull();
    expect(screen.getByTestId('week-0')).toBeInTheDocument();
  });

  it('6. week-0의 gridTemplateRows는 HEADER_H=60px로 시작한다', () => {
    renderJune();
    const week0 = screen.getByTestId('week-0');
    expect(week0.style.gridTemplateRows).toMatch(/^60px/);
  });

  it('7. 월 경계 플랜(6/29~7/3): in-month 날짜는 바 존재, out-of-month 날짜는 바 없음', () => {
    const crossMonthPlan: PlanWithTodosOut = {
      id: 99,
      user_id: 1,
      title: '경계 플랜',
      description_input: null,
      goal_input: null,
      period_start: '2026-06-29',
      period_end: '2026-07-03',
      source: 'manual',
      created_at: '2026-06-29T00:00:00Z',
      progress: 0,
      todos: [],
    };
    renderJune([crossMonthPlan]);
    expect(screen.getByTestId('plan-bar-99-2026-06-29')).toBeInTheDocument();
    expect(screen.queryByTestId('plan-bar-99-2026-07-01')).toBeNull();
  });
});
