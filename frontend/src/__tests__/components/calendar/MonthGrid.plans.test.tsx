/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MonthGrid } from '../../../components/calendar/MonthGrid';
import type { PlanWithTodosOut } from '../../../lib/plans';

const noop = () => {};

const plan: PlanWithTodosOut = {
  id: 7,
  user_id: 1,
  title: '독서 플랜',
  description_input: null,
  goal_input: null,
  period_start: '2026-05-11',
  period_end: '2026-05-17',
  source: 'manual',
  created_at: '2026-05-11T00:00:00Z',
  progress: 0.2,
  todos: [],
};

function renderGrid(onPlanDayClick?: (planId: number, date: string) => void) {
  return render(
    <MemoryRouter>
      <MonthGrid
        year={2026}
        month={5}
        entries={[]}
        schedules={[]}
        holidays={[]}
        plans={[plan]}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
        onPlanDayClick={onPlanDayClick}
      />
    </MemoryRouter>,
  );
}

describe('MonthGrid — plans prop', () => {
  it('plans가 전달되면 plan 바 세그먼트가 렌더링된다', () => {
    renderGrid(noop);
    // May 11 is within the plan range — at least one segment should be rendered
    const segments = screen.getAllByTestId(/plan-bar-7-2026-05/);
    expect(segments.length).toBeGreaterThan(0);
  });

  it('plan 이름이 첫 번째 세그먼트의 텍스트에 표시된다', () => {
    renderGrid(noop);
    // All segments have title attribute; the first in each week shows visible text
    const titledSegments = screen.getAllByTitle('독서 플랜');
    expect(titledSegments.length).toBeGreaterThan(0);
    // At least one segment contains visible text (isFirstInWeek)
    const withText = titledSegments.find((el) => el.textContent && el.textContent.length > 0);
    expect(withText).toBeDefined();
  });

  it('plan 세그먼트 클릭 시 onPlanDayClick 콜백이 호출된다', () => {
    const handler = vi.fn();
    renderGrid(handler);
    const segments = screen.getAllByTestId(/plan-bar-7-2026-05/);
    fireEvent.click(segments[0]);
    expect(handler).toHaveBeenCalledOnce();
    const [calledPlanId, calledDate] = handler.mock.calls[0];
    expect(calledPlanId).toBe(7);
    expect(calledDate).toMatch(/^2026-05-/);
  });

  it('period_start 세그먼트(2026-05-11)에 좌측 borderRadius가 적용된다', () => {
    renderGrid(noop);
    const seg = screen.getByTestId('plan-bar-7-2026-05-11');
    expect(seg.style.borderRadius).toBe('9px 0px 0px 9px');
  });

  it('period_end 세그먼트(2026-05-17)에 우측 borderRadius가 적용된다', () => {
    renderGrid(noop);
    const seg = screen.getByTestId('plan-bar-7-2026-05-17');
    expect(seg.style.borderRadius).toBe('0px 9px 9px 0px');
  });

  it('중간 세그먼트(2026-05-12)는 borderRadius가 없다', () => {
    renderGrid(noop);
    const seg = screen.getByTestId('plan-bar-7-2026-05-12');
    // borderRadius가 없거나 0px 0px 0px 0px
    const r = seg.style.borderRadius;
    expect(r === '' || r === '0px 0px 0px 0px' || r === '0px').toBe(true);
  });

  it('period_end 세그먼트는 점선 borderRight가 없다', () => {
    renderGrid(noop);
    const seg = screen.getByTestId('plan-bar-7-2026-05-17');
    expect(seg.style.borderRight).not.toContain('dashed');
  });

  it('중간 세그먼트는 점선 borderRight를 유지한다', () => {
    renderGrid(noop);
    const seg = screen.getByTestId('plan-bar-7-2026-05-12');
    expect(seg.style.borderRight).toContain('dashed');
  });

  it('plans prop 없이도 정상 렌더링된다', () => {
    render(
      <MemoryRouter>
        <MonthGrid
          year={2026}
          month={5}
          entries={[]}
          schedules={[]}
          holidays={[]}
          onPrev={noop}
          onNext={noop}
          onCellClick={noop}
        />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('month-grid')).toBeInTheDocument();
  });
});
