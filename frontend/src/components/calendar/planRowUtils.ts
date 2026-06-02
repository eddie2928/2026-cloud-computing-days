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
