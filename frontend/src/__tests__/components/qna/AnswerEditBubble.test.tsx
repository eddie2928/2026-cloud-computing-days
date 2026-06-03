/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnswerEditBubble } from '../../../components/qna/AnswerEditBubble';

describe('AnswerEditBubble', () => {
  it('value prop이 textarea에 프리필된다', () => {
    render(
      <AnswerEditBubble value="기존답변" onChange={vi.fn()} onSave={vi.fn()} onCancel={vi.fn()} />,
    );
    const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
    expect(textarea.value).toBe('기존답변');
  });

  it('입력 변경 시 onChange 호출', () => {
    const onChange = vi.fn();
    render(
      <AnswerEditBubble value="" onChange={onChange} onSave={vi.fn()} onCancel={vi.fn()} />,
    );
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '새 답변' } });
    expect(onChange).toHaveBeenCalledWith('새 답변');
  });

  it('저장 버튼 클릭 시 onSave 1회 호출', () => {
    const onSave = vi.fn();
    render(
      <AnswerEditBubble value="내용" onChange={vi.fn()} onSave={onSave} onCancel={vi.fn()} />,
    );
    fireEvent.click(screen.getByText('저장'));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it('취소 버튼 클릭 시 onCancel 1회 호출', () => {
    const onCancel = vi.fn();
    render(
      <AnswerEditBubble value="내용" onChange={vi.fn()} onSave={vi.fn()} onCancel={onCancel} />,
    );
    fireEvent.click(screen.getByText('취소'));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
