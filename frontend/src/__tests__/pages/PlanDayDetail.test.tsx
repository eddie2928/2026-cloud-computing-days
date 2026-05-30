/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PlanDayDetail } from '../../pages/PlanDayDetail';
import * as plansApi from '../../api/plans';
import type { PlanWithTodosOut } from '../../lib/plans';

vi.mock('../../api/plans');

vi.mock('../../hooks/useMockDate', () => ({
  useMockDate: () => '2026-05-30',
}));

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

const basePlan: PlanWithTodosOut = {
  id: 10,
  user_id: 1,
  title: '테스트 플랜',
  description_input: null,
  goal_input: null,
  period_start: '2026-05-28',
  period_end: '2026-06-03',
  source: 'manual',
  created_at: '2026-05-28T00:00:00Z',
  progress: 0.4,
  todos: [
    { id: 1, plan_id: 10, todo_date: '2026-05-30', sequence: 1, content: '오늘 할 일', completed: false, completed_at: null },
    { id: 2, plan_id: 10, todo_date: '2026-05-29', sequence: 1, content: '어제 할 일', completed: false, completed_at: null },
  ],
};

function renderWithRoute(planId: string, date: string) {
  return render(
    <MemoryRouter initialEntries={[`/plans/${planId}/day/${date}`]}>
      <Routes>
        <Route path="/plans/:planId/day/:date" element={<PlanDayDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PlanDayDetail 페이지', () => {
  beforeEach(() => {
    vi.mocked(plansApi.getPlan).mockResolvedValue(basePlan);
    vi.mocked(plansApi.updateTodo).mockResolvedValue({
      id: 1, plan_id: 10, todo_date: '2026-05-30', sequence: 1, content: '오늘 할 일', completed: true, completed_at: '2026-05-30T10:00:00Z',
    });
    mockNavigate.mockClear();
  });

  it('오늘(today) 날짜이면 체크박스가 활성화된다', async () => {
    renderWithRoute('10', '2026-05-30');
    await waitFor(() => screen.getByText('오늘 할 일'));
    const checkboxes = screen.getAllByRole('button', { name: /완료/ });
    expect(checkboxes[0]).not.toBeDisabled();
  });

  it('다른 날짜이면 체크박스가 disabled된다', async () => {
    renderWithRoute('10', '2026-05-29');
    await waitFor(() => screen.getByText('어제 할 일'));
    const checkboxes = screen.getAllByRole('button', { name: /완료/ });
    expect(checkboxes[0]).toBeDisabled();
  });

  it('오늘 체크박스 클릭 시 updateTodo를 호출한다', async () => {
    renderWithRoute('10', '2026-05-30');
    await waitFor(() => screen.getByText('오늘 할 일'));
    fireEvent.click(screen.getByRole('button', { name: /완료 처리/ }));
    await waitFor(() => {
      expect(plansApi.updateTodo).toHaveBeenCalledWith(10, 1, { completed: true });
    });
  });

  it('해당 날짜 todo가 0개이면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(plansApi.getPlan).mockResolvedValue({ ...basePlan, todos: [] });
    renderWithRoute('10', '2026-05-30');
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  it('plan 메타 카드가 렌더링된다', async () => {
    renderWithRoute('10', '2026-05-30');
    await waitFor(() => {
      expect(screen.getByText('테스트 플랜')).toBeInTheDocument();
      expect(screen.getByText(/2026-05-28.*2026-06-03/)).toBeInTheDocument();
    });
  });

  it('"Plan 수정 페이지로" 링크가 렌더링된다', async () => {
    renderWithRoute('10', '2026-05-30');
    await waitFor(() => {
      expect(screen.getByText('Plan 수정 페이지로')).toBeInTheDocument();
    });
  });
});
