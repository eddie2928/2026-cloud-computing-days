import { describe, it, expect } from 'vitest';
import {
  packIntervalsIntoRows,
  type PackInterval,
} from '../../../components/calendar/planRowUtils';

function iv(
  colStart: number,
  colEnd: number,
  isMultiDay: boolean,
  sortKey: number,
): PackInterval {
  return { colStart, colEnd, isMultiDay, sortKey };
}

describe('packIntervalsIntoRows', () => {
  it('TC1: 다중일 단독 → row0', () => {
    const [rowA] = packIntervalsIntoRows([iv(1, 6, true, 0)]);
    expect(rowA).toBe(0);
  });

  it('TC2: 겹치는 다중일 두 개 → 각각 row0, row1', () => {
    const [rowA, rowB] = packIntervalsIntoRows([iv(1, 6, true, 0), iv(1, 3, true, 1)]);
    expect(rowA).toBe(0);
    expect(rowB).toBe(1);
  });

  it('TC3: 안 겹치는 다중일 두 개 → 같은 row0 (최대 패킹)', () => {
    // A=[1,6), C=[6,8) — 연속하지만 겹치지 않음
    const [rowA, rowC] = packIntervalsIntoRows([iv(1, 6, true, 0), iv(6, 8, true, 1)]);
    expect(rowA).toBe(0);
    expect(rowC).toBe(0);
  });

  it('TC4: A(1-8), B(1-3), C(3-5) → A=0, B=1, C=1 (B 옆 빈칸에 C 끼워넣기)', () => {
    const [rowA, rowB, rowC] = packIntervalsIntoRows([
      iv(1, 8, true, 0),
      iv(1, 3, true, 1),
      iv(3, 5, true, 2),
    ]);
    expect(rowA).toBe(0);
    expect(rowB).toBe(1);
    expect(rowC).toBe(1);
  });

  it('TC5: 단일 D 먼저 입력해도 다중일 A가 row0 선점 (정렬 우선순위)', () => {
    // 입력 순서: D 단일(3–4), A 다중일(1–6)
    const [rowD, rowA] = packIntervalsIntoRows([iv(3, 4, false, 0), iv(1, 6, true, 1)]);
    expect(rowA).toBe(0);
    expect(rowD).toBe(1);
  });

  it('TC6: 동일 구간 X(sortKey=10), Y(sortKey=5) → Y=row0, X=row1', () => {
    const [rowX, rowY] = packIntervalsIntoRows([iv(1, 8, true, 10), iv(1, 8, true, 5)]);
    expect(rowX).toBe(1);
    expect(rowY).toBe(0);
  });

  it('TC7: 단일 막대 단독 → row0', () => {
    const [row] = packIntervalsIntoRows([iv(3, 4, false, 0)]);
    expect(row).toBe(0);
  });

  it('빈 배열 → 빈 배열', () => {
    expect(packIntervalsIntoRows([])).toEqual([]);
  });

  it('겹치는 3개 → 각각 row0, row1, row2', () => {
    // 모두 [1,8) 겹침
    const rows = packIntervalsIntoRows([
      iv(1, 8, true, 0),
      iv(1, 4, true, 1),
      iv(1, 3, true, 2),
    ]);
    // 정렬: span 기준 7>3>2 → 0,1,2 순 → 모두 겹침 → 각각 row
    expect(rows[0]).toBe(0);
    expect(rows[1]).toBe(1);
    expect(rows[2]).toBe(2);
  });

  it('span이 같을 때 colStart 빠른 쪽이 먼저 배정', () => {
    // A=[2,5) span=3, B=[5,8) span=3 — 안 겹침 → 같은 row
    const [rowA, rowB] = packIntervalsIntoRows([iv(2, 5, true, 0), iv(5, 8, true, 1)]);
    expect(rowA).toBe(0);
    expect(rowB).toBe(0);
  });
});
