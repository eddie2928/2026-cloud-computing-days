/// <reference types="@testing-library/jest-dom" />
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ProgressBar } from '../../../components/plans/ProgressBar';

describe('ProgressBar', () => {
  it('renders at 0% — fill width is 0%', () => {
    const { getByTestId } = render(<ProgressBar value={0} />);
    expect(getByTestId('pb-fill').style.width).toBe('0%');
  });

  it('renders at 50% — fill width is 50%', () => {
    const { getByTestId } = render(<ProgressBar value={50} />);
    expect(getByTestId('pb-fill').style.width).toBe('50%');
  });

  it('renders at 100% — fill width is 100%', () => {
    const { getByTestId } = render(<ProgressBar value={100} />);
    expect(getByTestId('pb-fill').style.width).toBe('100%');
  });

  it('clamps value below 0 to 0%', () => {
    const { getByTestId } = render(<ProgressBar value={-10} />);
    expect(getByTestId('pb-fill').style.width).toBe('0%');
  });

  it('clamps value above 100 to 100%', () => {
    const { getByTestId } = render(<ProgressBar value={150} />);
    expect(getByTestId('pb-fill').style.width).toBe('100%');
  });

  it('has role=progressbar with correct aria attrs at 50', () => {
    const { getByRole } = render(<ProgressBar value={50} />);
    const bar = getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '50');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
  });
});
