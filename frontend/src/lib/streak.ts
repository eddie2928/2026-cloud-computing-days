import type { CalendarEntry } from './week';

export function getStreak(entries: CalendarEntry[], today: string): number {
  const dateSet = new Set(entries.map(e => e.date));
  if (!dateSet.has(today)) return 0;

  let streak = 0;
  const cur = new Date(today);
  while (dateSet.has(cur.toISOString().split('T')[0])) {
    streak++;
    cur.setDate(cur.getDate() - 1);
  }
  return streak;
}
