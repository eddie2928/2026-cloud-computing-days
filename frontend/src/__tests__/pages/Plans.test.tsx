/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Plans } from '../../pages/Plans';
import * as plansApi from '../../api/plans';
import type { PlanOut } from '../../lib/plans';

vi.mock('../../api/plans');

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockPlans: PlanOut[] = [
  {
    id: 1,
    user_id: 1,
    title: '테스트 플랜',
    description_input: null,
    goal_input: null,
    period_start: '2026-06-01',
    period_end: '2026-06-30',
    source: 'manual',
    created_at: '2026-06-01T00:00:00Z',
    progress: 0.5,
  },
  {
    id: 2,
    user_id: 1,
    title: '두 번째 플랜',
    description_input: null,
    goal_input: null,
    period_start: '2026-07-01',
    period_end: '2026-07-15',
    source: 'manual',
    created_at: '2026-07-01T00:00:00Z',
    progress: 0,
  },
];

describe('Plans 페이지', () => {
  beforeEach(() => {
    vi.mocked(plansApi.listPlans).mockResolvedValue(mockPlans);
    mockNavigate.mockClear();
  });

  it('plans 목록을 렌더링한다', async () => {
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText('테스트 플랜')).toBeInTheDocument();
      expect(screen.getByText('두 번째 플랜')).toBeInTheDocument();
    });
  });

  it('plans가 없으면 빈 상태 메시지를 표시한다', async () => {
    vi.mocked(plansApi.listPlans).mockResolvedValue([]);
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/아직 만든 Plan이 없어요/)).toBeInTheDocument();
    });
  });

  it('카드 클릭 시 /plans/:id 로 이동한다', async () => {
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => screen.getByText('테스트 플랜'));
    fireEvent.click(screen.getAllByTestId('plan-card')[0]);
    expect(mockNavigate).toHaveBeenCalledWith('/plans/1');
  });

  it('"+ Plan 추가" 버튼이 렌더링된다', async () => {
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => {
      expect(screen.getByText(/\+ Plan 추가/)).toBeInTheDocument();
    });
  });

  it('"+ Plan 추가" 버튼 클릭 시 /plans/new 로 이동한다', async () => {
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => screen.getByText(/\+ Plan 추가/));
    fireEvent.click(screen.getByText(/\+ Plan 추가/));
    expect(mockNavigate).toHaveBeenCalledWith('/plans/new');
  });

  it('빈 상태에서 "새 Plan 만들기" 버튼 클릭 시 /plans/new 로 이동한다', async () => {
    vi.mocked(plansApi.listPlans).mockResolvedValue([]);
    render(<MemoryRouter><Plans /></MemoryRouter>);
    await waitFor(() => screen.getByText('새 Plan 만들기'));
    fireEvent.click(screen.getByText('새 Plan 만들기'));
    expect(mockNavigate).toHaveBeenCalledWith('/plans/new');
  });
});
