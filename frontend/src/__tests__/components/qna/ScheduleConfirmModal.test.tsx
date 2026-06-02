/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ScheduleConfirmModal } from '../../../components/qna/ScheduleConfirmModal';
import type { PendingScheduleItem } from '../../../components/qna/ScheduleConfirmModal';

const baseSchedule: PendingScheduleItem = {
  period_start: '2026-05-10',
  period_end: '2026-05-10',
  situation: '팀 회의',
  start_time: '09:00',
  end_time: '10:00',
};

describe('ScheduleConfirmModal — 날짜 수정', () => {
  it('초기값으로 period_start/period_end가 날짜 input에 채워진다', () => {
    render(
      <ScheduleConfirmModal
        open
        schedule={baseSchedule}
        onAccept={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    const inputs = document.querySelectorAll('input[type="date"]');
    expect(inputs).toHaveLength(2);
    expect((inputs[0] as HTMLInputElement).value).toBe('2026-05-10');
    expect((inputs[1] as HTMLInputElement).value).toBe('2026-05-10');
  });

  it('종료일을 변경하면 onAccept가 변경된 period_end로 호출된다', () => {
    const onAccept = vi.fn();
    render(
      <ScheduleConfirmModal
        open
        schedule={baseSchedule}
        onAccept={onAccept}
        onReject={vi.fn()}
      />,
    );
    const [, endInput] = document.querySelectorAll('input[type="date"]');
    fireEvent.change(endInput, { target: { value: '2026-05-12' } });
    fireEvent.click(screen.getByText('추가'));
    expect(onAccept).toHaveBeenCalledOnce();
    const payload = onAccept.mock.calls[0][0] as PendingScheduleItem;
    expect(payload.period_end).toBe('2026-05-12');
  });

  it('시작일도 변경되면 period_start가 override되어 전달된다', () => {
    const onAccept = vi.fn();
    render(
      <ScheduleConfirmModal
        open
        schedule={baseSchedule}
        onAccept={onAccept}
        onReject={vi.fn()}
      />,
    );
    const [startInput] = document.querySelectorAll('input[type="date"]');
    fireEvent.change(startInput, { target: { value: '2026-05-08' } });
    fireEvent.click(screen.getByText('추가'));
    expect(onAccept).toHaveBeenCalledOnce();
    const payload = onAccept.mock.calls[0][0] as PendingScheduleItem;
    expect(payload.period_start).toBe('2026-05-08');
  });

  it('종료일이 시작일보다 이르면 추가 버튼이 비활성화된다', () => {
    render(
      <ScheduleConfirmModal
        open
        schedule={{ ...baseSchedule, period_start: '2026-05-10', period_end: '2026-05-10' }}
        onAccept={vi.fn()}
        onReject={vi.fn()}
      />,
    );
    const [, endInput] = document.querySelectorAll('input[type="date"]');
    fireEvent.change(endInput, { target: { value: '2026-05-08' } });
    const addBtn = screen.getByText('추가');
    expect(addBtn).toBeDisabled();
  });
});
