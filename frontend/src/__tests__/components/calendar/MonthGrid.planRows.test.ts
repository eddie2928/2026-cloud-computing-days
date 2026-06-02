import { describe, it, expect } from 'vitest';
import {
  packIntervalsIntoRows,
  type PackInterval,
} from '../../../components/calendar/planRowUtils';

// 플랜 막대 배치 관련 케이스 — sortKey = plan.id

function planIv(
  colStart: number,
  colEnd: number,
  planId: number,
): PackInterval {
  return {
    colStart,
    colEnd,
    isMultiDay: colEnd - colStart > 1,
    sortKey: planId,
  };
}

describe('packIntervalsIntoRows — 플랜 배치 케이스', () => {
  it('단일 플랜(단독) → row0', () => {
    const [row] = packIntervalsIntoRows([planIv(1, 8, 1)]);
    expect(row).toBe(0);
  });

  it('긴 플랜(span=7)이 짧은 플랜(span=3)보다 먼저 row0 선점', () => {
    // 두 플랜이 겹침: A(1-8,span=7), B(1-4,span=3)
    const [rowA, rowB] = packIntervalsIntoRows([planIv(1, 8, 1), planIv(1, 4, 2)]);
    expect(rowA).toBe(0);
    expect(rowB).toBe(1);
  });

  it('겹치지 않는 두 플랜 → 같은 row0에 패킹', () => {
    // A(1-3), B(4-7) — 안 겹침
    const [rowA, rowB] = packIntervalsIntoRows([planIv(1, 3, 1), planIv(4, 7, 2)]);
    expect(rowA).toBe(0);
    expect(rowB).toBe(0);
  });

  it('id 오름차 tie-break: id=3보다 id=1이 먼저 row0', () => {
    // 동일 구간, id만 다름
    const [rowHigh, rowLow] = packIntervalsIntoRows([planIv(1, 8, 3), planIv(1, 8, 1)]);
    expect(rowHigh).toBe(1); // id=3
    expect(rowLow).toBe(0);  // id=1
  });

  it('세 플랜 모두 겹침 → row0, row1, row2 순', () => {
    // span 순: A(7)>B(5)>C(3)
    const rows = packIntervalsIntoRows([
      planIv(1, 8, 1), // span=7
      planIv(2, 7, 2), // span=5
      planIv(3, 6, 3), // span=3
    ]);
    expect(rows[0]).toBe(0); // A
    expect(rows[1]).toBe(1); // B
    expect(rows[2]).toBe(2); // C
  });

  it('빈 배열 → 빈 배열', () => {
    expect(packIntervalsIntoRows([])).toEqual([]);
  });
});
