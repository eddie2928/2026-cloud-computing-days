/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Calendar } from '../../pages/Calendar';

const mockNavigate = vi.hoisted(() => vi.fn());
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('../../api/client', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { entries: [], schedules: [], holidays: [] } }),
  },
}));

vi.mock('../../api/plans', () => ({
  listPlansForCalendar: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../components/calendar/MonthGrid', () => ({
  MonthGrid: () => <div data-testid="month-grid" />,
}));

describe('Calendar 페이지', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('플랜 토글 후 플랜 추가 클릭 시 /plans/new + state.from=/calendar?view=plan 전달', () => {
    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Calendar />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: '플랜' }));
    fireEvent.click(screen.getByRole('button', { name: /플랜 추가/ }));

    expect(mockNavigate).toHaveBeenCalledWith('/plans/new', {
      state: { from: '/calendar?view=plan' },
    });
  });

  it('일정 뷰(기본)에서 일정 추가 클릭 시 /schedule/new + state.from=/calendar?view=schedule 전달', () => {
    render(
      <MemoryRouter initialEntries={['/calendar']}>
        <Calendar />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /일정 추가/ }));

    expect(mockNavigate).toHaveBeenCalledWith('/schedule/new', {
      state: { from: '/calendar?view=schedule' },
    });
  });
});
