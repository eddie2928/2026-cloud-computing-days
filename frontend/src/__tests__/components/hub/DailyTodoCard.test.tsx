/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DailyTodoCard } from '../../../components/hub/DailyTodoCard';

describe('DailyTodoCard', () => {
  it('renders without crashing', () => {
    render(<DailyTodoCard onClick={() => {}} planCount={3} activeTodayTodos={2} />);
    expect(screen.getByText('오늘의 계획')).toBeInTheDocument();
  });

  it('shows activeTodayTodos count when > 0', () => {
    render(<DailyTodoCard onClick={() => {}} planCount={3} activeTodayTodos={5} />);
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('할 일')).toBeInTheDocument();
  });

  it('shows empty message when activeTodayTodos is 0', () => {
    render(<DailyTodoCard onClick={() => {}} planCount={0} activeTodayTodos={0} />);
    expect(screen.getByText('오늘은 비어 있어요')).toBeInTheDocument();
  });

  it('shows planCount in secondary line', () => {
    render(<DailyTodoCard onClick={() => {}} planCount={7} activeTodayTodos={2} />);
    expect(screen.getByText('진행 중인 Plan 7개')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<DailyTodoCard onClick={handleClick} planCount={3} activeTodayTodos={2} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledOnce();
  });
});
