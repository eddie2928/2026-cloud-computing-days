/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MonthGrid } from '../../../components/calendar/MonthGrid';
import type { PlanWithTodosOut } from '../../../lib/plans';

// 2026-06 기준: 6/1 = 월요일
// 주 구성: [5/31(일), 6/1, 6/2, 6/3, 6/4, 6/5, 6/6] / [6/7 ~ 6/13] / ...

const noop = () => {};

function makePlan(id: number, start: string, end: string): PlanWithTodosOut {
  return {
    id, user_id: 1,
    title: `Plan ${id}`,
    description_input: null, goal_input: null,
    period_start: start, period_end: end,
    source: 'manual', created_at: '2026-06-01T00:00:00Z',
    progress: 0, todos: [],
  };
}

function renderGrid(plans: PlanWithTodosOut[]) {
  return render(
    <MemoryRouter>
      <MonthGrid
        year={2026} month={6}
        entries={[]} schedules={[]} holidays={[]}
        plans={plans}
        onPrev={noop} onNext={noop} onCellClick={noop}
      />
    </MemoryRouter>,
  );
}

describe('MonthGrid — 플랜 고정 row (주 단위)', () => {
  it('한 주 내 다중일 플랜: 모든 세그먼트가 동일 gridRow (연속 막대)', () => {
    // Jun 1(Mon) ~ Jun 6(Sat) — 같은 주
    const plan = makePlan(1, '2026-06-01', '2026-06-06');
    renderGrid([plan]);
    const segs = screen.getAllByTestId(/plan-bar-1-2026-06-0[1-6]/);
    expect(segs.length).toBe(6);
    const rows = new Set(segs.map((el) => el.style.gridRow));
    expect(rows.size).toBe(1); // 모두 같은 gridRow
  });

  it('겹치는 두 플랜: 긴 쪽(id=1)이 위, 짧은 쪽(id=2)이 아래', () => {
    // A: Jun 1~6, B: Jun 2~4 — B는 A 안에 포함
    const A = makePlan(1, '2026-06-01', '2026-06-06');
    const B = makePlan(2, '2026-06-02', '2026-06-04');
    renderGrid([A, B]);

    const segA = screen.getByTestId('plan-bar-1-2026-06-03');
    const segB = screen.getByTestId('plan-bar-2-2026-06-03');
    expect(parseInt(segA.style.gridRow)).toBeLessThan(parseInt(segB.style.gridRow));
  });

  it('주 경계를 넘는 플랜: 각 주에서 일관된 gridRow (지그재그 없음)', () => {
    // Jun 1(Mon) ~ Jun 13(Sat) — 두 주에 걸침
    const plan = makePlan(1, '2026-06-01', '2026-06-13');
    renderGrid([plan]);

    // 주1 세그먼트
    const wk1 = screen.getAllByTestId(/plan-bar-1-2026-06-0[1-6]/);
    const wk1Rows = new Set(wk1.map((el) => el.style.gridRow));
    expect(wk1Rows.size).toBe(1);

    // 주2 세그먼트
    const wk2 = screen.getAllByTestId(/plan-bar-1-2026-06-(07|08|09|1[0-3])/);
    const wk2Rows = new Set(wk2.map((el) => el.style.gridRow));
    expect(wk2Rows.size).toBe(1);
  });

  it('안 겹치는 두 플랜: 같은 week에서 같은 row에 끼워 넣기', () => {
    // A: Jun 1~2, B: Jun 4~6 — 같은 주, 안 겹침
    const A = makePlan(1, '2026-06-01', '2026-06-02');
    const B = makePlan(2, '2026-06-04', '2026-06-06');
    renderGrid([A, B]);

    const segA = screen.getByTestId('plan-bar-1-2026-06-01');
    const segB = screen.getByTestId('plan-bar-2-2026-06-04');
    // 안 겹치므로 같은 row0에 배치되어야 함 (최대 패킹)
    expect(segA.style.gridRow).toBe(segB.style.gridRow);
  });

  it('짧은 플랜이 끝나도 긴 플랜의 row가 유지됨 (지그재그 없음)', () => {
    // B(Jun1~3, 짧음)과 A(Jun1~10, 김) — 기존 코드는 period_end 오름차 정렬로
    // Jun1~3에서 B=row0, A=row1이 되고 Jun4부터 A=row0으로 바뀌는 지그재그 발생.
    // 새 코드는 span 기준으로 A(span=6)가 row0을 유지해야 함.
    const A = makePlan(1, '2026-06-01', '2026-06-10');
    const B = makePlan(2, '2026-06-01', '2026-06-03');
    renderGrid([A, B]);

    // Jun2(B 아직 활성)와 Jun5(B 끝남) — A가 같은 row이어야 함
    const segA_whileB = screen.getByTestId('plan-bar-1-2026-06-02');
    const segA_afterB = screen.getByTestId('plan-bar-1-2026-06-05');
    expect(segA_whileB.style.gridRow).toBe(segA_afterB.style.gridRow);
  });
});
