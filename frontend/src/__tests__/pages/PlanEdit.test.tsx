/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PlanEdit } from '../../pages/PlanEdit';
import * as plansApi from '../../api/plans';
import type { PlanWithTodosOut } from '../../lib/plans';

vi.mock('../../api/plans');

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockPlan: PlanWithTodosOut = {
  id: 7,
  user_id: 1,
  title: '기존 플랜 제목',
  description_input: null,
  goal_input: null,
  period_start: '2026-06-01',
  period_end: '2026-06-10',
  source: 'manual',
  created_at: '2026-06-01T00:00:00Z',
  progress: 0.5,
  todos: [
    { id: 1, plan_id: 7, todo_date: '2026-06-01', sequence: 1, content: '할 일 A', completed: false, completed_at: null },
    { id: 2, plan_id: 7, todo_date: '2026-06-01', sequence: 2, content: '할 일 B', completed: false, completed_at: null },
  ],
};

function renderEdit() {
  return render(
    <MemoryRouter initialEntries={['/plans/7/edit']}>
      <Routes>
        <Route path="/plans/:planId/edit" element={<PlanEdit />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PlanEdit 페이지', () => {
  beforeEach(() => {
    vi.mocked(plansApi.getPlan).mockResolvedValue(mockPlan);
    vi.mocked(plansApi.updatePlan).mockResolvedValue({
      ...mockPlan,
      todos: undefined as unknown as [],
    } as unknown as import('../../lib/plans').PlanOut);
    vi.mocked(plansApi.bulkReplaceTodos).mockResolvedValue({ ...mockPlan });
    mockNavigate.mockClear();
  });

  it('초기 렌더 시 기존 title/period/todo 채워짐', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('기존 플랜 제목')).toBeInTheDocument());

    expect(screen.getByDisplayValue('2026-06-01')).toBeInTheDocument();
    expect(screen.getByDisplayValue('2026-06-10')).toBeInTheDocument();

    // Two todo rows from period_start day
    expect(screen.getByDisplayValue('할 일 A')).toBeInTheDocument();
    expect(screen.getByDisplayValue('할 일 B')).toBeInTheDocument();
  });

  it('항목 추가 버튼 클릭 시 새 행 추가됨', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('할 일 A')).toBeInTheDocument());

    const addBtn = screen.getByText('+ 항목 추가');
    fireEvent.click(addBtn);

    // Now there should be 3 rows (todo-row-0, 1, 2)
    expect(screen.getByTestId('todo-row-2')).toBeInTheDocument();
  });

  it('행 삭제 버튼 클릭 시 해당 행 제거', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('할 일 A')).toBeInTheDocument());

    const deleteButtons = screen.getAllByLabelText('행 삭제');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => expect(screen.queryByDisplayValue('할 일 A')).not.toBeInTheDocument());
    expect(screen.getByDisplayValue('할 일 B')).toBeInTheDocument();
  });

  it('저장 클릭 시 updatePlan + bulkReplaceTodos 모두 호출', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('기존 플랜 제목')).toBeInTheDocument());

    // Change title to trigger updatePlan
    fireEvent.change(screen.getByDisplayValue('기존 플랜 제목'), { target: { value: '수정된 제목' } });

    fireEvent.click(screen.getByText('저장'));

    await waitFor(() => expect(plansApi.updatePlan).toHaveBeenCalledWith(7, expect.objectContaining({ title: '수정된 제목' })));
    expect(plansApi.bulkReplaceTodos).toHaveBeenCalledWith(7, expect.arrayContaining(['할 일 A', '할 일 B']));
  });

  it('빈 content 행은 저장 시 제거됨', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('할 일 A')).toBeInTheDocument());

    // Clear first row content
    fireEvent.change(screen.getByTestId('todo-row-0'), { target: { value: '' } });

    // Change title to ensure updatePlan is called too
    fireEvent.change(screen.getByDisplayValue('기존 플랜 제목'), { target: { value: '변경' } });

    fireEvent.click(screen.getByText('저장'));

    await waitFor(() => expect(plansApi.bulkReplaceTodos).toHaveBeenCalledWith(7, ['할 일 B']));
  });

  it('취소 클릭 시 /plans/7로 navigate', async () => {
    renderEdit();
    await waitFor(() => expect(screen.getByDisplayValue('기존 플랜 제목')).toBeInTheDocument());

    fireEvent.click(screen.getAllByText('취소')[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/plans/7');
  });
});
