/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MonthGrid } from '../../../components/calendar/MonthGrid';
import type { ScheduleItem } from '../../../lib/week';
import type { PlanWithTodosOut } from '../../../lib/plans';

const noop = () => {};

function makeSchedule(
  id: number,
  start: string,
  end: string,
  situation: string,
  startTime?: string,
): ScheduleItem {
  return { id, period_start: start, period_end: end, situation, start_time: startTime ?? null };
}

function renderGrid(
  schedules: ScheduleItem[] = [],
  plans: PlanWithTodosOut[] = [],
) {
  return render(
    <MemoryRouter>
      <MonthGrid
        year={2026}
        month={5}
        entries={[]}
        schedules={schedules}
        holidays={[]}
        plans={plans}
        onPrev={noop}
        onNext={noop}
        onCellClick={noop}
      />
    </MemoryRouter>,
  );
}

describe('MonthGrid — cells & overflow', () => {
  it('MAX_BARS(2) 초과 시 해당 일자 칩에 숨김 카운트가 표시된다', () => {
    // 4 schedules → rowIndex 0,1 visible, rowIndex 2,3 hidden
    const schedules = [
      makeSchedule(1, '2026-05-01', '2026-05-01', '일정A'),
      makeSchedule(2, '2026-05-01', '2026-05-01', '일정B'),
      makeSchedule(3, '2026-05-01', '2026-05-01', '일정C'),
      makeSchedule(4, '2026-05-01', '2026-05-01', '일정D'),
    ];
    renderGrid(schedules);
    const chip = document.querySelector('[data-overflow-date="2026-05-01"]');
    expect(chip).not.toBeNull();
    expect(chip!.textContent).toMatch(/\+2/);
  });

  it('멀티데이 일정이 단일일 일정보다 낮은 gridRow(위쪽 슬롯)에 배치된다', () => {
    // Both schedules start on May 1 — they're in the same week row
    const schedules = [
      makeSchedule(1, '2026-05-01', '2026-05-01', '단일일'),   // single-day
      makeSchedule(2, '2026-05-01', '2026-05-02', '멀티데이'),  // multi-day (spans 2 days in same week)
    ];
    renderGrid(schedules);
    // Multi-day bar appears in the same week as single-day; may have multiple bars across weeks
    const multiEls = screen.getAllByTitle('멀티데이');
    const singleEl = screen.getByTitle('단일일');
    // Find the bar in the same week grid container as the single-day bar
    const multiEl = multiEls[0];
    const multiRow = parseInt(multiEl.style.gridRow);
    const singleRow = parseInt(singleEl.style.gridRow);
    // multi-day bar should have lower gridRow (= closer to top = earlier slot)
    expect(multiRow).toBeLessThan(singleRow);
  });

  it('start_time 빠른 일정이 더 낮은 gridRow(위쪽 슬롯)에 배치된다', () => {
    const schedules = [
      makeSchedule(1, '2026-05-01', '2026-05-01', '오후일정', '14:00'),
      makeSchedule(2, '2026-05-01', '2026-05-01', '오전일정', '09:00'),
    ];
    renderGrid(schedules);
    const morningEl = screen.getByTitle('오전일정');
    const afternoonEl = screen.getByTitle('오후일정');
    const morningRow = parseInt(morningEl.style.gridRow);
    const afternoonRow = parseInt(afternoonEl.style.gridRow);
    expect(morningRow).toBeLessThan(afternoonRow);
  });

  it('날짜 셀 버튼이 gridRow 1/-1을 가져 막대와 같은 컨테이너에 위치한다', () => {
    const schedules = [makeSchedule(1, '2026-05-01', '2026-05-01', '테스트일정')];
    renderGrid(schedules);
    // The cell button for May 1 should span all rows
    const cellBtn = screen.getByRole('button', { name: '2026-05-01' });
    expect(cellBtn.style.gridRow).toBe('1 / -1');
    // The schedule bar should also be in the grid (existence check)
    const barBtn = screen.getByTitle('테스트일정');
    expect(barBtn).toBeInTheDocument();
  });
});

const plan: PlanWithTodosOut = {
  id: 99,
  user_id: 1,
  title: '테스트플랜',
  description_input: null,
  goal_input: null,
  period_start: '2026-05-05',
  period_end: '2026-05-05',
  source: 'manual',
  created_at: '2026-05-05T00:00:00Z',
  progress: 0,
  todos: [],
};

describe('MonthGrid — mode prop', () => {
  it('mode="schedule"이면 plan-bar-* 가 렌더링되지 않는다', () => {
    const schedule = makeSchedule(1, '2026-05-05', '2026-05-05', '회의');
    render(
      <MemoryRouter>
        <MonthGrid
          year={2026} month={5} entries={[]} holidays={[]}
          schedules={[schedule]} plans={[plan]}
          mode="schedule"
          onPrev={noop} onNext={noop} onCellClick={noop}
        />
      </MemoryRouter>,
    );
    expect(screen.queryAllByTestId(/plan-bar-99/)).toHaveLength(0);
    expect(screen.getByTitle('회의')).toBeInTheDocument();
  });

  it('mode="plan"이면 schedule 바가 렌더링되지 않는다', () => {
    const schedule = makeSchedule(1, '2026-05-05', '2026-05-05', '회의');
    render(
      <MemoryRouter>
        <MonthGrid
          year={2026} month={5} entries={[]} holidays={[]}
          schedules={[schedule]} plans={[plan]}
          mode="plan"
          onPrev={noop} onNext={noop} onCellClick={noop}
        />
      </MemoryRouter>,
    );
    expect(screen.queryByTitle('회의')).toBeNull();
    expect(screen.getAllByTestId(/plan-bar-99/)).not.toHaveLength(0);
  });

  it('일정 바 텍스트에 start_time이 포함되지 않는다', () => {
    const schedule = makeSchedule(1, '2026-05-05', '2026-05-05', '회의', '09:00');
    renderGrid([schedule]);
    const bar = screen.getByTitle('회의');
    expect(bar.textContent).toBe('회의');
    expect(bar.textContent).not.toContain('09:00');
  });
});
