/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { UndoConfirmModal } from '../../../components/qna/UndoConfirmModal';

function renderModal(onConfirm = vi.fn(), onClose = vi.fn()) {
  render(
    <UndoConfirmModal
      open
      onClose={onClose}
      onConfirm={onConfirm}
      targetSequence={3}
    />,
  );
  return { onConfirm, onClose };
}

describe('UndoConfirmModal', () => {
  it('keep 버튼 클릭 시 onConfirm("keep") 1회 호출', () => {
    const { onConfirm } = renderModal();
    fireEvent.click(screen.getByText('이 답변 수정하기'));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith('keep');
  });

  it('discard 버튼 클릭 시 onConfirm("discard") 1회 호출', () => {
    const { onConfirm } = renderModal();
    fireEvent.click(screen.getByText('이후 기록 삭제하고 다시'));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith('discard');
  });

  it('취소 버튼 클릭 시 onClose 1회 호출', () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByText('취소'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
