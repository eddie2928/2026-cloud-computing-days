/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import PlanMiniCalendar from '../../../components/plans/PlanMiniCalendar';
import type { PlanWithTodosOut } from '../../../lib/plans';

const TODAY = '2026-05-05';

function makePlan(overrides: Partial<PlanWithTodosOut> = {}): PlanWithTodosOut {
  return {
    id: 1,
    user_id: 1,
    title: '테스트 플랜',
    description_input: null,
    goal_input: null,
    period_start: '2026-05-01',
    period_end: '2026-05-10',
    source: 'manual',
    created_at: '2026-05-01T00:00:00Z',
    progress: 0,
    todos: [
      // 2026-05-01: 2 todos, 1 done → "1/2"
      { id: 1, plan_id: 1, todo_date: '2026-05-01', sequence: 1, content: 'a', completed: true, completed_at: null },
      { id: 2, plan_id: 1, todo_date: '2026-05-01', sequence: 2, content: 'b', completed: false, completed_at: null },
      // 2026-05-03: 2 todos, both done → "2/2" (100%)
      { id: 3, plan_id: 1, todo_date: '2026-05-03', sequence: 1, content: 'c', completed: true, completed_at: null },
      { id: 4, plan_id: 1, todo_date: '2026-05-03', sequence: 2, content: 'd', completed: true, completed_at: null },
      // 2026-05-07: future, 1 todo → "0/1"
      { id: 5, plan_id: 1, todo_date: '2026-05-07', sequence: 1, content: 'e', completed: false, completed_at: null },
    ],
    ...overrides,
  };
}

describe('PlanMiniCalendar', () => {
  it('renders 완료/전체 fraction for all dates in plan period', () => {
    const { getByTestId } = render(
      <PlanMiniCalendar plan={makePlan()} todayStr={TODAY} onSelectDate={vi.fn()} />,
    );

    // 2026-05-01: 1 done / 2 total
    const cell01 = getByTestId('cell-2026-05-01');
    expect(cell01.textContent).toContain('1/2');

    // 2026-05-03: 2/2
    const cell03 = getByTestId('cell-2026-05-03');
    expect(cell03.textContent).toContain('2/2');

    // 2026-05-02: 0 todos → "0/0"
    const cell02 = getByTestId('cell-2026-05-02');
    expect(cell02.textContent).toContain('0/0');

    // 2026-05-07: future, still shows fraction
    const cell07 = getByTestId('cell-2026-05-07');
    expect(cell07.textContent).toContain('0/1');
  });

  it('does NOT call onSelectDate when a future cell is clicked', () => {
    const onSelectDate = vi.fn();
    const { getByTestId } = render(
      <PlanMiniCalendar plan={makePlan()} todayStr={TODAY} onSelectDate={onSelectDate} />,
    );

    // 2026-05-07 is future (> TODAY 2026-05-05)
    fireEvent.click(getByTestId('cell-2026-05-07'));
    expect(onSelectDate).not.toHaveBeenCalled();
  });

  it('calls onSelectDate(date) when a past cell is clicked', () => {
    const onSelectDate = vi.fn();
    const { getByTestId } = render(
      <PlanMiniCalendar plan={makePlan()} todayStr={TODAY} onSelectDate={onSelectDate} />,
    );

    // 2026-05-01 is past
    fireEvent.click(getByTestId('cell-2026-05-01'));
    expect(onSelectDate).toHaveBeenCalledWith('2026-05-01');
  });

  it('100% done cell has sage-wash background style', () => {
    const { getByTestId } = render(
      <PlanMiniCalendar plan={makePlan()} todayStr={TODAY} onSelectDate={vi.fn()} />,
    );

    // 2026-05-03 is 100% done
    const cell = getByTestId('cell-2026-05-03');
    expect(cell.style.background).toBe('var(--sage-wash)');
  });

  it('prev button is disabled when already at the start month', () => {
    const { getByLabelText } = render(
      <PlanMiniCalendar plan={makePlan()} todayStr={TODAY} onSelectDate={vi.fn()} />,
    );

    const prevBtn = getByLabelText('이전 달');
    expect(prevBtn).toBeDisabled();
  });
});
