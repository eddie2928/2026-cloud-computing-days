import type { PlanWithTodosOut } from "../../lib/plans";

export function computePlanRowByDate(
  dates: string[],
  plans: PlanWithTodosOut[],
): Map<string, Map<number, number>> {
  const result = new Map<string, Map<number, number>>();
  for (const date of dates) {
    const active = plans
      .filter((p) => p.period_start <= date && date <= p.period_end)
      .sort((a, b) => {
        if (a.period_start !== b.period_start) return a.period_start.localeCompare(b.period_start);
        if (a.period_end !== b.period_end) return a.period_end.localeCompare(b.period_end);
        return a.id - b.id;
      });
    const dayMap = new Map<number, number>();
    active.forEach((plan, index) => dayMap.set(plan.id, index));
    result.set(date, dayMap);
  }
  return result;
}

export interface PackInterval {
  colStart: number;
  colEnd: number;
  isMultiDay: boolean;
  sortKey: number;
}

/**
 * 겹치지 않는 인터벌을 최소 row 수에 최대한 패킹.
 * 정렬: 다중일 먼저 → colStart 오름차 → span 넓은 순 → sortKey 오름차(tie-break).
 * 반환: 입력 배열과 동일 순서의 rowIndex 배열.
 */
export function packIntervalsIntoRows(intervals: PackInterval[]): number[] {
  if (intervals.length === 0) return [];

  const indexed = intervals.map((iv, origIdx) => ({ ...iv, origIdx }));

  indexed.sort((a, b) => {
    const aM = a.isMultiDay ? 0 : 1;
    const bM = b.isMultiDay ? 0 : 1;
    if (aM !== bM) return aM - bM;
    if (a.colStart !== b.colStart) return a.colStart - b.colStart;
    const aSpan = a.colEnd - a.colStart;
    const bSpan = b.colEnd - b.colStart;
    if (aSpan !== bSpan) return bSpan - aSpan;
    return a.sortKey - b.sortKey;
  });

  const result = new Array<number>(intervals.length);
  const assigned: Array<{ colStart: number; colEnd: number; rowIndex: number }> = [];

  for (const iv of indexed) {
    let rowIndex = 0;
    while (
      assigned.some(
        (s) =>
          s.rowIndex === rowIndex &&
          s.colStart < iv.colEnd &&
          s.colEnd > iv.colStart,
      )
    ) {
      rowIndex++;
    }
    assigned.push({ colStart: iv.colStart, colEnd: iv.colEnd, rowIndex });
    result[iv.origIdx] = rowIndex;
  }

  return result;
}
